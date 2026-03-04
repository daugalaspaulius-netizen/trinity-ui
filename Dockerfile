# Trinity UI + Backend Production Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY trinity_app/ ./trinity_app/
COPY README.md .

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TRINITY_ENGINE_URL=http://localhost:9000/api/chat

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/', timeout=5)"

# Run the application
CMD ["uvicorn", "trinity_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
