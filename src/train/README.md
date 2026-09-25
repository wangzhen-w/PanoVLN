# Training configuration

The released navigation model uses panoramic observations and predicts 18 atomic
actions. When PanoVGGT is enabled, fusion uses aggregator features, post-merger
injection, and grouping. These are fixed architecture choices shared by training,
simulation, and real-world inference.

Edit `src/train/config/config.yaml` before running:

```bash
bash src/train/train.sh
```

The launcher runs from the repository root. Checkpoint and dataset paths are relative to
that root. Dataset paths default to `./data`;
point them to your own data and checkpoints:

| Asset | Default location |
| --- | --- |
| Initial Qwen model | `checkpoints/Qwen3.5-4B/` |
| Initial PanoVGGT weights | `checkpoints/PanoVGGT/model.pt` |
| Training annotations | `./data/train.jsonl` |
| Optional validation annotations | `./data/val.jsonl` |
| Training images | `./data/` |
| Optional validation images | `./data/` |
| Trained model | `checkpoints/PanoVLN/` |

Image roots point to the dataset root containing `images/`, since sample paths
already begin with `images/`. The optional validation JSONL is user-provided;
validation is disabled by default.

Each training sample must provide an 18-action target. Terminal targets are
padded with `stop`. The regular dataset preparation and DAgger workflows remain
available in `scripts/prepare_dataset.sh` and `scripts/generate_dagger_data.sh`.

`panovggt_enabled` remains configurable. ERP latitude cropping, fusion weight
`panovggt_alpha_value`, trainable modules, learning rates, and precision settings
also remain configurable. The PanoVGGT encoder stays frozen during policy training.

The saved model config records the fixed architecture as metadata. Existing
checkpoints with matching metadata remain supported; a checkpoint with a different
view, output length, feature source, injection stage, or sampling mode is rejected.
Legacy perspective settings that were unused by a panoramic checkpoint are ignored
and removed from the config when it is loaded.

`actions_per_replan` controls execution, independently of the 18 predicted actions.
Fixed execution lengths and the uncertainty policy remain available in simulation
and on the robot. Configure their settings in the evaluation/client launch files.
