# Trinity UI Production Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY trinity_app/ ./trinity_app/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TRINITY_ENGINE_URL=http://localhost:9000/api/chat
ENV PORT=8000

# Expose port (Render uses $PORT)
EXPOSE $PORT

# Run with PORT from environment
CMD uvicorn trinity_app.main:app --host 0.0.0.0 --port $PORT
