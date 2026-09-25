# PanoVLN instruction generation

This pipeline takes the recorded trajectories from `dataset_create/trajectory`, renders observations when needed, writes navigation instructions for local route segments, verifies them, and exports clean ERP images and standard Habitat R2R data. Instructions should let a navigator follow the route, select the correct entrance at decision points, and stop in the intended destination area. Minor repetition, irrelevant appearance differences, and small turns do not prevent an instruction from being accepted.

## Run and configure the pipeline

Use an active Python environment with Habitat-Sim 0.3.3, NumPy, SciPy, NetworkX, Pillow, requests, imageio, and imageio-ffmpeg. Qwen is called through a separately deployed vLLM service.

Edit the assignments at the top of [create_instructions.sh](../create_instructions.sh):

| Setting | Purpose |
| --- | --- |
| `PYTHON_BIN` | Python interpreter with Habitat-Sim installed |
| `TRAJECTORIES` | Input trajectory `.json.gz` or `.json` file |
| `SCENE_ROOT` | HM3D scene root |
| `OUTPUT_ROOT`, `NAME` | R2R output directory and file name |
| `ERP_ROOT` | Training image directory; defaults to `./data/images/panovln` |
| `WORK_DIR` | Checkpoints for resuming; defaults to `${OUTPUT_ROOT}/.work/instruction` and is removed after successful completion |
| `NUM_PROCESSES` | Number of Habitat workers; defaults to 16, each holding one simulator |
| `EPISODES_PER_PROCESS` | Concurrent trajectories per worker; defaults to 9. The API concurrency limit is `NUM_PROCESSES × EPISODES_PER_PROCESS`, or 144 by default |
| `GPU_DEVICE_IDS=(0 1 2 3 4 5 6 7)` | GPUs used by Habitat; defaults to two simulators per GPU |
| `CPU_THREADS_PER_PROCESS` | Numerical library threads per worker; defaults to 1 to limit OpenMP and BLAS overhead |
| `LIMIT` | Maximum number of selected trajectories; `0` (default) processes all, while `24` processes at most 24 |
| `SELECTION` | `first` follows input order; `diverse` prioritizes scene coverage and trajectories with more decisions |
| `ERP_WIDTH`, `ERP_HEIGHT` | ERP resolution; defaults to 1600×800 and must have a 2:1 ratio |
| `JPEG_QUALITY` | Training image JPEG quality; defaults to 95 |
| `BASE_URL`, `MODEL_NAME`, `API_KEY` | Model API endpoint, model name, and key |
| `MEDIA_MODE` | Defaults to `video`; `frames` uses the frame-by-frame compatibility input |
| `KEEP_WORK` | Defaults to `false`; set to `true` to retain intermediate files for debugging |

The default setup uses GPUs 0–7, 16 rendering workers, and at most 144 concurrent trajectory workflows. It sets `LIMIT=0` and `NAME="train"`, and does not split the dataset according to the source scene directories. The default input is:

```text
./data/general_vln_dataset/panovln/trajectory/trajectories.json.gz
```

Run from the repository root:

```bash
# Check inputs and settings without rendering or calling the model.
./dataset_create/create_instructions.sh inspect

# Generate data using the settings at the top of the script.
./dataset_create/create_instructions.sh generate

# Check the exported R2R format and scene paths.
./dataset_create/create_instructions.sh validate
```

You can append CLI options such as `--trajectory-ids trajectory_...` or `--scene-ids 00800-TEEsavR23oF`. CLI options override the script settings. When changing the output location through the CLI, also supply `--erp-root` and `--work-dir`. For routine runs, edit the script settings directly.

Each worker owns one Habitat simulator and can process up to `EPISODES_PER_PROCESS` trajectories concurrently within a scene. Each trajectory has its own HTTP client and checkpoint, allowing other trajectories to advance while one waits for the API. The worker's main thread handles replay, route projection, and ERP export sequentially; Habitat's OpenGL context is never shared between threads.

At startup, the pipeline checks completed records and batches only unfinished trajectories by scene. Scenes with more remaining trajectories are scheduled first, and a batch contains at most four rounds of concurrent work. After a batch, a worker takes another from a shared queue. Several workers may handle a large scene so that the final tasks do not leave most workers idle. A batch does not switch scenes, and adjacent batches reuse the simulator when they use the same scene.

