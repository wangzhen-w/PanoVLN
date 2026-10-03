# Reproducing PanoVLN

[Back to the repository](../README.md) · [Training configuration](../src/train/README.md) · [Robot deployment](../realworld/README.md)

This guide covers the path from installation to simulation, training, and a recorded Go2 trial. Run commands from the repository root unless stated otherwise. The shell launchers define their paths and GPU choices inside the files; edit those settings before running them.

| Workflow | Required assets | Start here |
| --- | --- | --- |
| Simulation evaluation | Complete PanoVLN checkpoint, MP3D scenes, R2R/RxR evaluation episodes | [Install](#install-the-environment) → [scenes](#scenes-and-navigation-annotations) → [evaluate](#evaluate-a-checkpoint) |
| Training | Qwen/PanoVGGT initialization or a navigation checkpoint, training JSONL, rendered images | [Prepare data](#prepare-training-data) → [train](#train-a-model) |
| Robot deployment | PanoVLN Real World checkpoint on a GPU server; ROS2 Go2 client and panorama camera | [Deploy](#deploy-on-a-physical-robot) |

Keep the robot client in its ROS-compatible Python environment. It needs neither Habitat nor the model weights. The GPU server needs the model environment and HTTP dependencies; Habitat is used only for simulation and data rendering.

## Install the environment

Use Linux with an NVIDIA GPU for the model process. Create the Python environment and install the core versions recorded for this repository:

```bash
git clone https://github.com/wangzhen-w/PanoVLN.git
cd PanoVLN
conda create -n panovln python=3.12 -y
conda activate panovln

python -m pip install torch==2.10.0 torchvision==0.25.0
python -m pip install \
  transformers==5.5.0 accelerate==1.13.0 peft==0.18.1 \
  deepspeed==0.18.0 \
  numpy pillow pyyaml tqdm scipy einops timm omegaconf \
  huggingface-hub safetensors wandb
```

Select [PyTorch CUDA wheels](https://pytorch.org/get-started/locally/) compatible with your driver. For FlashAttention, follow the [FlashAttention 2 installation instructions](https://github.com/Dao-AILab/flash-attention#installation-and-features). To use PyTorch attention instead, set `attn_implementation: sdpa` in the training configuration or `ATTN_IMPLEMENTATION="sdpa"` in the evaluation launcher.

PanoVLN is imported from the checkout by the launchers. The bundled `src/panovggt/requirements.txt` belongs to the upstream standalone PanoVGGT project and pins an older PyTorch stack; use the environment above for this navigation code.

Before downloading large assets, check the model imports:

```bash
python - <<'PYMODEL'
import torch, transformers
from src.qwen_vl import Qwen3_5ForConditionalGenerationForPanoVLN
print("PyTorch:", torch.__version__, "CUDA:", torch.cuda.is_available())
print("Transformers:", transformers.__version__)
PYMODEL
```

### Habitat setup

Rendering, DAgger collection, and simulation evaluation use **Habitat-Sim 0.3.3** with rendering support. Follow its [versioned installation instructions](https://github.com/facebookresearch/habitat-sim/tree/v0.3.3); select headless rendering on a server without a display. Install a build matching the active Python version. If a matching binary package is unavailable, the upstream [source-build route](https://github.com/facebookresearch/habitat-sim/blob/v0.3.3/BUILD_FROM_SOURCE.md) is:

```bash
git clone --branch v0.3.3 --recursive https://github.com/facebookresearch/habitat-sim.git ../habitat-sim
cd ../habitat-sim
python -m pip install -r requirements.txt
python setup.py install --headless
cd ../PanoVLN
```

Install the compiler/CMake and EGL/OpenGL system dependencies listed in that build guide before compiling. Keep this build in the same `panovln` environment.

Install the matching Habitat-Lab and Habitat-Baselines packages in the same environment:

```bash
git clone --branch v0.3.3 https://github.com/facebookresearch/habitat-lab.git ../habitat-lab
python -m pip install -e ../habitat-lab/habitat-lab -e ../habitat-lab/habitat-baselines
python -m pip install fastdtw networkx imageio imageio-ffmpeg opencv-python
```

Check the imports before preparing scenes:

```bash
python -c "import torch, transformers, habitat, habitat_sim; print('CUDA:', torch.cuda.is_available()); print('Transformers:', transformers.__version__)"
```

## Download a checkpoint

Choose a checkpoint from the [model zoo](../README.md#model-zoo):

```bash
# Full-data simulation model
hf download wangzhen-w/PanoVLN --local-dir checkpoints/PanoVLN

# R2R/RxR-only navigation-data model (optional)
hf download wangzhen-w/PanoVLN_base --local-dir checkpoints/PanoVLN_base

# Physical robot deployment model (optional)
hf download wangzhen-w/PanoVLN_realworld --local-dir checkpoints/PanoVLN_realworld
```

Download each model directory in full, including configuration, tokenizer, and processor files. A complete PanoVLN checkpoint includes the geometry encoder; separate initialization weights are used when starting training from Qwen. For physical deployment, use `PanoVLN_realworld`, which adds trajectory recovery and collision avoidance. Keep this checkpoint choice in the experiment record; it is distinct from the simulation models.

## Scenes and navigation annotations

For R2R-CE and RxR-CE, follow the [VLN-CE dataset instructions](https://github.com/jacobkrantz/VLN-CE#data) and obtain Matterport3D scene assets through the original access process. For PanoVLN training scenes and new trajectory generation, obtain [HM3D assets](https://aihabitat.org/datasets/hm3d/).

The default root is `data/`. You can place the data there or create a `data` symlink to an existing storage volume. Preserve each dataset's split directories and the original scene assets and navigation meshes.

```text
data/
├── general_vln_dataset/
│   ├── r2r/
│   │   ├── train/train.json.gz
│   │   ├── val_seen/val_seen.json.gz
│   │   └── val_unseen/val_unseen.json.gz
│   ├── rxr/
│   │   ├── train/train_guide.json.gz
│   │   ├── val_seen/val_seen_guide.json.gz
│   │   └── val_unseen/val_unseen_guide.json.gz
│   └── panovln/train.json.gz
├── scene/
│   ├── mp3d/<scene_id>/
│   └── hm3d/
│       ├── train/<scene_id>/
│       └── val/<scene_id>/
├── images/
│   ├── r2r/<episode_id>/frame_0.jpg
│   ├── rxr/<episode_id>/frame_0.jpg
│   ├── panovln/<episode_id>/frame_0.jpg
│   └── dagger/<trajectory_id>/frame_0.jpg
├── sub_dataset/
│   ├── r2r.jsonl
│   ├── rxr.jsonl
│   ├── panovln.jsonl
│   └── dagger.jsonl
└── train.jsonl
```

Only prepare the datasets needed by your run. Simulation evaluation needs the relevant evaluation split and scene assets; it renders observations online and does not need the training image folders.

| Configuration | Episode path | Scene root |
| --- | --- | --- |
| [`config/vln_r2r.yaml`](../config/vln_r2r.yaml) | `data/general_vln_dataset/r2r/{split}/{split}.json.gz` | `data/scene/` |
| [`config/vln_rxr.yaml`](../config/vln_rxr.yaml) | `data/general_vln_dataset/rxr/{split}/{split}_{role}.json.gz` | `data/scene/` |
| [`config/vln_panovln.yaml`](../config/vln_panovln.yaml) | `data/general_vln_dataset/panovln/train.json.gz` | `data/scene/hm3d/` |

R2R/RxR evaluation defaults to `val_unseen`; RxR selects the `guide` role and English (`en-US`, `en-IN`) instructions. Both use 1280×640 RGB panoramas, 0.25 m forward steps, 15° turns, and a 3 m success distance. The PanoVLN generation configuration uses a 0.3 m goal tolerance. Preserve these task settings when comparing results.

## Evaluate a checkpoint

Edit [`scripts/eval_r2r.sh`](../scripts/eval_r2r.sh) or [`scripts/eval_rxr.sh`](../scripts/eval_rxr.sh). For the first run, change these settings directly in the selected script:

```bash
MODEL_PATH="./checkpoints/PanoVLN"
GPU_IDS="0"
PROCS_PER_GPU=1
TOTAL_MAX_EPISODES=5
SAVE_PATH="./outputs/eval/r2r_smoke"
```

Use an `rxr_smoke` output directory when running RxR. If FlashAttention is unavailable, also set `ATTN_IMPLEMENTATION="sdpa"`.

```bash
bash scripts/eval_r2r.sh
# or
bash scripts/eval_rxr.sh
```

After the small run completes, set `TOTAL_MAX_EPISODES=0` for the full split, select your GPU/worker allocation, and use a new output directory. Default launchers request four GPUs with three workers per GPU; choose concurrency to fit your available memory.

The launchers evaluate `val_unseen` by default and write:

| File | Contents |
| --- | --- |
| `result.jsonl` | Per-episode results, merged from worker shards |
| `result_summary.json` | Aggregate evaluation metrics |

Existing episode results are reused. Use a new `SAVE_PATH` when changing checkpoints, execution policies, seeds, or episode budgets. Save the launcher and configuration alongside the results to record the full setup.

### Run one worker directly

The Python entry point also accepts explicit arguments. This command runs a five-episode R2R check with one GPU and PyTorch SDPA, without editing the multi-worker launcher:

```bash
PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}" CUDA_VISIBLE_DEVICES=0 \
python src/eval/eval.py \
  --exp-config config/vln_r2r.yaml \
  --split-num 1 --split-id 0 \
  --model-path checkpoints/PanoVLN \
  --result-path outputs/eval/r2r_single_worker \
  --total-max-episodes 5 --max-episodes 0 \
  --attn-implementation sdpa \
  --forward-distance 25 --turn-angle 15 \
  --max-memory-images 10 --memory-pool-window-frames 100 \
  --actions-per-replan uncertainty --uncertainty-budget 1.2 --seed 42

python src/eval/analyze_results.py --path outputs/eval/r2r_single_worker
```

For RxR, change the config to `config/vln_rxr.yaml` and the output directory. `--forward-distance` is measured in centimeters in this evaluation CLI; the robot client's `--forward-distance` is measured in meters.

### Outputs and resuming

Workers append `result_rank<N>.jsonl` while running. The analysis step merges them into `result.jsonl`, writes `result_summary.json`, and removes the merged shards. Rows include episode/scene IDs, task metrics, executed actions, and model-predicted sequences. Summary keys are `num_episodes`, `success`, `spl`, `oracle_success`, `distance_to_goal`, `path_length`, and `ndtw`; rate metrics use fractions (multiply by 100 for percentages). `SAVE_TOPDOWN=true` adds per-episode videos under `top_down/`.

An interrupted run can reuse the same output directory to skip completed episode/scene pairs. Use a fresh directory for a different checkpoint, execution policy, or evaluation budget. The saved summary reflects the rows present in that directory.

### Execution settings

The model predicts 18 actions. The launchers independently control how many to execute before requesting a new panorama:

| Setting | Meaning |
| --- | --- |
| `ACTIONS_PER_REPLAN="uncertainty"` | Select an execution prefix from action confidence |
| `ACTIONS_PER_REPLAN=6` | Use a fixed six-action execution prefix |
| `UNCERTAINTY_BUDGET=1.2` | Confidence budget for prefix selection |

The launchers use Python defaults for the uncertainty action range `(4, 8)` and collision recovery after `2` consecutive forward collisions with static RGB. Both benchmarks execute STOP only when it falls within the selected action prefix; STOP does not extend the fixed execution length or the uncertainty-selected horizon.

## Prepare training data

### 1. Download released annotations

The [Hugging Face dataset](https://huggingface.co/datasets/wangzhen-w/PanoVLN) contains per-dataset annotations, prepared training JSONL files, and PanoVLN navigation episodes:

```bash
hf download wangzhen-w/PanoVLN --repo-type dataset --local-dir data
```

The release contains annotation files. Obtain scenes separately and render the corresponding images before training. To download only the base-training files, use:

```bash
hf download wangzhen-w/PanoVLN --repo-type dataset \
  --include "sub_dataset/r2r.jsonl" "sub_dataset/rxr.jsonl" "train_r2r_rxr.jsonl" \
  --local-dir data
```

| Released file | Mixture |
| --- | --- |
| `train_r2r_rxr.jsonl` | R2R + RxR |
| `r2r_rxr_dagger.jsonl` | R2R + RxR + DAgger |
| `r2r_rxr_dagger_panovln.jsonl` | R2R + RxR + DAgger + PanoVLN |
| `sub_dataset/{dataset}.jsonl` | Trajectory-level actions used by rendering and sample preparation |
| `general_vln_dataset/panovln/train.json.gz` | PanoVLN navigation episodes |

### 2. Prepare per-dataset actions and images

If the required `data/sub_dataset/*.jsonl` files are already downloaded, keep them and proceed to frame extraction. To regenerate R2R/RxR action annotations from source navigation episodes, edit `DATASET_NAMES` and the hardware settings in [`scripts/preprocess.sh`](../scripts/preprocess.sh), then run:

```bash
bash scripts/preprocess.sh
```

Select the datasets whose images are needed in [`scripts/extract_frame.sh`](../scripts/extract_frame.sh). Its default is `DATASET_NAMES=(r2r rxr)`; add `panovln` and/or `dagger` for those annotations. Set `GPU_IDS` and `PROCESSES_PER_GPU` for your machine; the supplied renderer requests eight GPUs with six processes each. For an initial rendering check, set `GPU_IDS="0"`, `PROCESSES_PER_GPU="1"`, and `MAX_EPISODES="5"`. Clear `MAX_EPISODES` to render all required images before a full training run, then run:

```bash
bash scripts/extract_frame.sh
```

Frames are saved under `data/images/<dataset>/`. The default format is JPEG, with one directory per episode. Complete episodes are skipped on subsequent runs. Match image filenames and locations to the paths recorded in the training JSONL.

### 3. Select or build training samples

For the released mixtures, copy the chosen prepared JSONL to the training path:

```bash
# R2R + RxR
cp data/train_r2r_rxr.jsonl data/train.jsonl

# Alternatively, R2R + RxR + DAgger + PanoVLN
# cp data/r2r_rxr_dagger_panovln.jsonl data/train.jsonl
```

The release also includes `r2r_rxr_dagger.jsonl`. Select the mixture corresponding to your experiment and render images for every included dataset.

To build a custom mixture, edit `DATASET_NAMES` in [`scripts/prepare_dataset.sh`](../scripts/prepare_dataset.sh), then run:

```bash
bash scripts/prepare_dataset.sh
```

The default output is `data/train.jsonl`. Targets contain exactly 18 actions; terminal targets are padded with `stop`. When rebuilding an existing training file, use `bash scripts/prepare_dataset.sh --overwrite`.

Prepared samples contain `instruction`, `action_sequence`, `images`, `episode_id`, `dataset`, `step_index`, `end_step`, `real_action_count`, and `history_actions`. `images` is ordered from the episode start through the current observation; `action_sequence` has exactly 18 target words. The loader selects a bounded history from these paths.

Check the first selected training sample before launching a long run:

```bash
python - <<'PYDATA'
import json
from pathlib import Path
root = Path("data")
with (root / "train.jsonl").open() as stream:
    row = json.loads(next(stream))
assert len(row["action_sequence"]) == 18
assert set(row["action_sequence"]) <= {"stop", "forward", "left", "right"}
missing = [name for name in row["images"] if not (root / name).is_file()]
assert not missing, f"Missing images: {missing[:5]}"
print(row["dataset"], row["episode_id"], "images:", len(row["images"]))
PYDATA
```

This checks one sample's format and paths. To generate additional trajectories and instructions, follow the [dataset-generation guide](../dataset_create/README.md).

## Train a model

For training from initialization, download Qwen3.5-4B and PanoVGGT:

```bash
hf download Qwen/Qwen3.5-4B --local-dir checkpoints/Qwen3.5-4B
hf download YijingGuo/PanoVGGT --local-dir checkpoints/PanoVGGT
```

Confirm the geometry checkpoint is at `checkpoints/PanoVGGT/model.pt`, or update `model.panovggt_checkpoint_path` in the training YAML to its actual location.

Edit [`src/train/config/config.yaml`](../src/train/config/config.yaml):

- Set `model.name_or_path` and `model.panovggt_checkpoint_path` to the initialization weights.
- Set `data.train_jsonl` to your selected training file.
- Set `data.train_image_root` to `./data`, because sample paths already start with `images/`.
- Adjust batch size, precision, learning rates, and attention implementation to your hardware.

Set `GPU_DEVICES` and a fresh `OUTPUT_DIR` in [`src/train/train.sh`](../src/train/train.sh), then launch:

```bash
bash src/train/train.sh
```

The launcher defines its settings in the file and does not accept command-line overrides. Its `OUTPUT_DIR` overrides `training.output_dir` in the YAML. Defaults are eight GPUs, per-device batch size 4, gradient accumulation 4, one epoch, BF16, gradient checkpointing, DeepSpeed ZeRO-2, and offline W&B logging. The nominal effective batch size is `number_of_GPUs × per_device_train_batch_size × gradient_accumulation_steps` (128 with the default eight GPUs).

| Configuration | Effect |
| --- | --- |
| `model.name_or_path` | Initialize from Qwen3.5-4B or fine-tune a compatible PanoVLN checkpoint |
| `model.trainable_modules` | Select visual tower, visual merger, language model, and PanoVGGT projection MLP |
| `model.panovggt_checkpoint_path` | External encoder initialization when the navigation checkpoint does not already contain it |
| `training.*_lr` | Separate learning rates for the language, visual, merger, and fusion modules |
| `training.deepspeed` | Defaults to `scripts/zero2.json` |
| `run.resume_from_checkpoint` | Resume from the latest `checkpoint-*` in the same output directory when `true` |
| `run.do_eval`, `training.eval_strategy` | Enable evaluation only after providing `data.eval_jsonl` and its images |

The PanoVGGT encoder remains frozen. Training saves `train.log`, periodic `checkpoint-*` directories (every 1,000 steps by default, retaining two), and the final model/processor/tokenizer in `OUTPUT_DIR`. Save a copy of the YAML and launcher with the run. Fine-tuning a model in a **new** directory uses `model.name_or_path`; resuming an interrupted run in the **same** directory uses `run.resume_from_checkpoint: true`.

Validation is disabled by default; `data/val.jsonl` is a user-provided file. To enable it, set `run.do_eval: true`, select an evaluation strategy such as `steps`, and provide the matching JSONL/image root. The [training guide](../src/train/README.md) describes fixed architecture metadata and the supported configuration options.

## Refine with DAgger

1. Train an initial navigation policy.
2. Set its checkpoint, `SOURCE_DATASET_NAMES`, GPUs, and output paths in [`scripts/generate_dagger_data.sh`](../scripts/generate_dagger_data.sh).
3. Collect new trajectories:

```bash
bash scripts/generate_dagger_data.sh
```

The collector writes trajectory annotations under `data/sub_dataset/dagger.jsonl` and the executed observations under `data/images/dagger/`. It uses 18-action oracle targets, an uncertainty range of 4–8 actions, and a 0.3 m final-goal tolerance. Collection defaults to eight GPUs with five processes per GPU; reduce concurrency and set a small `MAX_EPISODES` for an initial check. Completed episodes are skipped on subsequent runs.

Include `dagger` in `DATASET_NAMES` in `scripts/prepare_dataset.sh`. Configure training to start from the initial policy and write to a new output directory, then rebuild and fine-tune:

```bash
bash scripts/prepare_dataset.sh --overwrite
bash src/train/train.sh
```

## Deploy on a physical robot

Use **`PanoVLN_realworld`**, the checkpoint with enhanced trajectory recovery and collision avoidance. These capabilities support recovery from route deviations and responses to obstacles during physical navigation. The GPU server returns actions and action uncertainty; the Go2 client captures panoramas, selects history, executes the chosen action prefix, and records the trial.

### 1. Start the GPU server

On the Linux GPU machine, activate the model environment and run from the repository root:

```bash
conda activate panovln
hf download wangzhen-w/PanoVLN_realworld --local-dir checkpoints/PanoVLN_realworld
python -m pip install -r realworld/panovln/requirements.txt
bash realworld/panovln/run_server.sh
```

The settings at the top of [`run_server.sh`](../realworld/panovln/run_server.sh) are:

| Setting | Default / purpose |
| --- | --- |
| `MODEL_PATH` | `./checkpoints/PanoVLN_realworld` |
| `GPU_IDS` | `0`; GPU visible to the server |
| `HOST`, `PORT` | `0.0.0.0`, `8000`; listen address and port |
| `PYTHON_BIN` | `python3` from the active model environment |
| `ATTN_IMPLEMENTATION` | `flash_attention_2`; use `sdpa` if needed |
| `LOG_ROOT` | `./outputs/realworld_server/panovln` |
| `PANOVGGT_CHECKPOINT` | Empty for a complete navigation checkpoint; set an external path only when encoder weights are absent |

The server loads the model **before** starting HTTP. `/ready` and `/health` report the loaded model path, panoramic view mode, action-sequence length, and uncertainty support. Extra server flags are forwarded by the launcher; for example, `bash realworld/panovln/run_server.sh --attn-implementation sdpa` selects SDPA for that run.

### 2. Prepare the robot-side environment

On the Go2 client machine, use **ROS2 Foxy** and its compatible `/usr/bin/python3`. Install FFmpeg for the configured recorder, plus the Python dependencies:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg python3-pip python3-colcon-common-extensions
/usr/bin/python3 -m pip install -r realworld/panovln/requirements-client.txt

source /opt/ros/foxy/setup.bash
cd realworld/panovln/ros2_unitree_api_ws
colcon build --base-paths src --packages-select unitree_api unitree_go
cd ../../..
```

The launcher automatically sources the generated `install/setup.bash`. Keep it on the client or rebuild if it is removed. The included workspace provides message definitions; the Go2 sport API connection must already be available. Confirm the client can see `/api/sport/request`, `/api/sport/response`, and `/sportmodestate` in the ROS2 network. The last topic supplies odometry for the default closed-loop execution. If odometry is unavailable, the client can fall back to timed open-loop motion; check the client log when validating motion accuracy.

### 3. Configure one trial

Edit [`realworld/panovln/go2_client.yaml`](../realworld/panovln/go2_client.yaml). CLI arguments override YAML values.

| YAML field | What to set |
| --- | --- |
| `server.server_base_url` | Reachable GPU-server URL on port 8000. The supplied `127.0.0.1` is valid only when both processes share a host. |
| `experiment.scene_name`, `route_id`, `trial_id` | Environment, route, and repetition identifiers used in the output directory |
| `navigation.instruction` / `instruction_file` | Instruction text; a configured file takes precedence |
| `camera.camera` | Panorama camera device, default `/dev/video0` |
| `camera.frame_width`, `frame_height`, `camera_fps` | Camera capture format, defaults 2880×1440 at 30 FPS |
| `motion.forward_distance`, `turn_degrees` | Action units, 0.25 m / 15° |
| `motion.forward_speed`, `yaw_speed` | Execution speeds, defaults 0.35 m/s and 0.8 rad/s |
| `odometry.disable_odom_control` | `false` requests odometry-based control; calibrate tolerances and gains for the robot |
| `recording.save_output_dir`, `save_contents` | Output root and recording types; `all` additionally saves individual images |

Keep these policy defaults for the released deployment configuration:

```yaml
navigation:
  actions_per_replan: uncertainty
  uncertainty_budget: 1.2
  replan_action_range: [4, 8]
  stop_commit_max_actions: 12
  execution_mode: continuous
  prefetch_after_actions: 0
  history_limit: 120

upload:
  upload_max_memory_images: 10
  upload_memory_pool_window_frames: 100
  upload_image_mode: resize
  upload_width: 1280
  upload_height: 640
```

This is an excerpt; keep the other sections in the supplied YAML. The client sends up to 10 historical frames selected from the recent 100-frame window, plus the current panorama. In continuous mode, adjacent identical actions are merged while observations are captured after each original action unit. `stop_commit_max_actions` can commit through a predicted stop before the ordinary uncertainty limit.

Print the final configuration without opening the camera, contacting the server, or controlling the robot:

```bash
bash realworld/panovln/run_go2_client.sh --print-config
```

### 4. Check readiness and the camera/server path

From the robot-side machine, this reads the configured server URL and verifies that the model is ready:

```bash
/usr/bin/python3 - <<'PYREADY'
from pathlib import Path
import requests, yaml
config = yaml.safe_load(Path("realworld/panovln/go2_client.yaml").read_text())
url = config["server"]["server_base_url"].rstrip("/") + "/ready"
response = requests.get(url, timeout=10)
response.raise_for_status()
print(response.json())
PYREADY
```

Then run one inference cycle with **motion disabled**:

```bash
bash realworld/panovln/run_go2_client.sh \
  --control-backend dry-run --max-replans 1 \
  --scene-name office --route-id 1 --trial-id dry-run-01
```

This opens the camera, sends observations to the model server, records the trial, and prints the proposed control commands. It does not send ROS2 motion commands. Use a new trial ID if this output directory already exists.

### 5. Execute a robot trial

The supplied YAML selects `control_backend: ros2` and `real_robot_ack: "yes"`. After checking the instruction, camera, server, and motion settings, run the following only for an intended physical trial:

```bash
bash realworld/panovln/run_go2_client.sh \
  --control-backend ros2 --real-robot-ack yes \
  --scene-name office --route-id 1 --trial-id 1
```

This command can move the Go2. `Ctrl+C` triggers the client's stop and cleanup handler. The server can remain running between trials; change the instruction and increment `trial_id` when starting another run. The [shared deployment guide](../realworld/README.md) covers the included baseline server/client pairs. The [PanoVLN configuration/API reference](../realworld/panovln/README.md) documents precedence, control behavior, HTTP request/response fields, and troubleshooting.

### 6. Inspect trial outputs

```text
outputs/realworld/PanoVLN_office_1_1/
├── navigation.mp4
├── navigation.json
├── summary.json
└── images/                 # With save_contents: all

outputs/realworld_server/panovln/{timestamp}_{suffix}/
├── server.log
└── inference.jsonl
```

`navigation.json` records the instruction, execution configuration, predicted/executed actions, and request timings. `summary.json` includes `time_s`, `speed_mps`, call counts, latency, and waiting-time statistics. Speed is in m/s; multiply by 100 when reporting cm/s. Success (`sr`), final goal distance (`ne`), and pause count initially remain `null`: annotate success/distance after the trial and derive pauses from an explicit stationary-interval criterion using odometry or video. Insufficient odometry leaves distance-based speed unavailable. `inference.jsonl` records each server request and its timing; matching request IDs connect the client and server logs. Existing trial directories are not overwritten.

For every supported argument:

```bash
bash realworld/panovln/run_server.sh --help
bash realworld/panovln/run_go2_client.sh --help
```

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Model directory does not exist | Download the checkpoint and set `MODEL_PATH` in the launcher. |
| Missing tokenizer or processor | Download the complete model repository. |
| FlashAttention import/build failure | Use the compatible upstream build or switch the configuration to `sdpa`. |
| Scene or navigation mesh missing | Check the original scene files and `scenes_dir` in the Habitat YAML. |
| Training image not found | Render the selected dataset and use `./data` as the image root. |
| GPU out of memory | Reduce evaluation workers or training batch size. |
| An evaluation finishes with few new episodes | Check whether `SAVE_PATH` already contains completed results. |
| Robot cannot reach the model server | Use the server's reachable address and check the `/ready` endpoint. |

When opening an issue, include your commit, checkpoint, environment versions, launcher settings, and the smallest command that reproduces the problem.
