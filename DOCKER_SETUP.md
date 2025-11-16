# 🐳 Docker Setup Guide

## Quick Start with Docker

### Prerequisites
- Docker Desktop installed ([Download](https://www.docker.com/products/docker-desktop))
- Docker Compose (included with Docker Desktop)

## Option 1: Docker Compose (Recommended)

### Build and Run

```bash
# Navigate to project directory
cd D:\AndroidSdk\StudioProjects\ffmpeg-video-api

# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

The API will be available at `http://localhost:8000`

### Rebuild After Changes

```bash
docker-compose down
docker-compose up -d --build
```

## Option 2: Docker Commands

### Build the Image

```bash
docker build -t ffmpeg-video-api .
```

### Run the Container

```bash
docker run -d \
  --name ffmpeg-video-api \
  -p 8000:8000 \
  -v "%cd%/uploads:/app/uploads" \
  -v "%cd%/outputs:/app/outputs" \
  ffmpeg-video-api
```

### View Logs

```bash
docker logs -f ffmpeg-video-api
```

### Stop the Container

```bash
docker stop ffmpeg-video-api
docker rm ffmpeg-video-api
```

## Verify Installation

### Check Container Status

```bash
docker ps
```

### Test the API

```bash
# Check health
curl http://localhost:8000/health

# Or open in browser
start http://localhost:8000/docs
```

### Access Container Shell

```bash
# Using docker-compose
docker-compose exec ffmpeg-api bash

# Using docker directly
docker exec -it ffmpeg-video-api bash

# Inside container, verify installations:
ffmpeg -version
python -c "import PIL; print('Pillow installed')"
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs

# Or
docker logs ffmpeg-video-api
```

### Port Already in Use

Edit `docker-compose.yml` and change port:
```yaml
ports:
  - "8001:8000"  # Change 8000 to 8001
```

### Permission Issues with Volumes

On Windows, ensure Docker has access to the drive:
- Docker Desktop → Settings → Resources → File Sharing
- Add `D:\` drive

### Rebuild from Scratch

```bash
# Remove old containers and images
docker-compose down -v
docker rmi ffmpeg-video-api

# Rebuild
docker-compose up -d --build
```

## Development Workflow

### For Active Development

Use volume mounting to see code changes:

```yaml
# Add to docker-compose.yml
services:
  ffmpeg-api:
    volumes:
      - ./main.py:/app/main.py  # Mount main.py
```

Then restart:
```bash
docker-compose restart
```

### For Production

Use the standard build (no volume mounting for code).

## Environment Variables

Create `.env` file:

```env
PORT=8000
MAX_FILE_SIZE=10485760
DOWNLOAD_TIMEOUT=120
VIDEO_TIMEOUT=300
```

Add to `docker-compose.yml`:

```yaml
services:
  ffmpeg-api:
    env_file:
      - .env
```

## Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  ffmpeg-api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Useful Commands

```bash
# View all containers
docker ps -a

# View images
docker images

# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# View resource usage
docker stats

# Export logs
docker logs ffmpeg-video-api > logs.txt 2>&1
```

## API Usage from Host

Once running, test the API:

```bash
# PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get

# Or use the test script (install requests first)
pip install requests
python test_inspix_api.py
```

## Production Deployment

### Using Docker Hub

```bash
# Tag image
docker tag ffmpeg-video-api yourusername/ffmpeg-video-api:latest

# Push to Docker Hub
docker push yourusername/ffmpeg-video-api:latest

# Pull and run on server
docker pull yourusername/ffmpeg-video-api:latest
docker run -d -p 8000:8000 yourusername/ffmpeg-video-api:latest
```

### Using Docker Swarm / Kubernetes

For scaling, convert to orchestration config files.

## Complete Setup Example

```bash
# 1. Navigate to project
cd D:\AndroidSdk\StudioProjects\ffmpeg-video-api

# 2. Build and start
docker-compose up -d

# 3. Wait for startup (check logs)
docker-compose logs -f

# 4. Test health endpoint
curl http://localhost:8000/health

# 5. Open API docs
start http://localhost:8000/docs

# 6. Run test
python test_inspix_api.py

# 7. View generated videos
dir outputs\

# 8. Stop when done
docker-compose down
```

## Success Indicators

✅ Container shows as "healthy" in `docker ps`
✅ Health endpoint returns: `{"status": "healthy", "ffmpeg": true}`
✅ Swagger docs accessible at `/docs`
✅ Test script completes successfully
✅ Video files appear in `outputs/` directory

---

**Your API is now running in a containerized environment with all dependencies!** 🚀
