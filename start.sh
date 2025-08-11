#!/usr/bin/env bash
set -e

# Keep HF cache & audio on the mounted volume
export HF_HOME=${HF_HOME:-/data/hfcache}
export HUGGINGFACE_HUB_CACHE=${HUGGINGFACE_HUB_CACHE:-$HF_HOME}
export TRANSFORMERS_CACHE=${TRANSFORMERS_CACHE:-$HF_HOME}
export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}

# Celery worker (GPU) – include the tasks module so only the worker imports MALIBA
celery -A app.celery worker --loglevel=INFO --concurrency=1 --prefetch-multiplier=1 \
  --include tasks_gpu &

# Web API (no model import)
exec gunicorn app:app -b 0.0.0.0:${PORT:-8080} --workers=1 --threads=2 --timeout=120
