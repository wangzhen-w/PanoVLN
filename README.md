<div align="center">

# 🧭 PanoVLN

### Learning Vision-and-Language Navigation in 360°

**Panoramic observations · Geometry-aware action prediction · Confidence-guided execution**

<p>
  <a href="#overview"><img src="https://img.shields.io/badge/Vision-360%C2%B0_Panoramas-0F766E?style=flat-square" alt="360-degree panoramic vision — overview" /></a>
  <a href="#model-zoo"><img src="https://img.shields.io/badge/Backbone-Qwen3.5--4B-6366F1?style=flat-square" alt="Qwen3.5-4B backbone — model zoo" /></a>
  <a href="#evaluation"><img src="https://img.shields.io/badge/Simulation-Habitat-2563EB?style=flat-square" alt="Habitat simulation — evaluation guide" /></a>
  <a href="realworld/README.md"><img src="https://img.shields.io/badge/Robot-Unitree_Go2-334155?style=flat-square" alt="Unitree Go2 — real-world deployment" /></a>
</p>

[Getting Started](#getting-started) · [Data Preparation](#data-preparation) · [Training](#training) · [Evaluation](#evaluation) · [Real-World Deployment](realworld/README.md) · [Model Zoo](#model-zoo)

</div>

---

<a name="overview"></a>

PanoVLN follows natural-language navigation instructions using **360° RGB panoramas**. It combines a vision-language model with a frozen panoramic geometry encoder, predicts sequences of navigation actions, and adapts how many actions to execute before observing the environment again.

This repository includes data preparation, supervised training, DAgger collection, Habitat evaluation, and a client–server deployment for the Unitree Go2.

The training data is available on [Hugging Face](https://huggingface.co/datasets/wangzhen-w/PanoVLN), and model checkpoints are linked in the [Model Zoo](#model-zoo).

| | What is included |
| :--- | :--- |
| 🌐 **Panoramic perception** | Current and historical ERP observations provide visual context around the agent. |
| 🧩 **Semantic–geometric fusion** | PanoVGGT aggregator features are spatially grouped and fused into the VLM's current-image tokens after the visual merger. |
| 🎯 **Confidence-guided execution** | Predict 18 actions, then select an execution prefix using action uncertainty before replanning. |
| 🛠️ **Data-to-robot workflow** | Trajectory and instruction generation, DAgger, simulation evaluation, and recorded real-world trials. |

The action vocabulary is `forward` (0.25 m), `left` (15°), `right` (15°), and `stop`. Training targets contain exactly **18 actions**, with terminal targets padded using `stop`. The prediction length and the number of actions executed per model call are separate.

<a name="getting-started"></a>

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/wangzhen-w/PanoVLN.git
cd PanoVLN
```

Run the following commands from the repository root unless a step says otherwise.

### 2. Set up the model environment

Use Linux with an NVIDIA GPU. Create the environment and install the core dependencies:

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

Install a compatible [FlashAttention 2 build](https://github.com/Dao-AILab/flash-attention#installation-and-features), or select `sdpa` in the model settings. Choose [PyTorch CUDA wheels](https://pytorch.org/get-started/previous-versions/) compatible with your machine.

<details>
<summary><b>Habitat setup — needed for rendering, DAgger, and simulation evaluation</b></summary>

Install **Habitat-Sim 0.3.3** with rendering support. Follow its [versioned build instructions](https://github.com/facebookresearch/habitat-sim/blob/v0.3.3/BUILD_FROM_SOURCE.md); use a headless build on servers without a display.

Install the matching Habitat-Lab and Habitat-Baselines packages into the same environment:

```bash
git clone --branch v0.3.3 https://github.com/facebookresearch/habitat-lab.git ../habitat-lab
python -m pip install -e ../habitat-lab/habitat-lab -e ../habitat-lab/habitat-baselines
python -m pip install fastdtw networkx imageio imageio-ffmpeg opencv-python
```

</details>

### 3. Download model weights

See the [Model Zoo](#model-zoo). Training starts from Qwen3.5-4B and PanoVGGT; evaluation and deployment require a trained PanoVLN checkpoint.

Before running a bash launcher, edit its settings at the top for your Python environment, GPUs, and local paths.

<a name="data-preparation"></a>

## 🗂️ Data Preparation

### 1. Obtain scenes and navigation annotations

Download the **[PanoVLN training dataset](https://huggingface.co/datasets/wangzhen-w/PanoVLN)** from Hugging Face and follow the dataset repository instructions to prepare the released files.

For **R2R-CE** and **RxR-CE**, follow the [VLN-CE dataset instructions](https://github.com/jacobkrantz/VLN-CE#data). Obtain the corresponding Matterport3D scene assets separately. Creating additional PanoVLN trajectories requires [HM3D scenes](https://aihabitat.org/datasets/hm3d/).

All dataset paths are relative to the repository root, with `data/` as the default data root. Place your dataset there, or create a symlink at that location to an existing dataset directory. Arrange the downloaded files as follows; keep the split subdirectories in R2R, RxR, and HM3D:

```text
data/
├── general_vln_dataset/
│   ├── r2r/
│   │   ├── train/
│   │   │   └── train.json.gz
│   │   ├── val_seen/
│   │   │   └── val_seen.json.gz
│   │   └── val_unseen/
│   │       └── val_unseen.json.gz
│   ├── rxr/
│   │   ├── train/
│   │   │   └── train_guide.json.gz
│   │   ├── val_seen/
│   │   │   └── val_seen_guide.json.gz
│   │   └── val_unseen/
│   │       └── val_unseen_guide.json.gz
│   └── panovln/
│       └── train.json.gz
├── scene/
│   ├── hm3d/
│   │   ├── train/
│   │   │   ├── 00000-kfPV7w3FaU5/
│   │   │   ├── 00001-UVdNNRcVyV1/
│   │   │   └── ...
│   │   └── val/
│   │       └── ...
│   └── mp3d/
│       ├── 17DRP5sb8fy/
│       ├── 1LXtFkjw3qL/
│       └── ...
├── images/
│   ├── r2r/
│   │   └── <episode_id>/
│   │       └── frame_0.jpg
│   ├── rxr/
│   │   └── <episode_id>/
│   │       └── frame_0.jpg
│   ├── panovln/
│   │   └── <episode_id>/
│   │       └── frame_0.jpg
│   └── dagger/
│       └── <trajectory_id>/
│           └── frame_0.jpg
├── sub_dataset/
│   ├── r2r.jsonl
│   ├── rxr.jsonl
│   ├── panovln.jsonl
│   └── dagger.jsonl
└── train.jsonl                           # Generated 18-action training samples
```

Only the datasets used in your run are required. Keep the original scene assets and their navigation meshes. The paths in [`config/`](config/) follow this layout.

### 2. Generate action annotations and panoramic frames

Data scripts process **R2R and RxR by default**. Change `DATASET_NAMES` at the top of each script to select other datasets (`SOURCE_DATASET_NAMES` for DAgger collection).

Run preprocessing and frame extraction in order:

```bash
bash scripts/preprocess.sh
bash scripts/extract_frame.sh
```

Annotations are saved to `data/sub_dataset/`, and images to `data/images/`. Skip the corresponding step if these files are already prepared.

### 3. Prepare the training file

Build the training JSONL with [`scripts/prepare_dataset.sh`](scripts/prepare_dataset.sh):

```bash
bash scripts/prepare_dataset.sh
```

The default output is `data/train.jsonl`, containing 18-action training samples.

<a name="custom-data"></a>

To create new PanoVLN trajectories and instructions, follow the [dataset-generation guide](dataset_create/README.md).

<a name="training"></a>

## 🏋️ Training

Set your model and data paths in [`src/train/config/config.yaml`](src/train/config/config.yaml), then choose the GPUs and output directory in [`src/train/train.sh`](src/train/train.sh).

```bash
bash src/train/train.sh
```

The model is saved to the launcher's output directory. See the [training guide](src/train/README.md) for configuration details.

<a name="dagger"></a>

### DAgger refinement

After training an initial policy, select that checkpoint and the source datasets in [`scripts/generate_dagger_data.sh`](scripts/generate_dagger_data.sh):

```bash
bash scripts/generate_dagger_data.sh
```

Then include `dagger` in `scripts/prepare_dataset.sh`. Configure training to start from the initial policy and save to a new output directory, then rebuild the training file and fine-tune:

```bash
bash scripts/prepare_dataset.sh --overwrite
bash src/train/train.sh
```

<a name="evaluation"></a>

## 📊 Evaluation

<a name="benchmark-results"></a>

### Reported benchmark results

Val-Unseen results from the manuscript. NE is in meters; all other scores are percentages. † denotes training without navigation data beyond R2R-CE and RxR-CE.

| Checkpoint | R2R NE ↓ | R2R OS ↑ | R2R SR ↑ | R2R SPL ↑ | RxR NE ↓ | RxR SR ↑ | RxR SPL ↑ | RxR nDTW ↑ |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PanoVLN† (`PanoVLN_base`) | 3.10 | 79.7 | 73.9 | 67.9 | 3.14 | 74.1 | 63.9 | 71.4 |
| **PanoVLN** (`PanoVLN`) | **2.83** | **83.1** | **77.3** | **70.6** | **2.85** | **78.0** | **65.9** | 73.3 |

### Run simulation evaluation

Set the checkpoint, GPUs, and output directory in [`scripts/eval_r2r.sh`](scripts/eval_r2r.sh) or [`scripts/eval_rxr.sh`](scripts/eval_rxr.sh), then run the corresponding benchmark:

```bash
# R2R-CE
bash scripts/eval_r2r.sh

# RxR-CE
bash scripts/eval_rxr.sh
```

The script saves per-episode results to `result.jsonl` and aggregate metrics to `result_summary.json` in the selected output directory. Use a separate directory for each experiment.

<a name="real-world"></a>

## 🤖 Real-World Deployment

Deploy PanoVLN on a Unitree Go2 with a GPU inference server and panoramic-camera robot client. See the **[real-world deployment guide](realworld/README.md)** for environment setup, checkpoint configuration, ROS message compilation, navigation, and experiment recording.

## 🙏 Acknowledgements

PanoVLN builds on [Qwen](https://github.com/QwenLM/Qwen3.5), [PanoVGGT](https://github.com/YijingGuo-June/PanoVGGT), [Habitat](https://github.com/facebookresearch/habitat-lab), and the [VLN-CE](https://github.com/jacobkrantz/VLN-CE) ecosystem. We thank their authors for making their work available. Bundled third-party components retain their original license notices.

<a name="model-zoo"></a>

## 🤗 Model Zoo

| Model | Role | Repository / weights | Suggested local path |
| :--- | :--- | :--- | :--- |
| **PanoVLN** | Full-data checkpoint for simulation benchmarks | [Hugging Face](https://huggingface.co/wangzhen-w/PanoVLN) | `checkpoints/PanoVLN/` |
| **PanoVLN Base (†)** | R2R/RxR-only navigation-data checkpoint | [Hugging Face](https://huggingface.co/wangzhen-w/PanoVLN_base) | `checkpoints/PanoVLN_base/` |
| **PanoVLN Real World** | Robot deployment with enhanced trajectory recovery and collision avoidance | [Hugging Face](https://huggingface.co/wangzhen-w/PanoVLN_realworld) | `checkpoints/PanoVLN_realworld/` |
| Qwen3.5-4B | VLM initialization for training | [Hugging Face](https://huggingface.co/Qwen/Qwen3.5-4B) | `checkpoints/Qwen3.5-4B/` |
| PanoVGGT | Frozen panoramic geometry encoder | [Upstream checkpoint](https://huggingface.co/YijingGuo/PanoVGGT) | `checkpoints/PanoVGGT/model.pt` |

Use `PanoVLN` to reproduce the full-data simulation results and `PanoVLN_base` for the PanoVLN† results.

For physical robot deployment, we provide a dedicated **`PanoVLN_realworld`** checkpoint with two enhancements:

- **Trajectory recovery:** Improved ability to recover from deviations and resume following the navigation instruction.
- **Collision avoidance:** Improved ability to avoid obstacles during navigation.

These enhancements address recovery and collision avoidance during physical execution, which motivates a separate deployment checkpoint. Use `PanoVLN_realworld` with the [real-world deployment guide](realworld/README.md); use the simulation checkpoints above to reproduce the reported benchmark results.

Use a fully saved PanoVLN checkpoint, including its tokenizer and processor files, for evaluation or deployment.
