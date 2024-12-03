# Use a lightweight Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt /app/

# Install system dependencies required for Coqui TTS
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    && apt-get clean

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download and cache the Coqui TTS model
RUN python3 -m TTS.server.server --model_name tts_models/bam/fairseq/vits

# Copy the rest of the application files
COPY . /app

# Expose the port your Flask app runs on
EXPOSE 8080

# Define the command to run the Flask app
CMD ["python", "app.py"]
