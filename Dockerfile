# Trinity UI - Minimal Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install base dependencies
RUN apt-get update && apt-get install -y gcc g++ ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app
COPY trinity_app ./trinity_app

# Port
EXPOSE 8000

# Simple shell entry - works reliably
ENTRYPOINT ["/bin/sh", "-c", "python -m uvicorn trinity_app.main:app --host 0.0.0.0 --port 8000"]

