#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"
# Edit deployment settings here before launching.
MODEL_PATH="./checkpoints/PanoVLN_realworld"
GPU_IDS="0"
HOST="0.0.0.0"
PORT="8000"
PYTHON_BIN="python3"
LOG_ROOT="./outputs/realworld_server/panovln"
ATTN_IMPLEMENTATION="flash_attention_2"
PANOVGGT_CHECKPOINT="" # Set if the VLN checkpoint does not include PanoVGGT weights.

export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
export CUDA_VISIBLE_DEVICES="$GPU_IDS"
for arg in "$@"; do
    if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
        exec "$PYTHON_BIN" -m realworld.panovln.server --help
    fi
done
mkdir -p "$LOG_ROOT"
LOG_DIR="$(mktemp -d "$LOG_ROOT/$(date -u +%Y%m%d_%H%M%S)_XXXXXX")"
exec > >(tee -i -a "$LOG_DIR/server.log") 2>&1
EXTRA_ARGS=(--attn-implementation "$ATTN_IMPLEMENTATION")
if [[ -n "$PANOVGGT_CHECKPOINT" ]]; then
    EXTRA_ARGS+=(--panovggt-checkpoint "$PANOVGGT_CHECKPOINT")
fi
exec "$PYTHON_BIN" -m realworld.panovln.server --host "$HOST" --port "$PORT" \
    --model-path "$MODEL_PATH" --log-dir "$LOG_DIR" "${EXTRA_ARGS[@]}" "$@"
