# Base image selection
FROM python:3.11-slim

# Setup runtime environment variable configurations
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies (FFmpeg is required by frame extraction tasks)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Optimize pip installation layers
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add non-root appuser system accounts for container security isolation
RUN useradd --create-home appuser && \
    chown -R appuser:appuser /app
USER appuser

# Copy application code into container workspace
COPY --chown=appuser:appuser app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

