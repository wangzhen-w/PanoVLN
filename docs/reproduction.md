# Reproducing PanoVLN

[Back to the repository](../README.md) · [Training configuration](../src/train/README.md) · [Robot deployment](../realworld/README.md)

This guide covers environment setup, simulation evaluation, training data, and DAgger refinement. Run commands from the repository root unless a step says otherwise. Edit settings directly in the supplied launchers before running them; most launchers define their paths and GPU choices inside the script.

## Install the environment

Use Linux and an NVIDIA GPU. Create the Python environment and install the core versions recorded for this repository:

```bash
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

### Habitat setup

Rendering, DAgger collection, and simulation evaluation require **Habitat-Sim 0.3.3** with rendering support. Follow its [versioned installation instructions](https://github.com/facebookresearch/habitat-sim/tree/v0.3.3); select the headless build on a server without a display.

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

Download each model directory in full, including configuration, tokenizer, and processor files. A complete PanoVLN checkpoint includes the geometry encoder; separate initialization weights are used when starting training from Qwen.

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

Only prepare the datasets needed by your run. Simulation evaluation needs the relevant evaluation split and scene assets; it renders observations online and does not need the training image folders. The scene and annotation paths are defined in [`config/`](../config/).

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

### Execution settings

The model predicts 18 actions. The launchers independently control how many to execute before requesting a new panorama:

| Setting | Meaning |
| --- | --- |
| `ACTIONS_PER_REPLAN="uncertainty"` | Select an execution prefix from action confidence |
| `ACTIONS_PER_REPLAN=6` | Use a fixed six-action execution prefix |
| `REPLAN_ACTION_RANGE=(4 8)` | Inclusive bounds in uncertainty mode |
| `UNCERTAINTY_BUDGET=1.2` | Confidence budget for prefix selection |
| `STOP_COMMIT_MAX_ACTIONS` | Commit to an early predicted stop within this window |
| `COLLISION_RECOVERY_STEPS` | Consecutive collision threshold for recovery |

Retain the supplied benchmark-specific settings when reproducing the reported results. R2R and RxR use different stop-commit windows.

## Prepare training data

### 1. Download released annotations

The [Hugging Face dataset](https://huggingface.co/datasets/wangzhen-w/PanoVLN) contains per-dataset annotations, prepared training JSONL files, and PanoVLN navigation episodes:

```bash
hf download wangzhen-w/PanoVLN --repo-type dataset --local-dir data
```

The release contains annotation files. Obtain scenes separately and render the corresponding images before training.

### 2. Prepare per-dataset actions and images

If the required `data/sub_dataset/*.jsonl` files are already downloaded, keep them and proceed to frame extraction. To regenerate R2R/RxR action annotations from source navigation episodes, edit `DATASET_NAMES` and the hardware settings in [`scripts/preprocess.sh`](../scripts/preprocess.sh), then run:

```bash
bash scripts/preprocess.sh
```

Select the datasets whose images are needed in [`scripts/extract_frame.sh`](../scripts/extract_frame.sh). Its default is `DATASET_NAMES=(r2r rxr)`; add `panovln` and/or `dagger` for those annotations. Set `GPU_IDS` and `PROCESSES_PER_GPU` for your machine, then run:

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

To generate additional trajectories and instructions, follow the [dataset-generation guide](../dataset_create/README.md).

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

The launcher defines its settings in the file and does not accept command-line overrides. It saves the trained model and `train.log` to `OUTPUT_DIR`. Validation is disabled by default; enabling it requires your own validation JSONL and matching images. The [training guide](../src/train/README.md) describes architecture constraints and supported parameters.

## Refine with DAgger

1. Train an initial navigation policy.
2. Set its checkpoint, `SOURCE_DATASET_NAMES`, GPUs, and output paths in [`scripts/generate_dagger_data.sh`](../scripts/generate_dagger_data.sh).
3. Collect new trajectories:

```bash
bash scripts/generate_dagger_data.sh
```

Include `dagger` in `DATASET_NAMES` in `scripts/prepare_dataset.sh`. Configure training to start from the initial policy and write to a new output directory, then rebuild and fine-tune:

```bash
bash scripts/prepare_dataset.sh --overwrite
bash src/train/train.sh
```

## Deploy on a physical robot

Use `PanoVLN_realworld` and follow the [real-world deployment guide](../realworld/README.md). It covers the GPU server, ROS2 robot client, Unitree message build, camera settings, readiness check, navigation, and trial recording.

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