This raises the API concurrency ceiling to 144 while keeping at most 16 local simulators, two per GPU. If a scene exceeds GPU memory, lower `NUM_PROCESSES` and raise `EPISODES_PER_PROCESS` to preserve the API concurrency ceiling. Actual API concurrency also depends on rendering preparation, remaining tasks, and service throughput. In `render` mode, each worker processes only one trajectory. Concurrency settings are not part of the data content fingerprint and can be changed after an interruption.

The main process displays one overall `tqdm` progress bar with the selected count, percentage, elapsed time, throughput, estimated remaining time, and counts of `accepted`, `quarantined`, `error`, and `resumed` records. After the startup check, reusable records are included in the initial progress count; throughput reflects work newly completed in the current run. Reaching 100% means every selected trajectory has been processed, not that every trajectory was accepted. Final aggregation and export still follow. Worker errors appear above the progress bar, while details are saved in checkpoints and the final summary. `render` mode also shows a `prepared` count.

Native Habitat logs during scene startup and shutdown are captured temporarily. If an operation fails, the captured diagnostics are shown and the exception is preserved. The pipeline needs RGB, depth, scene geometry, and NavMesh, but no semantic sensor or object category annotations. Missing optional semantic descriptions do not affect these inputs.

The instruction stage uses Habitat-Sim directly. It does not run Habitat-Lab task measures or repartition navigation regions. Verification shares one clean video observation and one full-text comparison across the decisions, ordinary motion, and stopping requirements in a segment. Text repair reuses the same observation. When a segment fails, the pipeline repairs it before checking later segments. Acceptance still requires every relevant decision, motion, and stop check to pass. Throughput also depends on the number of segments, repair attempts, and model service load.

`GPU_DEVICE_IDS` controls only Habitat GPUs, not the GPUs assigned to the existing vLLM service. The script targets `http://127.0.0.1:10430/v1` and `Qwen3.8-27B` by default. Service deployment and throughput determine actual inference concurrency. API keys are not written to request records or run manifests. Requests to the local aggregator bypass proxies automatically. If the aggregator uses a proxy for a remote API, configure it in the aggregator process and exclude localhost from that proxy.

## Final outputs

```text
./data/
├── general_vln_dataset/panovln/
│   ├── train.json
│   └── train.json.gz
└── images/panovln/
    └── 0/                         # R2R episode_id
        ├── frame_0.jpg
        ├── frame_1.jpg
        └── ...
```

The two R2R files contain identical JSON after decompression and include only automatically verified trajectories. Training images use Habitat's native equirectangular camera at the actual agent pose, kept level and placed at the sensor height recorded in the trajectory metadata. This training camera is separate from the downward-facing perspective camera used to create instructions.

**`frame_i.jpg` shows the observation before executing `action_ids[i]`.** Every action has an image, including in-place rotations and the final STOP. No duplicate frame is saved after STOP, so each trajectory has as many images as source actions. Image and checkpoint directories use the final numeric R2R `episode_id`: the trajectory's zero-based index in the full input file. Filtering or quarantine can leave gaps, and IDs are not renumbered. The source `trajectory_id` remains in the JSON for action alignment. ERP images contain no route, candidate label, or other overlay.

Images are exported only after a trajectory passes verification, and its directory is published only after all images are complete. A partial directory left by a forced interruption is rebuilt when that trajectory resumes; it is not treated as a complete training sample. Failed trajectories do not produce official training images. Set `ERP_ROOT` separately to match the training image path, and use a new image directory when changing camera resolution.

## Temporary files and recovery

The pipeline renders as it processes trajectories instead of extracting the full image set in advance. Once a trajectory becomes `accepted` or `quarantined`, it removes its videos, compass views, perspective images, depth, route arrays, and model request records. Compact process records remain until aggregation. After the full batch completes and R2R export succeeds, the entire `WORK_DIR` is removed. The final directory contains no instruction-generation media or sidecars.

