# Creating the PanoVLN dataset

All available HM3D scenes contribute to one training dataset. PanoVLN does not split these scenes into training and validation sets. The `train/` and `val/` directories in the original HM3D assets remain part of the scene paths; they do not determine how PanoVLN uses a scene.

## Directory layout

```text
./data/general_vln_dataset/panovln/
├── trajectory/
│   ├── trajectories.json.gz       # Source actions, poses, and decision events
│   └── trajectories_stats.json
├── train.json
├── train.json.gz                   # Standard R2R format; all episodes are for training
└── .work/                         # Checkpoints used during generation
    ├── trajectory/
    └── instruction/
```

The scene root is `./data/scene/hm3d/`. Keep each scene under its original `train/<scene>/` or `val/<scene>/` path. Training images are written to `./data/images/panovln/<episode_id>/frame_<i>.jpg`, following the layout used by training. The `sub_dataset/` layout stays the same.

Source trajectories are stored separately from the final R2R file so their actions and decision metadata are preserved. The `.work/` directories support resuming either generation stage after an interruption; each stage removes its checkpoints after successful completion. Images, videos, and compass views are produced for the current trajectory as needed. The final outputs retain only the training ERP images and R2R files. The source trajectory file remains available for action alignment.

## Generate trajectories

Set the scene root, output, GPUs, and run mode at the top of [create_trajectories.sh](create_trajectories.sh). By default, the script scans every HM3D scene with both a GLB and a NavMesh and collects them into one `trajectory/trajectories.json.gz` file. `SCENE_IDS=()` selects all scenes; set a list of IDs to select specific scenes.

Run from the repository root:

```bash
./dataset_create/create_trajectories.sh inspect
./dataset_create/create_trajectories.sh collect
./dataset_create/create_trajectories.sh validate
```

Collection first partitions navigation regions, then uses panoramic depth to identify meaningful branches, and finally samples natural shortest paths between regions. A route must pass a valid decision. Routes with the same decision sequence and similar region structure keep only one representative coordinate variant. The process does not add artificial decision waypoints or enforce a fixed trajectory quota per scene.

Each trajectory records its start, goal, actual stop pose, region and connection sequences, primitive actions, and decision events. An event's `action_index` is the number of actions executed before reaching that state. Replaying `action_ids[:action_index]` reproduces the corresponding pose.

Completed scenes have separate checkpoints. Rerunning `collect` after an interruption reuses them. An existing complete trajectory file is retained by default; set `OVERWRITE=true` to recollect it. `validate` independently replays every action and checks decision poses, final poses, collisions, and goal arrival. It removes trajectory checkpoints only after all checks pass.

## Generate instructions and images

[create_instructions.sh](create_instructions.sh) reads the unified trajectory file by default. It uses GPUs 0–7 and 16 Habitat processes, with up to nine concurrent trajectories per process and an API concurrency limit of 144. `LIMIT=0` processes all trajectories. Only unfinished tasks are batched by scene; idle processes take the next batch from a shared queue. API waits can overlap, while each process renders sequentially on its main thread, keeping at most two simulators on each GPU.

```bash
./dataset_create/create_instructions.sh inspect
./dataset_create/create_instructions.sh generate
```

The pipeline has five stages: natural segmentation, visual evidence, local language generation, light editing, and local verification. After verification, it exports clean ERP images and standard R2R data. Trajectories that cannot be described or verified clearly are quarantined. See the [instruction generation guide](instruction/README.md) for details.

Rerun the same command after an interruption. Do not delete `.work/instruction` while generation is incomplete. Completed trajectories are skipped; unfinished trajectories reuse saved local text and model responses. Final outputs are the images under `images/panovln/` and `train.json` plus `train.json.gz` under `general_vln_dataset/panovln/`.

## Merge existing trajectory collections

Two existing collections were merged into a unified training input of **105,307 trajectories**. Of 900 inspected scenes, 872 produced qualifying trajectories. Every trajectory kept its original ID, actions, poses, decision events, and stop position; no routes were recollected or replanned.

The production entry point reads only the unified trajectory file, so existing trajectories do not need to be regenerated.

[trajectory/merge.py](trajectory/merge.py) can merge collections with matching parameters and disjoint scene sets. It checks IDs and per-scene counts and combines statistics. Replay conclusions inherited from unchanged source trajectories are marked as inherited, rather than presented as a new full replay.

```bash
python -m dataset_create.trajectory.merge \
  --datasets ./data/first.json.gz ./data/second.json.gz \
  --stats ./data/first_stats.json ./data/second_stats.json \
  --output-root ./data/general_vln_dataset/panovln/trajectory
```
