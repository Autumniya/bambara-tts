#!/usr/bin/env bash
set -Eeuo pipefail

echo "=== GPU DIAG ==="
nvidia-smi || true
HAS_GPU=0
python - <<'PY' && HAS_GPU=1 || true
import torch; import sys; sys.exit(0 if torch.cuda.is_available() else 1)
PY
echo "HAS_GPU=$HAS_GPU"
echo "=== /GPU DIAG ==="

export HF_HOME=${HF_HOME:-/data/hfcache}
export HUGGINGFACE_HUB_CACHE=${HUGGINGFACE_HUB_CACHE:-$HF_HOME}
export TRANSFORMERS_CACHE=${TRANSFORMERS_CACHE:-$HF_HOME}
export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}
export AUDIO_DIR=${AUDIO_DIR:-/data/audio}
mkdir -p "$HF_HOME" "$AUDIO_DIR"

cleanup(){ pkill -TERM -P $$ || true; }
trap cleanup SIGTERM SIGINT

if [ "$HAS_GPU" = "1" ]; then
  echo "Starting Celery GPU worker…"
  celery -A app.celery worker --loglevel=INFO --concurrency=1 --prefetch-multiplier=1 \
    --include tasks_gpu &
else
  echo "No GPU detected → skipping Celery. (Web will still run.)"
fi

exec gunicorn app:app -b 0.0.0.0:${PORT:-8080} --workers=1 --threads=2 --timeout=120
