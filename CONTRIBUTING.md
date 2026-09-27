# Contributing to PanoVLN

We welcome fixes and improvements to installation, reproducibility, data generation, evaluation, and robot deployment.

## Ask a question or report a bug

Open a [GitHub issue](https://github.com/wangzhen-w/PanoVLN/issues). For a bug report, include:

- The repository commit and checkpoint name.
- OS, Python, PyTorch, Transformers, CUDA, and Habitat versions relevant to the failure.
- GPU model and the selected worker or batch settings.
- The command, configuration changes, expected result, and actual result.
- A concise traceback or log excerpt with credentials and private paths removed.

For benchmark discrepancies, include the dataset split, checkpoint, seed, execution-policy settings, output summary, and number of completed episodes.

## Propose a change

For a substantial feature or a change to model behavior, open an issue first so the scope can be agreed upon. Small fixes can go directly to a pull request.

1. Fork the repository and create a branch for the change.
2. Keep the change focused and update the relevant documentation.
3. Validate the affected workflow and describe the environment and result in the pull request.
4. Link the issue, if applicable, and explain the behavior before and after the change.

Match the surrounding code style. Keep configuration defaults, saved checkpoint metadata, and execution behavior consistent across training, simulation, and robot inference when a change affects them.

## Validate your contribution

Choose checks that exercise the changed behavior. For a launcher edit, check shell syntax and run the relevant command in its supported environment. For model or evaluation changes, include a small reproducible run before attempting a full benchmark. For documentation, check links, paths, and commands against the actual code.

Report which checks ran and which require hardware or data you do not have. A documentation-only change does not require a training run.

## Files to keep local

Keep model weights, scene assets, generated datasets, run logs, credentials, and robot recordings out of pull requests. The repository ignores `data/`, `checkpoints/`, and `outputs/`; store your experiment artifacts there or outside the repository.

Retain third-party license notices when modifying bundled code. Repository-wide code licensing is pending an author decision; see the [license section](README.md#license) and resource cards for the current status.

## Share a deployment

Share the robot and camera setup, checkpoint, configuration, inference hardware, and a brief result in a GitHub issue. Include reproducible setup steps so another contributor can follow them. Obtain permission before sharing recordings that contain other people or private spaces.
