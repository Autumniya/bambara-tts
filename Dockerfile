# Use a CUDA runtime image with PyTorch preinstalled
FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 ffmpeg espeak-ng && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN chmod +x /app/start.sh

# Python deps (torch already present in base image)
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1
CMD ["./start.sh"]
