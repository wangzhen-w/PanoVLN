<a id="readme-top"></a>
<div align="center">
  <h1>PanoVLN</h1>
  <h3>Towards Effective Panoramic Vision-and-Language Navigation</h3>

  <p>
    Zhen Wang<sup>1</sup> · Changpeng Wang<sup>1</sup> · Zhe Liu<sup>2</sup> · Zhangyang Qi<sup>2</sup><br />
    Yuxiang Lu<sup>2</sup> · Zimo Zeng<sup>1</sup> · Donglian Qi<sup>1</sup> · Xi Chen<sup>2</sup><br />
    <sup>1</sup>Zhejiang University &nbsp;&nbsp; <sup>2</sup>The University of Hong Kong
  </p>

  <p>
    <a href="https://wangzhen-w.github.io/PanoVLN/"><img src="https://img.shields.io/badge/HomePage-Explore-0066CC?style=flat-square&logo=googlechrome&logoColor=white" alt="Project homepage" /></a>
    <a href="https://arxiv.org/abs/2609.34759"><img src="https://img.shields.io/badge/arXiv-2609.34759-B31B1B?style=flat-square&logo=arxiv&logoColor=white" alt="arXiv:2609.34759" /></a>
    <a href="https://github.com/wangzhen-w/PanoVLN/stargazers"><img src="https://img.shields.io/github/stars/wangzhen-w/PanoVLN?style=flat-square&color=2955E8" alt="GitHub stars" /></a>
    <a href="https://github.com/wangzhen-w/PanoVLN/issues"><img src="https://img.shields.io/github/issues/wangzhen-w/PanoVLN?style=flat-square&color=102C43" alt="Open issues" /></a>
  </p>
  <p>
    <a href="https://huggingface.co/wangzhen-w/PanoVLN"><img src="https://img.shields.io/badge/🤗_Model-PanoVLN-E6B94B?style=flat-square" alt="PanoVLN model" /></a>
    <a href="https://huggingface.co/wangzhen-w/PanoVLN_base"><img src="https://img.shields.io/badge/🤗_Model-PanoVLN_Base-E6B94B?style=flat-square" alt="PanoVLN Base model" /></a>
    <a href="https://huggingface.co/wangzhen-w/PanoVLN_realworld"><img src="https://img.shields.io/badge/🤗_Model-Real_World-E6B94B?style=flat-square" alt="PanoVLN Real World model" /></a>
    <a href="https://huggingface.co/datasets/wangzhen-w/PanoVLN"><img src="https://img.shields.io/badge/🤗_Dataset-PanoVLN-E6B94B?style=flat-square" alt="PanoVLN training data" /></a>
  </p>

</div>

https://github.com/user-attachments/assets/2ca7c19a-fc3a-4a7e-b298-9d9e195b6a5f

## Contents

