# 🚀 Render 502 Error - Quick Fix

## ✅ Files Already Updated

I've updated your project to work with Render. Here's what changed:

### 1. Updated `Dockerfile` ✅
- Uses `${PORT:-10000}` environment variable
- Added `curl` for health checks
- Increased timeout to 300 seconds
- Longer startup time (40s) for heavy FFmpeg processing

### 2. Created `render.yaml` ✅
- Auto-configures Render deployment
- Sets correct environment variables
- Configures health check
- Sets up disk storage for videos

### 3. Updated `main.py` ✅
- Already has PORT handling: `port = int(os.environ.get("PORT", 8000))`
- Added timeout settings for long video processing

---

## 🚀 Deploy to Render - 3 Steps

### Step 1: Commit & Push Changes

```bash
# Navigate to your project
cd D:\AndroidSdk\StudioProjects\ffmpeg-video-api

# Add all updated files
git add Dockerfile render.yaml main.py RENDER_DEPLOYMENT_GUIDE.md

# Commit
git commit -m "Fix Render deployment - add PORT binding and timeouts"

# Push to GitHub
git push origin main
```

### Step 2: Deploy on Render

**Option A: Using render.yaml (Recommended)**

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will read `render.yaml` and auto-configure everything
5. Click **"Apply"**

**Option B: Manual Setup**

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   ```
   Name: ffmpeg-video-api
   Environment: Docker
   Region: Oregon (or closest to you)
   Branch: main
   Instance Type: Starter (minimum $7/month)
   ```
5. In **"Advanced"** settings:
   - Health Check Path: `/health`
   - Docker Command: (leave blank, uses Dockerfile CMD)

6. Click **"Create Web Service"**

### Step 3: Monitor Deployment

1. **Watch the build logs** - takes 5-10 minutes
2. Look for:
   ```
   ✅ "Application startup complete"
   ✅ "Uvicorn running on http://0.0.0.0:10000"
   ```
3. Once deployed, test:
   ```bash
   curl https://your-app.onrender.com/health
   ```

---

## ⚠️ IMPORTANT: Plan Requirements

**Free Tier Won't Work** ❌

FFmpeg video processing requires:
- ✅ **Starter Plan**: $7/month (minimum)
- ✅ **Standard Plan**: $25/month (recommended for production)

**Why?**
- Free tier: 0.1 vCPU, 512MB RAM → crashes during video encoding
- Starter: 0.5 vCPU, 512MB RAM → works but slow
- Standard: 1 vCPU, 2GB RAM → smooth processing ✅

---

## 🐛 If Still Getting 502 Error

### Check Render Logs

1. Go to your service in Render Dashboard
2. Click **"Logs"** tab
3. Look for errors:

**Common errors:**

```bash
# Port binding issue
❌ "Address already in use"
✅ Fixed: Dockerfile now uses ${PORT:-10000}

# Missing dependencies
❌ "ModuleNotFoundError: No module named 'PIL'"
✅ Fixed: requirements.txt installed in Dockerfile

# FFmpeg missing
❌ "ffmpeg: command not found"
✅ Fixed: FFmpeg installed in Dockerfile

# Health check failing
❌ "Health check timeout"
✅ Fixed: Health check uses correct port and has 40s startup time

# Memory limit
❌ "Killed" or "Out of memory"
✅ Solution: Upgrade to Standard plan (2GB RAM)
```

### Test Endpoints

Once deployed, test these URLs:

```bash
# 1. Health check
curl https://your-app.onrender.com/health

# Should return:
{
  "status": "healthy",
  "ffmpeg": true,
  "service": "ffmpeg-video-api"
}

# 2. API Documentation
https://your-app.onrender.com/docs

# 3. Test video generation (use your actual URLs)
curl -X POST "https://your-app.onrender.com/generate-inspix-video" \
  -H "Content-Type: application/json" \
  -d '{
    "original_image_url": "https://picsum.photos/1200/1200",
    "result_image_urls": [
      "https://picsum.photos/1200/1200?random=1",
      "https://picsum.photos/1200/1200?random=2"
    ]
  }'
```

---

## 📊 Expected Deployment Timeline

```
Push to GitHub         →  Instant
Render detects change  →  ~30 seconds
Docker build starts    →  ~5-8 minutes (first time)
Deploy & health check  →  ~1 minute
Total                  →  ~6-10 minutes
```

**Subsequent deployments:** ~3-5 minutes (Docker cache)

---

## ✅ Success Checklist

After deployment, verify:

- [ ] Build completed successfully (green checkmark in Render)
- [ ] Logs show: "Application startup complete"
- [ ] Health endpoint returns: `{"status": "healthy", "ffmpeg": true}`
- [ ] API docs accessible at `/docs`
- [ ] Can generate a test video successfully
- [ ] No 502 errors when accessing the service

---

## 🆘 Still Not Working?

**Share with me:**

1. **Complete Render build logs** (from Render Dashboard → Logs)
2. **Error message** you're seeing
3. **Your Render plan** (Free/Starter/Standard)
4. **Screenshot** of the error

I'll provide a specific fix immediately.

---

## 💡 Tips for Production

### 1. Set Environment Variables

In Render Dashboard → Environment:

```
PORT=10000
MAX_FILE_SIZE=10485760
DOWNLOAD_TIMEOUT=120
VIDEO_TIMEOUT=300
```

### 2. Enable Auto-Deploy

Render Dashboard → Settings:
- ✅ Auto-Deploy: Yes
- Branch: main

Now every push to `main` auto-deploys!

### 3. Add Custom Domain (Optional)

Render Dashboard → Settings → Custom Domain:
- Add your domain (e.g., `api.yourdomain.com`)
- Follow DNS setup instructions

### 4. Monitor Performance

Render Dashboard → Metrics:
- CPU usage
- Memory usage
- Response times
- Request count

If you see high CPU/memory usage, upgrade to Standard plan.

---

## 🎯 Summary

**What was fixed:**
1. ✅ Dockerfile now uses Render's PORT environment variable
2. ✅ Added curl for health checks
3. ✅ Increased timeouts for video processing
4. ✅ Created render.yaml for easy deployment
5. ✅ Updated main.py with timeout settings

**Next steps:**
1. Commit and push changes to GitHub
2. Deploy on Render (Blueprint or Web Service)
3. Wait 6-10 minutes for first build
4. Test health endpoint
5. Generate test video

**Ready to deploy!** 🚀

Push your changes and Render will automatically build and deploy your service.
