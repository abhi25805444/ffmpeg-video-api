# 🎬 Inspix Video Generation API

## Overview

This API generates 15-second Instagram-ready videos following a precise timeline with professional transitions, text overlays, and branding elements.

## Endpoint

**POST** `/generate-inspix-video`

## Technical Specifications

### Video Output
- **Resolution:** 1080x1920 (9:16 portrait)
- **Frame Rate:** 30fps
- **Codec:** H.264 (libx264)
- **Audio:** Silent AAC track (required for Instagram)
- **Duration:** Exactly 15 seconds
- **File Size:** ~5-8MB (optimized quality)
- **Format:** MP4 with faststart flag

### Timeline Breakdown

#### [0-1s] Hook Grid
- Creates 2x2 grid from first 4 result images
- Each cell: 540x960px
- Quick zoom effect on each image (0.25s per image)
- No text overlays
- Grabs viewer attention immediately

#### [1-3s] Original Photo
- Displays `original_image_url` centered
- Scaled to 70% of screen height
- Text overlay: "This Photo +"
- Zoom animation: 1.0 → 1.08 scale
- Font: Arial Bold, 80pt, white with black stroke (4px)

#### [3-5s] Prompt Tease
- Original image visible but dimmed by 30%
- Text overlay: "+ inspix Prompt ="
- Shows `prompt_preview_text` (48pt font)
- Auto-generated if not provided
- Creates curiosity and engagement

#### [5-12s] Results Showcase
- Shows each result image sequentially
- **Dynamic timing:** 7 seconds ÷ number of results
- **Transitions:** fade, slideleft, circleopen, fadeblack (cycles)
- **Text overlays:**
  - "Style: {style_name}" at top (64pt)
  - Counter "1/4", "2/4", etc. at bottom (48pt)
- Ken Burns zoom effect (1.0 → 1.05) on each image

#### [12-14s] Branding
- Last result image visible (dimmed 20%)
- Text: "500+ Prompts Ready" (72pt)
- Logo overlay if provided:
  - Position: Top-right corner
  - Size: 120x120px
  - Opacity: 85%
- Fade-in animation (0.5s)

#### [14-15s] Call-to-Action
- Shows `custom_cta_text` or default "Link in Bio 👆"
- Font size: 80pt, white with black stroke (4px)
- Pulse animation (scale 1.0 → 1.05 → 1.0)
- Logo remains visible if provided

## Request Format

### JSON Body

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

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `original_image_url` | string | ✅ Yes | URL of the original photo to showcase |
| `result_image_urls` | array[string] | ✅ Yes | 1-10 URLs of AI-generated result images |
| `prompt_preview_text` | string | ❌ No | Text to display in prompt tease segment (auto-generated if omitted) |
| `style_names` | array[string] | ❌ No | Names for each style (must match result count, auto-generated if omitted) |
| `logo_url` | string | ❌ No | URL of logo to overlay (120x120px recommended) |
| `custom_cta_text` | string | ❌ No | Custom call-to-action text (defaults to "Link in Bio 👆") |

## Validation Requirements

### Image URLs
- ✅ Must return HTTP 200 status
- ✅ Content-Type must be `image/*`
- ✅ Minimum dimensions: 800x800px
- ✅ Maximum file size: 10MB per image
- ✅ Download timeout: 120 seconds

### URL Array Counts
- `result_image_urls`: 1-10 images required
- `style_names`: Must match `result_image_urls` count (if provided)

## Response Format

### Success Response (200 OK)

```json
{
  "message": "Inspix video created successfully",
  "video_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "download_url": "/download/inspix_f47ac10b-58cc-4372-a567-0e02b2c3d479.mp4",
  "file_size": 6291456,
  "file_size_mb": 6.0,
  "duration_seconds": 15,
  "resolution": "1080x1920",
  "fps": 30,
  "format": "mp4",
  "codec": "H.264",
  "audio": "AAC (silent)",
  "images_processed": {
    "original": 1,
    "results": 4,
    "logo": 1
  }
}
```

### Error Responses

#### 400 Bad Request
```json
{
  "detail": "Failed to download result image 2: Image dimensions 600x600 below minimum 800px"
}
```

Common causes:
- Invalid URL format
- Image too small (< 800px)
- Invalid content type
- Download timeout
- Style names count mismatch

#### 503 Service Unavailable
```json
{
  "detail": "FFmpeg not available"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Failed to generate video"
}
```

## Text Styling Specifications

### Font Requirements
- **Font Family:** Arial Bold / Helvetica Bold
- **Fallback:** `/Windows/Fonts/arialbd.ttf`

### Text Sizes
- **Main text:** 80pt, white, 4px black stroke
- **Secondary text:** 64pt, white, 3px black stroke
- **Small text:** 48pt, white, 2px black stroke

## Usage Examples

### Python (requests)

```python
import requests

url = "http://localhost:8000/generate-inspix-video"
data = {
    "original_image_url": "https://example.com/photo.jpg",
    "result_image_urls": [
        "https://example.com/style1.jpg",
        "https://example.com/style2.jpg",
        "https://example.com/style3.jpg",
        "https://example.com/style4.jpg"
    ],
    "prompt_preview_text": "Epic cinematic transformation",
    "style_names": ["Cinematic", "Vibrant", "Moody", "Dramatic"],
    "logo_url": "https://example.com/logo.png",
    "custom_cta_text": "Download Now! 👇"
}

response = requests.post(url, json=data)
result = response.json()

print(f"Video ID: {result['video_id']}")
print(f"Download: {result['download_url']}")
print(f"Size: {result['file_size_mb']} MB")

# Download the video
video_url = f"http://localhost:8000{result['download_url']}"
video_response = requests.get(video_url)
with open(f"video_{result['video_id']}.mp4", "wb") as f:
    f.write(video_response.content)
```