An interrupted process or an API, program, or I/O error retains the work directory. Rerun `generate` with the same settings to resume unfinished stages without repeating inference for completed trajectories. Saved local text and model responses are reused; a call or write that was still in progress when interrupted may run again. Do not manually delete checkpoints while generation is incomplete. The manifest fingerprints the code, settings, source data path, and trajectory metadata; each record also binds trajectory content and scene file information. An output lock prevents conflicting writers. Use separate `NAME` and `WORK_DIR` values for concurrent jobs.

A truncated model response, invalid JSON, or repeatedly missing required fields marks a trajectory `quarantined` after the configured retries are exhausted. JSON responses with invalid fields are removed from the reusable cache and kept as `.invalid.json` for debugging, so a resumed run does not repeatedly read the same invalid response. Network, HTTP service, and program errors remain `error` records awaiting recovery. Aggregation displays a `Checking records/ERP` progress bar, checks accepted records and clean ERP images, and writes JSON; only `accepted` records enter training data. JSON writing and compression and temporary-file cleanup each report status and duration. The training files are usable during cleanup, although many small historical backup files can make cleanup slow.

A later run checks the existing JSON/gzip and ERP and returns `already_exported`. **Increasing `LIMIT` does not automatically append to a completed dataset; use a new `NAME` and `WORK_DIR` for a new selection or configuration.** If the work directory was retained for debugging, you can expand the selection and reuse records when the configuration is otherwise unchanged.

Set `KEEP_WORK=true` while debugging to retain:

```text
WORK_DIR/
├── manifest.json
├── summary.json
├── last_run.json
└── episodes/<episode_id>/
    ├── record.json                 # Pose, segment and clause sources, verification and repair history
    ├── ground_route.npz
    ├── requests/<hash>.json
    └── media/s000/attempt_0/       # Clean/route videos and frames, compass, and depth
```

`render` only prepares visual evidence, which `generate` can reuse with the same settings. `export` aggregates a retained work directory without calling the model; when `KEEP_WORK` is disabled, a successful export removes that directory. By default, export refuses unfinished records. `export --allow-incomplete` explicitly exports the currently accepted subset and retains the work directory. An interrupted R2R publication or final cleanup is completed on resumption; the completion marker is removed last to avoid regeneration from scratch. `--retry-quarantined` starts another local repair round from a retained work directory.

## Five generation stages

1. **Natural segmentation:** Split around approaches to decisions, travel after an entrance, clear turns, and the destination approach. Do not cut ordinary route sections at a fixed frame count or every small turn. Adjacent segments may share approach context. Each action and decision belongs to one segment, and the final segment contains actual arrival and stopping.
2. **Visual evidence:** Replay the recorded actions and poses. Ordinary segments use local video; decision segments also receive an eight-direction compass, and the destination segment shows the actual approach. Generation views include a ground-projected ground-truth route. Clean versions are retained for verification.
3. **Local language generation:** Qwen describes what the navigator should do. Visual details should help identify an entrance, path, or stopping place using evidence available when the choice is made. Actual heading changes between video frames are marked LEFT/RIGHT to help locate turns. A new entrance must still be supported by the visible path; a small heading correction should not become a new choice. The author may reuse names from the preceding segment. Local text stays linked to its segment.
4. **Light editing:** Improve continuity and remove repetition without adding route facts. The program checks the original text, order, and sources of critical choice and stop clauses. The final instruction must not rely on route overlays.
5. **Local verification and repair:** First observe the full clean segment without its instruction. Then compare the full segment text against the observed entrance choice, motion order, and stopping requirement in one request. Conclusions are saved separately but share the observation and comparison requests. A failure points to the relevant segment; local language is repaired first, or the author can request upstream repair when evidence or segmentation is inadequate. By default, each segment allows two text repairs and one upstream repair. Trajectories that still cannot be clearly described or verified are quarantined.

Prompts are in [prompts.py](prompts.py) and settings in [config/default.json](config/default.json). The task definition is for general navigation; it has no routing rules keyed to a trajectory, scene, room, or object name.

### Routes and compass views

The program first checks replayed decision poses, the final pose, collisions, and goal arrival. RGB and unnormalized depth come from the same perspective camera: 448×448 by default, with a 90° horizontal field of view and a 30° downward pitch. Projection uses the camera's actual world extrinsics.

