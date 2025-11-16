# 🚀 Render Deployment Guide - Fix 502 Gateway Error

## 🔍 Common Causes of 502 Error on Render

1. ❌ Application not binding to the correct port
2. ❌ Application crashed during startup
3. ❌ Missing dependencies (FFmpeg not installed)
4. ❌ Health check failing
5. ❌ Memory/CPU limits exceeded
6. ❌ Startup timeout (video processing is CPU-intensive)

---

## ✅ Step-by-Step Fix

### 1. Check Render Logs (MOST IMPORTANT)

In your Render dashboard:
1. Go to your service
2. Click **"Logs"** tab
3. Look for error messages

**Common errors you might see:**
```
ModuleNotFoundError: No module named 'PIL'
ffmpeg: command not found
Application failed to start
Bind failed: port already in use
```

**Share these logs with me** and I can provide a specific fix.

---

### 2. Update Your Render Configuration

Create `render.yaml` in your project root:

```yaml
services:
  - type: web
    name: ffmpeg-video-api
    env: docker
    region: oregon
    plan: standard  # IMPORTANT: Free tier won't handle FFmpeg processing
    dockerfilePath: ./Dockerfile
    dockerContext: .

    # Environment variables
    envVars:
      - key: PORT
        value: 10000  # Render uses port 10000 by default
      - key: MAX_FILE_SIZE
        value: 10485760
      - key: DOWNLOAD_TIMEOUT
        value: 120
      - key: VIDEO_TIMEOUT
        value: 300

    # Health check
    healthCheckPath: /health

    # Auto-deploy
    autoDeploy: true

    # Disk storage for uploads/outputs
    disk:
      name: video-storage
      mountPath: /app/outputs
      sizeGB: 10
```

---

### 3. Update Dockerfile for Render

**CRITICAL:** Render requires dynamic port binding.

Update your `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including FFmpeg
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

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/health || exit 1

# IMPORTANT: Use PORT environment variable from Render
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --timeout-keep-alive 300
```

**Key changes:**
- Uses `${PORT:-10000}` to get port from environment
- Longer startup time (40s) for heavy dependencies
- Increased timeout (300s) for video processing

---

### 4. Update main.py for Port Binding

Add this at the top of `main.py` to handle Render's port:

```python
import os

# Get port from environment (Render sets this)
PORT = int(os.environ.get("PORT", 8000))
```

Then at the bottom where you run uvicorn:

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,  # Use PORT from environment
        timeout_keep_alive=300
    )
