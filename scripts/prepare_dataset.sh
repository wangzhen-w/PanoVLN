#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"
echo "Switched to project root: $PROJECT_ROOT"

export PYTHONPATH="./:${PYTHONPATH:-}"
export MAGNUM_LOG="quiet"
export GLOG_minloglevel="3"
export HABITAT_LAB_LOG="50"
export PYTHONWARNINGS="ignore"

PYTHON_BIN="python"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "Python executable not found in PATH: ${PYTHON_BIN}" >&2
    exit 1
fi

INPUT_ROOT="./data"
OUTPUT_PATH="./data/train.jsonl"
DATASET_NAMES=(r2r rxr)  # Edit this array to select the datasets to include.

PREPARE_CMD=(
    "${PYTHON_BIN}" src/data/prepare_training_data.py
    --input_root "${INPUT_ROOT}"
    --dataset_name "${DATASET_NAMES[@]}"
    --output_path "${OUTPUT_PATH}"
    --seed 42
)
PREPARE_CMD+=("$@")

echo "INPUT_ROOT: ${INPUT_ROOT}"
echo "OUTPUT_PATH: ${OUTPUT_PATH}"
echo "DATASET_NAMES: ${DATASET_NAMES[*]}"
echo "ACTION_HORIZON: 18"
echo "EXECUTION_HORIZON: 6"
echo "R2R_RXR_RULE: non-stop stride6 + multi-turn-onset + long-forward"
echo "PANOVLN_RULE: non-stop stride12 + per-episode-random-offset[0-11] + keep-start0"
echo "STOP_RULE: positions[1-12] keep80% + positions[13-18] keep40%; deterministic per window"
echo "DAGGER_RULE: keep-all-h18-oracle-decisions-with-executed-history"
printf 'Running:'
printf ' %q' "${PREPARE_CMD[@]}"
printf '\n'
"${PREPARE_CMD[@]}"