### JavaScript (fetch)

```javascript
const generateVideo = async () => {
  const response = await fetch('http://localhost:8000/generate-inspix-video', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      original_image_url: 'https://example.com/photo.jpg',
      result_image_urls: [
        'https://example.com/style1.jpg',
        'https://example.com/style2.jpg',
        'https://example.com/style3.jpg',
        'https://example.com/style4.jpg'
      ],
      prompt_preview_text: 'Epic cinematic transformation',
      style_names: ['Cinematic', 'Vibrant', 'Moody', 'Dramatic'],
      logo_url: 'https://example.com/logo.png',
      custom_cta_text: 'Download Now! 👇'
    })
  });

  const result = await response.json();
  console.log('Video created:', result);

  // Download the video
  const videoUrl = `http://localhost:8000${result.download_url}`;
  window.open(videoUrl, '_blank');
};

generateVideo();
```

### cURL

```bash
curl -X POST "http://localhost:8000/generate-inspix-video" \
  -H "Content-Type: application/json" \
  -d '{
    "original_image_url": "https://example.com/photo.jpg",
    "result_image_urls": [
      "https://example.com/style1.jpg",
      "https://example.com/style2.jpg",
      "https://example.com/style3.jpg",
      "https://example.com/style4.jpg"
    ],
    "prompt_preview_text": "Epic cinematic transformation",
    "style_names": ["Cinematic", "Vibrant", "Moody", "Dramatic"],
    "logo_url": "https://example.com/logo.png",
    "custom_cta_text": "Download Now! 👇"
  }'
```

## Error Handling

### Best Practices

1. **Validate URLs before sending:**
   ```python
   from urllib.parse import urlparse

   def is_valid_url(url):
       try:
           result = urlparse(url)
           return all([result.scheme, result.netloc])
       except:
           return False
   ```

2. **Check image dimensions:**
   - Ensure all images are at least 800x800px
   - Recommended: 1080x1080px or larger for best quality

3. **Handle timeouts:**
   - Set client timeout to at least 300 seconds
   - Video generation can take 60-180 seconds depending on image count

4. **Retry logic:**
   ```python
   import time

   def generate_with_retry(data, max_retries=3):
       for attempt in range(max_retries):
           try:
               response = requests.post(url, json=data, timeout=300)
               response.raise_for_status()
               return response.json()
           except requests.exceptions.RequestException as e:
               if attempt < max_retries - 1:
                   time.sleep(2 ** attempt)  # Exponential backoff
                   continue
               raise
   ```

## Performance Considerations

### Processing Time
- **1-4 results:** ~60-90 seconds
- **5-7 results:** ~90-120 seconds
- **8-10 results:** ~120-180 seconds

### Optimization Tips
1. Use images that are already optimized (not too large)
2. Ensure stable internet connection for image downloads
3. Pre-validate image URLs and dimensions
4. Use JPEG format for better compression (PNG works but is larger)

## Troubleshooting

### Common Issues

**Issue:** "FFmpeg not available"
- **Solution:** Install FFmpeg and ensure it's in system PATH
  ```bash
  # Windows (using Chocolatey)
  choco install ffmpeg

  # Or download from: https://ffmpeg.org/download.html
  ```

**Issue:** "Image dimensions below minimum"
- **Solution:** Ensure all images are at least 800x800px
- Check image dimensions before uploading

**Issue:** "Download timeout"
- **Solution:**
  - Use CDN-hosted images for faster downloads
  - Check image URLs are accessible
  - Verify network connectivity

**Issue:** "Failed to create [segment] segment"
- **Solution:**
  - Check FFmpeg installation
  - Ensure enough disk space (temp files can be 100-500MB)
  - Check logs for detailed error messages

## API Endpoints Reference

### Generate Inspix Video
- **URL:** `/generate-inspix-video`
- **Method:** `POST`
- **Auth:** None
- **Content-Type:** `application/json`

### Download Video
- **URL:** `/download/{filename}`
- **Method:** `GET`
- **Auth:** None
- **Returns:** `video/mp4`

### Health Check
- **URL:** `/health`
- **Method:** `GET`
- **Returns:** Server status and FFmpeg availability

### List Videos
- **URL:** `/list-videos`
- **Method:** `GET`
- **Returns:** List of all generated videos

### Cleanup Video
- **URL:** `/cleanup/{video_id}`
- **Method:** `DELETE`
- **Returns:** Deletion confirmation

## Instagram Compatibility

### Video Specs
✅ Resolution: 1080x1920 (9:16)
✅ Duration: 15 seconds (Instagram Reels optimal length)
✅ Frame Rate: 30fps
✅ Audio: AAC codec (silent track included)
✅ File Size: 5-8MB (under Instagram's limits)
✅ Format: MP4 with H.264 codec

### Upload to Instagram
The generated video is fully compatible with:
- Instagram Reels
- Instagram Stories
- Instagram Feed (IGTV)
- Facebook Reels
- TikTok (after export)

## License & Credits

Built with:
- **FastAPI** - Web framework
- **FFmpeg** - Video processing
- **Pillow** - Image validation
- **aiohttp** - Async HTTP client

---

**Need help?** Check the logs for detailed error messages or contact support.
