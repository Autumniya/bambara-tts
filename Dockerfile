FROM python:3.10-slim

# Install OS-level dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 ffmpeg espeak-ng \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Run the app with Gunicorn
CMD ["./start.sh"]
