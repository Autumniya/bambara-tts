FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

# System deps for audio + optional OGG transcode
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 ffmpeg espeak-ng ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first for better layer caching
COPY requirements.txt /app/requirements.txt

# IMPORTANT: base image already has CUDA-enabled torch/torchaudio.
# Do NOT reinstall CPU wheels; keep requirements minimal.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of your app
COPY . /app

# Cache + audio dirs on a mounted volume
ENV HF_HOME=/data/hfcache
ENV AUDIO_DIR=/data/audio

# Make sure start script is executable
RUN chmod +x /app/start.sh

EXPOSE 8000
CMD ["./start.sh"]
