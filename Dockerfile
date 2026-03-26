FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    SPEAKER_DEFAULT=Bourama \
    HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

RUN useradd -m -u 1000 user && \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

USER user
WORKDIR $HOME/app

COPY --chown=user requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      torch==2.7.1 \
      torchvision==0.22.1 \
      torchaudio==2.7.1 \
      --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=user app ./app
RUN mkdir -p data/audio

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
