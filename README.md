# 🎬 FFmpeg Video API - Inspix Implementation

A FastAPI-based video generation service that creates professional 15-second Instagram-ready videos with precise timeline control, transitions, and text overlays.

## ✨ Features

### New: Inspix Video Generation
- **15-second timeline** with 6 distinct segments
- **2x2 Hook Grid** opening with zoom effects
- **Dynamic results showcase** with multiple transition styles
- **Professional text overlays** with custom styling
- **Branding support** with logo overlay
- **Instagram-ready output** (1080x1920, 30fps, H.264 + AAC)

### Original Features
- Create videos from multiple image URLs
- Support for custom background music
- Configurable transitions and durations
- Text overlay support
- Automatic image downloading and validation

## 📋 Requirements

- **Python 3.8+**
- **FFmpeg** (must be installed and in PATH)
- **Dependencies:** FastAPI, aiohttp, Pillow, aiofiles

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install fastapi uvicorn aiohttp aiofiles pillow python-multipart
```

### 2. Install FFmpeg

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Mac:**
```bash
brew install ffmpeg
```

### 3. Run the Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

### 4. Access Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Inspix API Docs:** See `INSPIX_VIDEO_API.md`

## 🎯 API Endpoints

### Inspix Video Generation

**Endpoint:** `POST /generate-inspix-video`

**Request Body:**
```json
{
  "original_image_url": "https://example.com/original.jpg",
  "result_image_urls": [
    "https://example.com/result1.jpg",
    "https://example.com/result2.jpg",
    "https://example.com/result3.jpg",
    "https://example.com/result4.jpg"
  ],
  "prompt_preview_text": "A stunning sunset over mountains",
  "style_names": ["Cinematic", "Vibrant", "Moody", "Dramatic"],
  "logo_url": "https://example.com/logo.png",
  "custom_cta_text": "Link in Bio 👆"
}
```

**Response:**
```json
{
  "message": "Inspix video created successfully",
  "video_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "download_url": "/download/inspix_f47ac10b-58cc-4372-a567-0e02b2c3d479.mp4",
  "file_size_mb": 6.0,
  "duration_seconds": 15,
  "resolution": "1080x1920",
  "fps": 30
}
```

## 📖 Timeline Breakdown

### [0-1s] Hook Grid
- 2x2 grid of first 4 result images
- Each cell: 540x960px
- Quick zoom on each (0.25s per image)

### [1-3s] Original Photo
- Display original image centered
- Text: "This Photo +"
- Zoom animation (1.0 → 1.08)

### [3-5s] Prompt Tease
- Original image dimmed 30%
- Text: "+ inspix Prompt ="
- Show prompt preview (blurred)

### [5-12s] Results Showcase
- Sequential display of all results
- Dynamic timing: 7s ÷ number of results
- Transitions: fade, slideleft, circleopen, fadeblack
- Text: "Style: {name}" + counter

### [12-14s] Branding
- Last result dimmed 20%
- Text: "500+ Prompts Ready"
- Logo overlay (120x120px, 85% opacity)

### [14-15s] Call-to-Action
- Custom CTA text with pulse animation
- Logo remains visible

## 🧪 Testing

### Run the Test Script

```bash
python test_inspix_api.py
```

This will:
1. Check API health
2. Generate test videos with sample images
3. Download and save the generated video
4. Verify all functionality

### Manual Testing with cURL

```bash
curl -X POST "http://localhost:8000/generate-inspix-video" \
  -H "Content-Type: application/json" \
  -d @example_request.json
