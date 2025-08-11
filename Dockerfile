FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime
RUN apt-get update && apt-get install -y ffmpeg libsndfile1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PORT=8000 PORT_HEALTH=8000 HF_HUB_ENABLE_HF_TRANSFER=1 SPEAKER_DEFAULT=Bourama
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