[Getting Started](#getting-started) · [Training Data](#data-preparation) · [Dataset Construction](#dataset-construction) · [Models](#model-zoo) · [Training](#training) · [Evaluation](#evaluation) · [Robot Deployment](#real-world-deployment) · [Configuration](#customization) · [Citation](#citation)

<a id="introduction"></a>
## 🏠 Introduction

**PanoVLN** is a vision-and-language navigation policy that follows instructions from 360° RGB observations. It combines a Qwen3.5-4B backbone with PanoVGGT geometry features and predicts 18-action sequences. Confidence-guided execution selects how far to move before observing and planning again.

This repository provides **training and data-generation code, Habitat evaluation, three released checkpoints, and a GPU-server/Go2-client deployment pipeline**. For physical navigation, **PanoVLN Real World adds trajectory recovery and collision avoidance**, helping the robot handle route deviations and obstacles during execution.

| Task | Entry point |
| --- | --- |
| Evaluate a released checkpoint | [Environment](#getting-started) → [data layout](#data-preparation) → [evaluation](#evaluation) |
| Train or fine-tune | [Training data](#data-preparation) → [training](#training) |
| Deploy on a Unitree Go2 | [Real-world deployment](#real-world-deployment) |
| Generate new trajectories and instructions | [Dataset-generation guide](dataset_create/README.md) |
| Read the method and full results | [Paper on arXiv](https://arxiv.org/abs/2609.34759) · [project page](https://wangzhen-w.github.io/PanoVLN/) |

<a id="news"></a>
## 🔥 News

- **2026-09-25:** Source code released, including training, data generation, simulation evaluation, and robot deployment.
- **Available:** [Three checkpoints](#model-zoo), [training annotations](https://huggingface.co/datasets/wangzhen-w/PanoVLN), and the [project page](https://wangzhen-w.github.io/PanoVLN/) with a real-world navigation video and main results.
- **2026-09-28:** The [paper](https://arxiv.org/abs/2609.34759) is available on arXiv.

<a id="getting-started"></a>
## 📚 Getting Started

Training and model inference use **Linux with an NVIDIA GPU**. The model environment uses Python 3.12, PyTorch 2.10.0, and Transformers 5.5.0. Simulation additionally uses Habitat-Sim / Habitat-Lab **0.3.3**; the Go2 client uses its separate ROS2 environment.

```bash
git clone https://github.com/wangzhen-w/PanoVLN.git
cd PanoVLN
conda create -n panovln python=3.12 -y
conda activate panovln

python -m pip install torch==2.10.0 torchvision==0.25.0
python -m pip install \
  transformers==5.5.0 accelerate==1.13.0 peft==0.18.1 \
  deepspeed==0.18.0 numpy pillow pyyaml tqdm scipy einops timm \
  omegaconf huggingface-hub safetensors wandb
```

Choose [PyTorch CUDA wheels](https://pytorch.org/get-started/locally/) for your driver. Install [FlashAttention 2](https://github.com/Dao-AILab/flash-attention#installation-and-features) for the supplied launchers, or select `sdpa` in their attention settings. Follow the [Habitat installation steps](docs/reproduction.md#habitat-setup) before rendering or evaluation. PanoVLN runs directly from the repository; its launchers set `PYTHONPATH`.

Download the simulation model:

```bash
hf download wangzhen-w/PanoVLN --local-dir checkpoints/PanoVLN
```

Keep the checkpoint directory, including tokenizer, processor, and configuration files. See the [reproduction guide](docs/reproduction.md) for installation checks, exact configuration, outputs, and troubleshooting.

<a id="data-preparation"></a>
## 🗂️ Data Preparation

### 1. Obtain scenes and navigation annotations

Download the **[PanoVLN training dataset](https://huggingface.co/datasets/wangzhen-w/PanoVLN)** from Hugging Face and follow the dataset repository instructions to prepare the released files.

```bash
hf download wangzhen-w/PanoVLN --repo-type dataset --local-dir data
```

The download contains navigation annotations and training JSONL files. Obtain scene assets separately and render the required panoramic images.

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
├── train_r2r_rxr.jsonl                   # R2R + RxR mixture
├── r2r_rxr_dagger.jsonl                  # R2R + RxR + DAgger mixture
├── r2r_rxr_dagger_panovln.jsonl          # Full mixture
└── train.jsonl                          # Mixture selected in the training config
```

Only the datasets used in your run are required. Keep the original scene assets and their navigation meshes. The paths in [`config/`](config/) follow this layout.

`general_vln_dataset/` holds navigation episodes; `scene/` holds simulator scene assets. `sub_dataset/` holds action-aligned annotations, and `images/` holds their panoramic observations. The JSONL files at the data root are prepared training mixtures. Only evaluation episodes and scenes are needed to evaluate a checkpoint.

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

The default output is `data/train.jsonl`, containing 18-action training samples. If you use a released mixture, select it directly in `data.train_jsonl` in [`src/train/config/config.yaml`](src/train/config/config.yaml):

| Training stage | JSONL file | Sources |
| --- | --- | --- |
| Initial policy | `data/train_r2r_rxr.jsonl` | R2R-CE + RxR-CE |
| PanoVLN Base (†), including DAgger refinement | `data/r2r_rxr_dagger.jsonl` | R2R-CE + RxR-CE + corrective trajectories |
| Full PanoVLN | `data/r2r_rxr_dagger_panovln.jsonl` | The above + the constructed PanoVLN dataset |
| Custom mixture | `data/train.jsonl` | Generated from `DATASET_NAMES` in `scripts/prepare_dataset.sh` |

Set `data.train_image_root` to `data/`: sample image paths already start with `images/`. Render all image sources selected by the mixture. See the [training-data preparation guide](docs/reproduction.md#prepare-training-data) for regeneration and DAgger.

<a id="dataset-construction"></a>
## Dataset Construction

To **create new trajectories and language instructions from HM3D scenes**, use [`dataset_create/`](dataset_create/). Its guide covers scene inspection, trajectory collection and replay validation, instruction generation, and export of panoramic training images. This is separate from preparing or selecting the released training mixtures above.

<a id="benchmark-and-model-zoo"></a>
<a id="model-zoo"></a>
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

```bash
hf download wangzhen-w/PanoVLN --local-dir checkpoints/PanoVLN
# Alternatives: PanoVLN_base or PanoVLN_realworld, with the matching local directory.
```

[Main benchmark results](https://wangzhen-w.github.io/PanoVLN/#results) are shown on the project page.

<a id="training"></a>
## 🚀 Training

### Initialize and train

```bash
hf download Qwen/Qwen3.5-4B --local-dir checkpoints/Qwen3.5-4B
hf download YijingGuo/PanoVGGT --local-dir checkpoints/PanoVGGT
```

Configure the following before launching:

| File | Settings |
| --- | --- |
| [`src/train/config/config.yaml`](src/train/config/config.yaml) | `model.name_or_path`, `model.panovggt_checkpoint_path`, `data.train_jsonl`, `data.train_image_root`, batch size, attention, and learning rates |
| [`src/train/train.sh`](src/train/train.sh) | `GPU_DEVICES`, `CONFIG_PATH`, and a fresh `OUTPUT_DIR` |

Defaults use `checkpoints/Qwen3.5-4B/`, `checkpoints/PanoVGGT/model.pt`, `data/train.jsonl`, and `data/`. The launcher defaults to eight GPUs; set the GPU list and batch size for your machine. The PanoVGGT encoder remains frozen while the selected language, visual, and fusion modules are trained.

```bash
bash src/train/train.sh
```

`OUTPUT_DIR` receives `train.log`, periodic `checkpoint-*` directories, and the final model/tokenizer/processor. Validation is disabled by default. The launcher takes its settings from the files above and rejects command-line overrides; see the [training guide](docs/reproduction.md#train-a-model) for batch-size accounting, validation, and resuming.

### DAgger and fine-tuning

Set the trained `MODEL_PATH`, source datasets, GPUs, and output paths in [`scripts/generate_dagger_data.sh`](scripts/generate_dagger_data.sh), then collect corrective trajectories:

```bash
bash scripts/generate_dagger_data.sh
```

Include `dagger` in `DATASET_NAMES` in [`scripts/prepare_dataset.sh`](scripts/prepare_dataset.sh), point `model.name_or_path` to the starting navigation checkpoint, and use a new training output directory:

```bash
bash scripts/prepare_dataset.sh --overwrite
bash src/train/train.sh
```

The [reproduction guide](docs/reproduction.md#refine-with-dagger) explains the generated annotations, images, and mixture selection.

<a id="evaluation"></a>
## 📈 Evaluation

Edit [`scripts/eval_r2r.sh`](scripts/eval_r2r.sh) or [`scripts/eval_rxr.sh`](scripts/eval_rxr.sh). For a first R2R run, set these variables **inside the launcher**:

```bash
MODEL_PATH="./checkpoints/PanoVLN"
GPU_IDS="0"
PROCS_PER_GPU=1
TOTAL_MAX_EPISODES=5
SAVE_PATH="./outputs/eval/r2r_smoke"
```

Then launch the selected benchmark:

```bash
bash scripts/eval_r2r.sh
# For RxR, configure the other launcher and use a separate SAVE_PATH:
# bash scripts/eval_rxr.sh
```

Set `TOTAL_MAX_EPISODES=0` for the complete split. Both launchers default to `val_unseen`, uncertainty-based execution, and a 4–8-action range. Preserve their benchmark-specific stop settings when reproducing reported results. Each worker loads a model; adjust `PROCS_PER_GPU` to available memory.

| Output | Contents |
| --- | --- |
| `result.jsonl` | Per-episode metrics and predicted/executed action histories |
| `result_summary.json` | Episode count, success, SPL, oracle success, distance to goal, path length, and nDTW |
| `top_down/` | Per-episode videos when `SAVE_TOPDOWN=true` |

Existing episodes are skipped on resume. Use a new `SAVE_PATH` for each checkpoint or policy configuration. See [evaluation settings](docs/reproduction.md#evaluate-a-checkpoint) for single-worker commands and output interpretation.

<a id="real-world-deployment"></a>
## 🤖 Real-world Deployment

Use **[PanoVLN_realworld](https://huggingface.co/wangzhen-w/PanoVLN_realworld)** with a GPU inference server and a panoramic-camera Unitree Go2 client. This checkpoint adds **trajectory recovery** after route deviations and **collision avoidance** during physical execution.

Follow **[`realworld/`](realworld/)** for hardware and environment setup, checkpoint configuration, server startup, ROS2 client setup, navigation and trial recording. The [PanoVLN reference](realworld/panovln/README.md) documents configuration fields and the prediction API.

<a id="customization"></a>
## 🔧 Configuration

| Change | Edit |
| --- | --- |
| Checkpoint, data mixture, trainable modules, precision, learning rates | [`src/train/config/config.yaml`](src/train/config/config.yaml) |
| Training GPUs and output directory | [`src/train/train.sh`](src/train/train.sh) |
| Evaluation workers, memory window, and execution policy | [`scripts/eval_r2r.sh`](scripts/eval_r2r.sh), [`scripts/eval_rxr.sh`](scripts/eval_rxr.sh) |
| Dataset split, scene paths, panoramic sensor | [`config/`](config/) |
| Preprocessing, rendering, and custom data mixtures | `DATASET_NAMES` in [`scripts/`](scripts/) |
| Robot server address, camera, instruction, motion, recording | [`realworld/panovln/go2_client.yaml`](realworld/panovln/go2_client.yaml) |

Action targets contain **18 words** from `forward` (0.25 m), `left` (15°), `right` (15°), and `stop`; terminal targets are padded with `stop`. `actions_per_replan` controls the executed prefix independently. The [training configuration guide](src/train/README.md) documents the architecture constraints, ERP cropping, and fusion options.

<a id="citation"></a>
## 🔗 Citation

If you use PanoVLN, please cite our paper.

```bibtex
@misc{wang2026panovln,
  title  = {PanoVLN: Towards Effective Panoramic Vision-and-Language Navigation},
  author = {Zhen Wang and Changpeng Wang and Zhe Liu and Zhangyang Qi and
            Yuxiang Lu and Zimo Zeng and Donglian Qi and Xi Chen},
  year   = {2026},
  eprint = {2609.34759},
  archivePrefix = {arXiv},
  primaryClass = {cs.CV},
  doi    = {10.48550/arXiv.2609.34759},
  url    = {https://arxiv.org/abs/2609.34759}
}
```

Machine-readable citation metadata is available in [CITATION.cff](CITATION.cff).

<a id="license"></a>
## 📄 License

Video music credits are listed in [assets/README.md](assets/README.md).

The repository-wide code license is pending an author decision. Bundled third-party components retain their [PanoVGGT](src/panovggt/LICENSE), [NaVid](realworld/navid/licenses/LICENSE), and [NaVILA](realworld/navila/licenses/LICENSE) license notices.

The released Hugging Face model and dataset cards specify **Matterport Academic Use** terms. Consult each resource's card and the [Matterport academic-use agreement](https://matterport.com/legal/matterport-end-user-license-agreement-academic-use-model-data) before use. Obtain source scenes under their respective access and license terms.

<a id="acknowledgements"></a>
## 🙏 Acknowledgements

PanoVLN builds on [Qwen](https://github.com/QwenLM/Qwen3.5), [PanoVGGT](https://github.com/YijingGuo-June/PanoVGGT), [Habitat](https://github.com/facebookresearch/habitat-lab), and [VLN-CE](https://github.com/jacobkrantz/VLN-CE). We thank their authors and the dataset contributors for making these resources available.
