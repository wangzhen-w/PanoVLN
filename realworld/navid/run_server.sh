#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"
# Edit deployment settings here before launching.
MODEL_PATH="./checkpoints/NaVid"
GPU_IDS="0"
HOST="0.0.0.0"
PORT="8000"
PYTHON_BIN="python3"
LOG_ROOT="./outputs/realworld_server/navid"

export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
export CUDA_VISIBLE_DEVICES="$GPU_IDS"
for arg in "$@"; do
    if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
        exec "$PYTHON_BIN" -m realworld.navid.server --help
    fi
done
mkdir -p "$LOG_ROOT"
LOG_DIR="$(mktemp -d "$LOG_ROOT/$(date -u +%Y%m%d_%H%M%S)_XXXXXX")"
exec > >(tee -i -a "$LOG_DIR/server.log") 2>&1
exec "$PYTHON_BIN" -m realworld.navid.server --host "$HOST" --port "$PORT" \
    --model-path "$MODEL_PATH" --log-dir "$LOG_DIR" "$@"
