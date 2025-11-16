FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including FFmpeg and curl for health checks
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY test_inspix_api.py .
COPY example_request.json .

# Create necessary directories
RUN mkdir -p uploads outputs

# Expose port (Render will override with PORT env var)
EXPOSE 10000

# Health check - use curl and PORT env variable
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/health || exit 1

# Run the application - IMPORTANT: Use PORT environment variable from Render
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --timeout-keep-alive 300