```

## 📁 Project Structure

```
ffmpeg-video-api/
├── main.py                    # Main FastAPI application
├── INSPIX_VIDEO_API.md        # Detailed API documentation
├── README.md                  # This file
├── example_request.json       # Example request payload
├── test_inspix_api.py         # Test script
├── uploads/                   # Temporary upload directory
└── outputs/                   # Generated video outputs
```

## 🎨 Text Styling Specifications

### Font Configuration
- **Font:** Arial Bold (`/Windows/Fonts/arialbd.ttf`)
- **Main text:** 80pt, white, 4px black stroke
- **Secondary text:** 64pt, white, 3px black stroke
- **Small text:** 48pt, white, 2px black stroke

### Customization
Text styles are defined in the helper functions:
- `create_hook_grid()` - No text
- `create_original_photo_segment()` - "This Photo +"
- `create_prompt_tease_segment()` - Prompt text
- `create_results_showcase()` - Style names + counters
- `create_branding_segment()` - "500+ Prompts Ready"
- `create_cta_segment()` - Custom CTA text

## ⚙️ Configuration

### Constants in `main.py`

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MIN_IMAGE_DIMENSION = 800          # Minimum width/height
DOWNLOAD_TIMEOUT = 120             # Image download timeout (seconds)
VIDEO_TIMEOUT = 300                # Video generation timeout (seconds)
```

### Video Output Settings

```python
fps = 30                           # Frame rate
resolution = "1080x1920"           # Portrait (9:16)
codec = "libx264"                  # H.264 video codec
audio_codec = "aac"                # AAC audio codec
preset = "medium"                  # Encoding speed/quality balance
crf = 23                           # Quality (lower = better, 18-28 range)
```

## 🔧 Troubleshooting

### FFmpeg Not Found
```
Error: FFmpeg not available
```
**Solution:** Install FFmpeg and ensure it's in your system PATH

### Image Download Failures
```
Error: Failed to download image: HTTP 404
```
**Solution:** Verify URLs are accessible and return valid images

### Image Too Small
```
Error: Image dimensions 600x600 below minimum 800px
```
**Solution:** Use images that are at least 800x800px

### Timeout Errors
```
Error: Request timed out
```
**Solution:** Increase client timeout to 300+ seconds (video generation is CPU-intensive)

### Memory Issues
**Solution:**
- Reduce number of result images
- Use smaller source images (1080x1080 recommended)
- Ensure adequate disk space for temp files

## 📊 Performance

### Processing Times
- **1-4 result images:** ~60-90 seconds
- **5-7 result images:** ~90-120 seconds
- **8-10 result images:** ~120-180 seconds

### Optimization Tips
1. Use JPEG format (smaller than PNG)
2. Pre-optimize images to 1080x1080
3. Use CDN-hosted images for faster downloads
4. Run on systems with good CPU performance

## 🔒 Production Considerations

### Security
- [ ] Add authentication/API keys
- [ ] Rate limiting (e.g., 10 requests/minute)
- [ ] Input sanitization for text fields
- [ ] File upload size limits
- [ ] CORS configuration for specific origins

### Scalability
- [ ] Use task queue (Celery/RQ) for async processing
- [ ] Add Redis for job status tracking
- [ ] Implement video caching
- [ ] Set up cleanup cron jobs for old videos
- [ ] Add monitoring and logging

### Deployment
```bash
# Production server with Gunicorn + Uvicorn workers
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

## 📝 Example Usage

### Python Client

```python
import requests

# Generate video
response = requests.post(
    "http://localhost:8000/generate-inspix-video",
    json={
        "original_image_url": "https://example.com/photo.jpg",
        "result_image_urls": [
            "https://example.com/style1.jpg",
            "https://example.com/style2.jpg",
            "https://example.com/style3.jpg",
            "https://example.com/style4.jpg"
        ],
        "style_names": ["Cinematic", "Vibrant", "Moody", "Dramatic"]
    },
    timeout=300
)

result = response.json()
print(f"Video ready: {result['download_url']}")

# Download video
video = requests.get(f"http://localhost:8000{result['download_url']}")
with open("output.mp4", "wb") as f:
    f.write(video.content)
```

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Video processing powered by [FFmpeg](https://ffmpeg.org/)
- Image handling with [Pillow](https://pillow.readthedocs.io/)

## 📞 Support

For issues and questions:
- Check the `INSPIX_VIDEO_API.md` for detailed documentation
- Review logs for error messages
- Open an issue on GitHub

---

**Made with ❤️ for content creators**