The ground-truth polyline is projected to the real floor with downward ray casts. Depth reconstructs visible surface points in world coordinates; only upward-facing surfaces near the route are colored. Line width and arrow spacing use world-space dimensions, so perspective scales naturally. Occluded floor has no visible pixels, preventing routes from appearing through walls. Route points without geometric support are not drawn. Defaults are a 6.5 cm line width and 75 cm arrow spacing.

The eight compass images use the same position and instant. With the agent's actual heading as forward, one perspective view is captured every 45°:

| Front left | Front | Front right |
| --- | --- | --- |
| Left | Current heading ↑ | Right |
| Back left | Back | Back right |

The center is not a ninth view. A decision compass is captured at the annotated choice time, before the branch anchor, and may step backward along the actual trajectory to show the entrance and its surroundings. Abstract NavMesh connection centers are no longer labeled as building entrances A/B/C because they may not coincide with physical doorways. The generation view uses the ground-projected route to show where the agent went; the clean version retains the same scene evidence.

Video frames are selected by displacement and accumulated turn angle, retaining segment boundaries, decisions, and the actual STOP. Generation and verification both use the full core interval. Earlier approach context is provided by the pre-choice compass rather than a separate duplicate verification video for every decision. Clean video intentionally shows the traversed route for consistency checking. All selected frames are passed through the vLLM OpenCV decoder, with additional frame selection by the model processor disabled.

### Verification criteria

- **Decisions:** The observation step receives the full clean segment video, the pre-choice compass, and actual heading and elevation changes. It does not receive the instruction, ground-truth branch answer, or route markings. It records the traversed order, clues available before the choice, and alternative entrances. Text verification then checks `path_matches` and `choice_is_clear` for each decision. Both must be true, the status must pass, and confidence must be sufficient. A vague description does not pass merely because it is compatible with the video. Observations do not change with local wording and can be reused from the request cache.
- **Destination:** Clean approach video and the actual stop compass are used to check whether the text identifies the same local destination and would avoid a clear early or overshot stop. Tiny differences within the same destination area need not be distinguished.
- **Ordinary motion:** The full local clause is checked for motion order, including “then” and “again” after important choices, so one turn is not counted twice after a sentence is truncated. Heading change establishes direction, not the existence of a new entrance. Clear left/right reversals, incorrect stair direction, or entry into the wrong space fail. Minor corrections, natural bends in halls or stairs, approximate landmark names, and harmless repetition are acceptable. The text need not narrate every frame.

This process checks navigability and route consistency. It does not use a single-letter multiple-choice question for acceptance and is not an independent blind-navigation success experiment. Model observation and comparison can still be wrong; automatic acceptance is not a human-verified accuracy measure. Sampling, controlled comparisons, and visual review are recorded in [VALIDATION.md](VALIDATION.md).

## R2R format

The export follows the untokenized R2R schema used by the ScaleVLN 150k subset. The top-level fields are `episodes` and `instruction_vocab`. Each episode has the following shape:

```json
{
  "episode_id": 0,
  "trajectory_id": "trajectory_...",
  "scene_id": "train/00000-kfPV7w3FaU5/kfPV7w3FaU5.basis.glb",
  "start_position": [0.0, 0.0, 0.0],
  "start_rotation": [0.0, 0.0, 0.0, 1.0],
  "info": {"geodesic_distance": 10.0},
  "goals": [{"position": [1.0, 0.0, 2.0], "radius": 0.25}],
  "instruction": {"instruction_text": "...", "instruction_tokens": null},
  "reference_path": [[0.0, 0.0, 0.0], [1.0, 0.0, 2.0]]
}
```

`episode_id` is the trajectory's index in the source dataset, and `start_rotation` uses xyzw order. `reference_path` contains positions from the actual replay, omitting repeated positions from pure rotations and STOP. Both the goal and the last reference-path point are the actual stop position; shortest-path distance is also measured to that point.

Scene paths are relative to `SCENE_ROOT` and begin with `train/...` or `val/...` only to locate HM3D files. All these scenes contribute to the same training input. Habitat's `data_path` points to the exported `.json.gz`, and `scenes_dir` remains `./data/scene/hm3d`. The source trajectory file remains the basis for aligning actions and images. Generation-only fields are not added to the standard R2R export.