```

---

### 5. Deploy to Render

#### Option A: Using Dashboard (Easier)

1. **Connect Repository:**
   - Go to Render Dashboard
   - Click "New +" → "Web Service"
   - Connect your GitHub/GitLab repo

2. **Configure Service:**
   ```
   Name: ffmpeg-video-api
   Environment: Docker
   Region: Oregon (or closest to you)
   Branch: main
   ```

3. **Instance Type:**
   - ⚠️ **Don't use Free tier** - FFmpeg needs resources
   - Minimum: **Starter ($7/month)**
   - Recommended: **Standard ($25/month)** for production

4. **Environment Variables:**
   ```
   PORT=10000
   ```

5. **Advanced Settings:**
   - Health Check Path: `/health`
   - Auto-Deploy: Yes

#### Option B: Using render.yaml (Recommended)

1. Add `render.yaml` to your repo (see Step 2)
2. Push to GitHub
3. In Render Dashboard: "New +" → "Blueprint"
4. Select your repo
5. Render will auto-configure from `render.yaml`

---

### 6. Check Health Endpoint

Make sure your `/health` endpoint works. Add this to `main.py` if missing:

```python
@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    try:
        # Check if FFmpeg is available
        ffmpeg_available = check_ffmpeg()

        return {
            "status": "healthy",
            "ffmpeg": ffmpeg_available,
            "service": "ffmpeg-video-api",
            "version": "1.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
```

---

### 7. Resource Considerations

**FFmpeg video processing is CPU/Memory intensive:**

| Plan | CPU | RAM | Video Processing |
|------|-----|-----|------------------|
| Free | 0.1 vCPU | 512 MB | ❌ Will crash/timeout |
| Starter | 0.5 vCPU | 512 MB | ⚠️ Slow, may timeout |
| Standard | 1 vCPU | 2 GB | ✅ Recommended |
| Pro | 2 vCPU | 4 GB | ✅ Best performance |

**For your use case (15-second videos with 4-10 images):**
- Minimum: Starter ($7/month)
- Recommended: Standard ($25/month)

---

## 🐛 Debugging Steps

### Step 1: Check Render Logs

In Render dashboard → Logs, look for:

```
✅ Good signs:
- "Application startup complete"
- "Uvicorn running on http://0.0.0.0:10000"
- "INFO: Started server process"

❌ Bad signs:
- "ModuleNotFoundError"
- "ffmpeg: command not found"
- "Address already in use"
- "Application failed to start"
```

### Step 2: Test Health Endpoint

Once deployed, test:
```bash
curl https://your-app.onrender.com/health
```

Should return:
```json
{
  "status": "healthy",
  "ffmpeg": true,
  "service": "ffmpeg-video-api"
}
```

### Step 3: Test API Documentation

Visit: `https://your-app.onrender.com/docs`

Should show Swagger UI.

### Step 4: Check Shell Access

In Render dashboard → Shell:
```bash
# Check FFmpeg
ffmpeg -version

# Check Python packages
pip list | grep -i pillow

# Check port binding
netstat -tulpn | grep 10000

# Check disk space
df -h
```

---

## 🔧 Common Issues & Fixes

### Issue 1: "Address already in use"

**Cause:** Port conflict

**Fix:**
```python
# In main.py, use environment PORT
PORT = int(os.environ.get("PORT", 8000))
```

### Issue 2: "ModuleNotFoundError: No module named 'PIL'"

**Cause:** requirements.txt not installed

**Fix:**
Ensure `Dockerfile` has:
```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

### Issue 3: "ffmpeg: command not found"

**Cause:** FFmpeg not installed in Docker image

**Fix:**
Ensure `Dockerfile` has:
```dockerfile
RUN apt-get update && apt-get install -y ffmpeg
```

### Issue 4: Health Check Failing

**Cause:** App not responding on correct port

**Fix:**
1. Check PORT env variable
2. Ensure `/health` endpoint exists
3. Increase startup timeout in render.yaml

### Issue 5: Timeout During Video Generation

**Cause:** Processing taking too long

**Fix:**
```python
# In main.py, increase timeout
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --timeout-keep-alive 300 --timeout-graceful-shutdown 300
```

### Issue 6: Memory Limit Exceeded

**Symptom:** 502 error during video generation

**Fix:**
- Upgrade to Standard plan (2GB RAM)
- Or optimize video processing (use lower resolution)

---

## 📝 Deployment Checklist

- [ ] `Dockerfile` uses `${PORT}` environment variable
- [ ] `requirements.txt` includes all dependencies
- [ ] `render.yaml` configured (or manual setup complete)
- [ ] Health check endpoint `/health` exists
- [ ] FFmpeg installed in Docker image
- [ ] Using Starter plan or higher (not Free)
- [ ] Pushed latest code to GitHub
- [ ] Checked Render logs for errors
- [ ] Tested health endpoint works
- [ ] Tested API docs at `/docs`

---

## 🚀 Quick Fix Commands

### Update Dockerfile
```bash
# Copy the updated Dockerfile from this guide
# Ensure it has: ${PORT:-10000}
```

### Commit and Push
```bash
git add Dockerfile render.yaml main.py
git commit -m "Fix Render deployment - use PORT env variable"
git push origin main
```

### Monitor Deployment
1. Go to Render Dashboard
2. Wait for build to complete (~5-10 minutes)
3. Check logs for "Application startup complete"
4. Test health endpoint

---

## 🆘 Still Getting 502?

**Share with me:**

1. **Complete Render logs** (last 100 lines)
2. **Your current Dockerfile**
3. **Render plan** (Free/Starter/Standard)
4. **Error screenshot** from Render dashboard

Then I can provide a specific fix!

---

## ✅ Success Indicators

When deployment works:

1. ✅ Build completes without errors
2. ✅ "Application startup complete" in logs
3. ✅ Health check passes: `https://your-app.onrender.com/health`
4. ✅ Swagger docs work: `https://your-app.onrender.com/docs`
5. ✅ Can generate test video successfully

---

**Ready to fix your deployment!** Share your Render logs and I'll help you debug the specific issue.
