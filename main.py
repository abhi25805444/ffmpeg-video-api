from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import os
import tempfile
import shutil
import uuid
from typing import List, Optional, Dict, Any
import asyncio
from pathlib import Path
import logging
import aiohttp
import aiofiles
from urllib.parse import urlparse
import mimetypes
import json
from PIL import Image
import re
import gc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FFmpeg Video Generator API",
    description="Create videos from image URLs with optional background music",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Configuration - Extreme optimization for 512MB memory
MAX_FILE_SIZE = 3 * 1024 * 1024  # 3MB per file (extreme reduction)
MAX_IMAGES = 4  # Reduced to 4 for extreme memory constraints
SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
MAX_URL_LENGTH = 2048
MIN_IMAGE_DIMENSION = 480  # Further reduced for memory
DOWNLOAD_TIMEOUT = 60  # seconds
VIDEO_TIMEOUT = 120  # seconds for video processing
DOWNLOAD_CHUNK_SIZE = 2048  # Extremely small chunks
VIDEO_WIDTH = 720  # Reduced from 1080
VIDEO_HEIGHT = 1280  # Reduced from 1920

# Pydantic models for the new endpoint
class VideoGenerationRequest(BaseModel):
    original_image_url: str
    result_image_urls: List[str]
    prompt_preview_text: Optional[str] = None
    style_names: Optional[List[str]] = None
    logo_url: Optional[str] = None
    custom_cta_text: Optional[str] = "Link in Bio 👆"
    music_url: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
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
                "custom_cta_text": "Link in Bio 👆",
                "music_url": "https://example.com/background-music.mp3"
            }
        }

def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"FFmpeg check failed: {e}")
        return False

def validate_file_size(file: UploadFile) -> bool:
    """Validate file size"""
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        return False
    return True

def validate_image_format(filename: str) -> bool:
    """Validate image format"""
    return Path(filename).suffix.lower() in SUPPORTED_IMAGE_FORMATS

def validate_audio_format(filename: str) -> bool:
    """Validate audio format"""
    return Path(filename).suffix.lower() in SUPPORTED_AUDIO_FORMATS

async def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    """Save uploaded file to destination"""
    try:
        with open(destination, "wb") as buffer:
            content = await upload_file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File too large")
            buffer.write(content)
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

def validate_image_url(url: str) -> bool:
    """Validate image URL format"""
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False
        if len(url) > MAX_URL_LENGTH:
            return False
        return True
    except Exception:
        return False

async def download_image_from_url(session: aiohttp.ClientSession, url: str, destination: Path, validate_dimensions: bool = False) -> Dict[str, Any]:
    """Download image from URL and save to destination with enhanced validation"""
    try:
        logger.info(f"Downloading image from: {url}")

        async with session.get(url, timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)) as response:
            if response.status != 200:
                logger.error(f"Failed to download image: HTTP {response.status}")
                return {"success": False, "error": f"HTTP {response.status}"}

            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp', 'image/']):
                logger.error(f"Invalid content type: {content_type}")
                return {"success": False, "error": f"Invalid content type: {content_type}"}

            # Check content length
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > MAX_FILE_SIZE:
                logger.error(f"Image too large: {content_length} bytes")
                return {"success": False, "error": f"Image too large: {content_length} bytes"}

            # Download and save with smaller chunks for memory efficiency
            async with aiofiles.open(destination, 'wb') as f:
                total_size = 0
                async for chunk in response.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
                    total_size += len(chunk)
                    if total_size > MAX_FILE_SIZE:
                        logger.error(f"Image too large during download: {total_size} bytes")
                        return {"success": False, "error": f"Image too large during download"}
                    await f.write(chunk)

            logger.info(f"Downloaded image: {destination} ({total_size} bytes)")

            # Validate dimensions if requested
            if validate_dimensions:
                try:
                    with Image.open(destination) as img:
                        width, height = img.size
                        logger.info(f"Image dimensions: {width}x{height}")

                        if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                            logger.error(f"Image too small: {width}x{height} (min {MIN_IMAGE_DIMENSION}px)")
                            return {
                                "success": False,
                                "error": f"Image dimensions {width}x{height} below minimum {MIN_IMAGE_DIMENSION}px"
                            }

                        return {
                            "success": True,
                            "width": width,
                            "height": height,
                            "size": total_size,
                            "content_type": content_type
                        }
                except Exception as e:
                    logger.error(f"Error validating image dimensions: {e}")
                    return {"success": False, "error": f"Invalid image file: {str(e)}"}

            return {
                "success": True,
                "size": total_size,
                "content_type": content_type
            }

    except asyncio.TimeoutError:
        logger.error(f"Timeout downloading image from {url}")
        return {"success": False, "error": "Download timeout"}
    except Exception as e:
        logger.error(f"Error downloading image from {url}: {e}")
        return {"success": False, "error": str(e)}

def get_image_extension_from_url(url: str, content_type: str = None) -> str:
    """Get appropriate image extension from URL or content type"""
    # Try to get extension from URL
    parsed_url = urlparse(url)
    path_ext = Path(parsed_url.path).suffix.lower()

    if path_ext in SUPPORTED_IMAGE_FORMATS:
        return path_ext

    # Fallback to content type
    if content_type:
        extension = mimetypes.guess_extension(content_type)
        if extension and extension.lower() in SUPPORTED_IMAGE_FORMATS:
            return extension.lower()

    # Default fallback
    return '.jpg'

def validate_audio_url(url: str) -> bool:
    """Validate audio URL format"""
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False
        if len(url) > MAX_URL_LENGTH:
            return False
        return True
    except Exception:
        return False

async def download_audio_from_url(session: aiohttp.ClientSession, url: str, destination: Path) -> bool:
    """Download audio from URL and save to destination"""
    try:
        logger.info(f"Downloading audio from: {url}")

        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
            if response.status != 200:
                logger.error(f"Failed to download audio: HTTP {response.status}")
                return False

            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(audio_type in content_type for audio_type in ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/m4a', 'audio/aac', 'audio/ogg']):
                logger.error(f"Invalid audio content type: {content_type}")
                return False

            # Check content length
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > MAX_FILE_SIZE:
                logger.error(f"Audio too large: {content_length} bytes")
                return False

            # Download and save with smaller chunks for memory efficiency
            async with aiofiles.open(destination, 'wb') as f:
                total_size = 0
                async for chunk in response.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
                    total_size += len(chunk)
                    if total_size > MAX_FILE_SIZE:
                        logger.error(f"Audio too large during download: {total_size} bytes")
                        return False
                    await f.write(chunk)

            logger.info(f"Downloaded audio: {destination} ({total_size} bytes)")
            return True

    except Exception as e:
        logger.error(f"Error downloading audio from {url}: {e}")
        return False

def get_audio_extension_from_url(url: str, content_type: str = None) -> str:
    """Get appropriate audio extension from URL or content type"""
    # Try to get extension from URL
    parsed_url = urlparse(url)
    path_ext = Path(parsed_url.path).suffix.lower()

    if path_ext in SUPPORTED_AUDIO_FORMATS:
        return path_ext

    # Fallback to content type
    if content_type:
        extension = mimetypes.guess_extension(content_type)
        if extension and extension.lower() in SUPPORTED_AUDIO_FORMATS:
            return extension.lower()

    # Default fallback
    return '.mp3'

def escape_ffmpeg_text(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter"""
    # Replace special characters that need escaping in FFmpeg
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace("%", "\\%")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    return text

def get_memory_optimized_ffmpeg_flags() -> list:
    """Get FFmpeg flags optimized for extreme low memory (512MB)"""
    return [
        "-max_muxing_queue_size", "512",  # Reduce muxing queue
        "-bufsize", "256k",  # Limit buffer size
        "-maxrate", "1M",  # Limit bitrate
    ]

def auto_generate_prompt_preview(result_count: int) -> str:
    """Auto-generate prompt preview text if not provided"""
    prompts = [
        "Transform your photos with AI magic",
        "Unlock endless creative possibilities",
        "Professional edits in seconds",
        "Your photo, infinite styles"
    ]
    return prompts[min(result_count - 1, len(prompts) - 1)] if result_count > 0 else prompts[0]

def create_hook_grid(result_images: List[Path], output_path: Path, fps: int = 30) -> bool:
    """
    [0-1s] Hook Grid: Create 2x2 grid from first 4 result images
    Each cell: 540x960px, Quick zoom on each (0.25s per image)
    """
    try:
        logger.info("Creating hook grid segment [0-1s]")

        # Use first 4 images (or repeat if less than 4)
        grid_images = []
        for i in range(4):
            grid_images.append(result_images[i % len(result_images)])

        # Create temp directory for individual cell videos
        temp_dir = output_path.parent / f"grid_temp_{uuid.uuid4().hex[:8]}"
        temp_dir.mkdir(exist_ok=True)

        try:
            # Create individual videos for each grid cell with zoom effect
            cell_videos = []
            for i, img_path in enumerate(grid_images):
                cell_video = temp_dir / f"cell_{i}.mp4"
                cell_videos.append(cell_video)

                # Reduced resolution: 720x1280 grid cells = 360x640 each
                video_filter = (
                    f"scale=396:704:force_original_aspect_ratio=increase,"  # Scale to 1.1x size
                    f"crop=360:640"  # Crop to cell size (720/2 x 1280/2)
                )

                memory_flags = get_memory_optimized_ffmpeg_flags()

                cmd = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-t", "1",
                    "-i", str(img_path),
                    "-vf", video_filter,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-preset", "ultrafast",
                    "-crf", "30",  # Increased from 28 for smaller files
                    "-r", str(fps),
                    "-threads", "1",  # Reduced from 2
                ] + memory_flags + [
                    str(cell_video)
                ]

                logger.info(f"Creating grid cell {i+1}/4")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode != 0:
                    logger.error(f"Cell {i} creation failed: {result.stderr}")
                    return False

                # Force cleanup of input image from memory after processing
                del img_path
                gc.collect()

            # Force garbage collection after creating cells
            gc.collect()

            # Now combine the 4 cell videos into a 2x2 grid
            filter_complex = (
                f"[0:v][1:v]hstack=inputs=2[top];"
                f"[2:v][3:v]hstack=inputs=2[bottom];"
                f"[top][bottom]vstack=inputs=2[v]"
            )

            memory_flags = get_memory_optimized_ffmpeg_flags()

            cmd = [
                "ffmpeg", "-y",
                "-i", str(cell_videos[0]),
                "-i", str(cell_videos[1]),
                "-i", str(cell_videos[2]),
                "-i", str(cell_videos[3]),
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "ultrafast",
                "-crf", "30",
                "-r", str(fps),
                "-t", "1",
                "-threads", "1",
            ] + memory_flags + [
                str(output_path)
            ]

            logger.info(f"Combining grid cells into 2x2 layout")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                logger.error(f"Grid combination failed: {result.stderr}")
                return False

            # Delete cell videos immediately to free memory
            for cell_video in cell_videos:
                if cell_video.exists():
                    cell_video.unlink()
            gc.collect()

            logger.info(f"Hook grid created: {output_path}")
            return True

        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            gc.collect()

    except Exception as e:
        logger.error(f"Error creating hook grid: {e}")
        return False

def create_original_photo_segment(original_image: Path, output_path: Path, fps: int = 30) -> bool:
    """
    [1-3s] Original Photo: Display original centered, scale to 70% screen height
    Text overlay: "This Photo +", Zoom animation (1.0 → 1.08)
    """
    try:
        logger.info("Creating original photo segment [1-3s]")

        text = escape_ffmpeg_text("This Photo +")

        # Reduced to 720x1280 for memory efficiency
        video_filter = (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fade=t=in:st=0:d=0.5,"
            f"drawtext=text='{text}':"
            f"fontfile=/Windows/Fonts/arialbd.ttf:fontsize=54:fontcolor=white:"
            f"borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=(h-text_h)/2+200"
        )

        memory_flags = get_memory_optimized_ffmpeg_flags()

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-t", "2",
            "-i", str(original_image),
            "-vf", video_filter,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            "-crf", "30",
            "-r", str(fps),
            "-threads", "1",
        ] + memory_flags + [
            str(output_path)
        ]

        logger.info(f"Running original photo FFmpeg command")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            logger.error(f"Original photo segment failed: {result.stderr}")
            return False

        logger.info(f"Original photo segment created: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error creating original photo segment: {e}")
        return False

def create_prompt_tease_segment(original_image: Path, prompt_text: str, output_path: Path, fps: int = 30) -> bool:
    """
    [3-5s] Prompt Tease: Keep original visible (dimmed 30%)
    Text: "+ inspix Prompt =", Show prompt_preview_text (blurred, 48pt)
    """
    try:
        logger.info("Creating prompt tease segment [3-5s]")

        text1 = escape_ffmpeg_text("+ inspix Prompt =")
        text2 = escape_ffmpeg_text(prompt_text)

        # Reduced to 720x1280 with proportional font sizes
        video_filter = (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
            f"eq=brightness=-0.3,"
            f"drawtext=text='{text1}':"
            f"fontfile=/Windows/Fonts/arialbd.ttf:fontsize=42:fontcolor=white:"
            f"borderw=2:bordercolor=black:"
            f"x=(w-text_w)/2:y=(h)/2-70,"
            f"drawtext=text='{text2}':"
            f"fontfile=/Windows/Fonts/arialbd.ttf:fontsize=32:fontcolor=white:"
            f"borderw=2:bordercolor=black:"
            f"x=(w-text_w)/2:y=(h)/2+35"
        )

        memory_flags = get_memory_optimized_ffmpeg_flags()

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-t", "2",
            "-i", str(original_image),
            "-vf", video_filter,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            "-crf", "30",
            "-r", str(fps),
            "-threads", "1",
        ] + memory_flags + [
            str(output_path)
        ]

        logger.info(f"Running prompt tease FFmpeg command")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            logger.error(f"Prompt tease segment failed: {result.stderr}")
            return False

        logger.info(f"Prompt tease segment created: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error creating prompt tease segment: {e}")
        return False

def create_results_showcase(
    result_images: List[Path],
    style_names: List[str],
    output_path: Path,
    fps: int = 30
) -> bool:
    """
    [5-12s] Results Showcase: Show each result sequentially
    Dynamic timing: 7 seconds ÷ array length
    Transitions: fade, slideleft, circleopen, fadeblack
    Text overlay: "Style: {style_name}", Counter: "1/4", "2/4", etc.
    Ken Burns zoom on each
    """
    try:
        logger.info("Creating results showcase segment [5-12s]")

        total_duration = 7.0
        duration_per_image = total_duration / len(result_images)
        transition_duration = 0.5

        transitions = ["fade", "slideleft", "circleopen", "fadeblack"]

        # Create individual result videos with Ken Burns and text
        temp_videos = []
        temp_dir = output_path.parent / f"temp_{uuid.uuid4().hex[:8]}"
        temp_dir.mkdir(exist_ok=True)

        try:
            for i, img_path in enumerate(result_images):
                temp_video = temp_dir / f"result_{i:04d}.mp4"
                temp_videos.append(temp_video)

                style_name = style_names[i] if i < len(style_names) else f"Style {i+1}"
                counter_text = f"{i+1}/{len(result_images)}"

                text_style = escape_ffmpeg_text(f"Style\\: {style_name}")
                text_counter = escape_ffmpeg_text(counter_text)

                # Reduced to 720x1280 with proportional font sizes
                video_filter = (
                    f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                    f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
                    f"fade=t=in:st=0:d=0.3,"
                    f"drawtext=text='{text_style}':"
                    f"fontfile=/Windows/Fonts/arialbd.ttf:fontsize=42:fontcolor=white:"
                    f"borderw=2:bordercolor=black:"
                    f"x=(w-text_w)/2:y=70,"
                    f"drawtext=text='{text_counter}':"
                    f"fontfile=/Windows/Fonts/arialbd.ttf:fontsize=32:fontcolor=white:"
                    f"borderw=2:bordercolor=black:"
                    f"x=(w-text_w)/2:y=h-100"
                )

                memory_flags = get_memory_optimized_ffmpeg_flags()

                cmd = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-t", str(duration_per_image),
                    "-i", str(img_path),
                    "-vf", video_filter,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-preset", "ultrafast",
                    "-crf", "30",
                    "-r", str(fps),
                    "-threads", "1",
                ] + memory_flags + [
                    str(temp_video)
                ]

                logger.info(f"Creating result video {i+1}/{len(result_images)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)

                if result.returncode != 0:
                    logger.error(f"Error creating result video {i}: {result.stderr}")
                    return False

                # Force cleanup after each video
                del img_path
                gc.collect()

            # Force garbage collection after creating all result videos
            gc.collect()

            # Concatenate with xfade transitions
            if len(temp_videos) == 1:
                shutil.copy(temp_videos[0], output_path)
            else:
                # Build xfade filter complex
                filter_parts = []
                input_args = []

                for i, video in enumerate(temp_videos):
                    input_args.extend(["-i", str(video)])

                # Build xfade chain
                current_label = "[0:v]"
                for i in range(len(temp_videos) - 1):
                    next_input = f"[{i+1}:v]"
                    transition = transitions[i % len(transitions)]
                    offset = (i + 1) * duration_per_image - transition_duration
                    output_label = f"[v{i}]" if i < len(temp_videos) - 2 else "[v]"

                    filter_parts.append(
                        f"{current_label}{next_input}xfade=transition={transition}:duration={transition_duration}:offset={offset}{output_label}"
                    )
                    current_label = output_label

                filter_complex = ";".join(filter_parts)

                memory_flags = get_memory_optimized_ffmpeg_flags()

                cmd = [
                    "ffmpeg", "-y"
                ] + input_args + [
                    "-filter_complex", filter_complex,
                    "-map", "[v]",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-preset", "ultrafast",
                    "-crf", "30",
                    "-r", str(fps),
                    "-threads", "1",
                ] + memory_flags + [
                    str(output_path)
                ]

                logger.info(f"Concatenating result videos with transitions")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

                if result.returncode != 0:
                    logger.error(f"Error concatenating results: {result.stderr}")
                    return False

                # Delete temp videos immediately after concatenation
                for temp_video in temp_videos:
                    if temp_video.exists():
                        temp_video.unlink()
                gc.collect()

            logger.info(f"Results showcase created: {output_path}")
            return True

        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            gc.collect()

    except Exception as e:
        logger.error(f"Error creating results showcase: {e}")
        return False

def create_branding_segment(last_result_image: Path, logo_path: Optional[Path], output_path: Path, fps: int = 30) -> bool:
    """
    [12-14s] Branding: Last result visible (dimmed 20%)
    Text: "500+ Prompts Ready"
    Logo overlay (top-right, 120x120px, 85% opacity) if provided
    Fade-in animation
    """
    try:
        logger.info("Creating branding segment [12-14s]")

        text = escape_ffmpeg_text("500+ Prompts Ready")

        # Reduced to 720x1280 with proportional logo
        memory_flags = get_memory_optimized_ffmpeg_flags()

        # Add logo overlay if provided
        if logo_path and logo_path.exists():
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-t", "2", "-i", str(last_result_image),
                "-loop", "1", "-t", "2", "-i", str(logo_path),
                "-filter_complex",
                f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},eq=brightness=-0.2,fade=t=in:st=0:d=0.5[bg];"
                f"[1:v]scale=80:80:force_original_aspect_ratio=decrease,format=rgba,colorchannelmixer=aa=0.85[logo];"
                f"[bg][logo]overlay=W-w-30:30[v1];"
                f"[v1]drawtext=text='{text}':"
                f"fontfile=/Windows/Fonts/arialbd.ttf:fontsize=48:fontcolor=white:"
                f"borderw=3:bordercolor=black:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:"
                f"alpha='if(lt(t,0.5),t/0.5,1)'[v]",
                "-map", "[v]",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "ultrafast",
                "-crf", "30",
                "-r", str(fps),
                "-t", "2",
                "-threads", "1",
            ] + memory_flags + [
                str(output_path)
            ]
        else:
            video_filter = (
                f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
                f"eq=brightness=-0.2,"
                f"fade=t=in:st=0:d=0.5,"
                f"drawtext=text='{text}':"
                f"fontfile=/Windows/Fonts/arialbd.ttf:fontsize=48:fontcolor=white:"
                f"borderw=3:bordercolor=black:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:"
                f"alpha='if(lt(t,0.5),t/0.5,1)'"
            )
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-t", "2",
                "-i", str(last_result_image),
                "-vf", video_filter,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "ultrafast",
                "-crf", "30",
                "-r", str(fps),
                "-threads", "1",
            ] + memory_flags + [
                str(output_path)
            ]

        logger.info(f"Running branding FFmpeg command")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            logger.error(f"Branding segment failed: {result.stderr}")
            return False

        logger.info(f"Branding segment created: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error creating branding segment: {e}")
        return False

def create_cta_segment(last_result_image: Path, cta_text: str, logo_path: Optional[Path], output_path: Path, fps: int = 30) -> bool:
    """
    [14-15s] Call-to-Action: Show custom CTA text
    Pulse animation (scale 1.0 → 1.05 → 1.0)
    Logo remains visible
    """
    try:
        logger.info("Creating CTA segment [14-15s]")

        text = escape_ffmpeg_text(cta_text)

        # Reduced to 720x1280 with proportional text and logo
        memory_flags = get_memory_optimized_ffmpeg_flags()

        base_filter = (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            f"eq=brightness=-0.2"
        )

        text_filter = (
            f"drawtext=text='{text}':"
            f"fontfile=/Windows/Fonts/arialbd.ttf:fontsize=54:fontcolor=white:"
            f"borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=(h-text_h)/2"
        )

        if logo_path and logo_path.exists():
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-t", "1", "-i", str(last_result_image),
                "-loop", "1", "-t", "1", "-i", str(logo_path),
                "-filter_complex",
                f"[0:v]{base_filter}[bg];"
                f"[1:v]scale=80:80:force_original_aspect_ratio=decrease,format=rgba,colorchannelmixer=aa=0.85[logo];"
                f"[bg][logo]overlay=W-w-30:30[v1];"
                f"[v1]{text_filter}[v]",
                "-map", "[v]",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "ultrafast",
                "-crf", "30",
                "-r", str(fps),
                "-t", "1",
                "-threads", "1",
            ] + memory_flags + [
                str(output_path)
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-t", "1",
                "-i", str(last_result_image),
                "-vf", f"{base_filter},{text_filter}",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "ultrafast",
                "-crf", "30",
                "-r", str(fps),
                "-threads", "1",
            ] + memory_flags + [
                str(output_path)
            ]

        logger.info(f"Running CTA FFmpeg command")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            logger.error(f"CTA segment failed: {result.stderr}")
            return False

        logger.info(f"CTA segment created: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error creating CTA segment: {e}")
        return False

def create_video_from_images(
    image_paths: List[Path],
    output_path: Path,
    duration_per_image: float = 2.0,
    transition_duration: float = 1.0,
    fps: int = 25,
    text_content: Optional[str] = None,
    second_text_content: Optional[str] = None
) -> bool:
    """Create video from images using FFmpeg"""
    try:
        logger.info(f"Creating video from {len(image_paths)} images")
        logger.info(f"Output path: {output_path}")
        if text_content:
            logger.info(f"Adding first text overlay: {text_content}")
        if second_text_content:
            logger.info(f"Adding second text overlay: {second_text_content}")

        # Verify all input images exist
        for i, img_path in enumerate(image_paths):
            if not img_path.exists():
                logger.error(f"Image {i} does not exist: {img_path}")
                return False
            logger.info(f"Image {i}: {img_path} (size: {img_path.stat().st_size} bytes)")

        # Create a temporary directory for processed images
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            logger.info(f"Using temp directory: {temp_path}")

            if len(image_paths) == 1:
                # Single image - create a portrait video with fade in only
                logger.info("Creating portrait video from single image with fade effects")

                # Build video filter with optional text overlay
                video_filter = (
                    f"scale=1080:1920:force_original_aspect_ratio=decrease,"
                    f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
                    f"fade=t=in:st=0:d={transition_duration}"
                )

                # Add first text overlay if provided
                if text_content:
                    text_filter = (
                        f"drawtext=text='{text_content}':fontsize=72:fontcolor=white:"
                        f"x=(w-text_w)/2:y=h-text_h-100:"
                        f"box=1:boxcolor=black@0.8:boxborderw=25:"
                        f"shadowcolor=black:shadowx=2:shadowy=2:"
                        f"enable='between(t,0,3)'"
                    )
                    video_filter += f",{text_filter}"

                # Add second text overlay if provided
                if second_text_content:
                    video_duration = duration_per_image + transition_duration
                    second_text_filter = (
                        f"drawtext=text='{second_text_content}':fontsize=72:fontcolor=white:"
                        f"x=(w-text_w)/2:y=h-text_h-100:"
                        f"box=1:boxcolor=black@0.8:boxborderw=25:"
                        f"shadowcolor=black:shadowx=2:shadowy=2:"
                        f"enable='between(t,3,{video_duration})'"
                    )
                    video_filter += f",{second_text_filter}"

                cmd = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-t", str(duration_per_image + transition_duration),  # Add time for fade in
                    "-i", str(image_paths[0]),
                    "-vf", video_filter,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-preset", "ultrafast",
                    "-crf", "28",
                    "-r", str(fps),
                    "-movflags", "+faststart",
                    "-an",  # No audio stream
                    str(output_path)
                ]

                logger.info(f"FFmpeg command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

                if result.returncode != 0:
                    logger.error(f"FFmpeg error (return code {result.returncode}): {result.stderr}")
                    logger.error(f"FFmpeg stdout: {result.stdout}")
                    return False

                # Check output file size
                if not output_path.exists() or output_path.stat().st_size < 1000:
                    logger.error("Output video file is empty or too small.")
                    return False

                logger.info(f"Single image portrait video created successfully: {output_path.stat().st_size} bytes")
                return True

            else:
                # Multiple images - use simpler fade approach instead of complex xfade
                logger.info("Creating portrait slideshow with fade transitions")

                # Calculate total duration correctly for overlapping transitions
                if len(image_paths) == 1:
                    total_duration = duration_per_image + transition_duration
                else:
                    # For multiple images: first image full duration + (remaining images - transition overlaps) + last image fade out
                    total_duration = duration_per_image + ((len(image_paths) - 1) * (duration_per_image - transition_duration)) + transition_duration
                logger.info(f"Expected total video duration: {total_duration} seconds")

                # Create individual videos with fade effects
                temp_videos = []
                for i, img_path in enumerate(image_paths):
                    temp_video = temp_path / f"video_{i:04d}.mp4"
                    temp_videos.append(temp_video)

                    # Create fade effects based on position - fixed timing
                    fade_filters = []

                    if i == 0:  # First image - fade in + fade out
                        fade_filters.append(f"fade=t=in:st=0:d={transition_duration}")
                        if len(image_paths) > 1:
                            fade_filters.append(f"fade=t=out:st={duration_per_image - transition_duration}:d={transition_duration}")
                        video_duration = duration_per_image
                    elif i == len(image_paths) - 1:  # Last image - fade in + extended fade out
                        fade_filters.append(f"fade=t=in:st=0:d={transition_duration}")
                        fade_filters.append(f"fade=t=out:st={duration_per_image - transition_duration}:d={transition_duration}")
                        video_duration = duration_per_image  # No extension needed
                    else:  # Middle images - overlapping fades
                        fade_filters.append(f"fade=t=in:st=0:d={transition_duration}")
                        fade_filters.append(f"fade=t=out:st={duration_per_image - transition_duration}:d={transition_duration}")
                        video_duration = duration_per_image - transition_duration  # Shorter duration to prevent gaps

                    # Build video filter
                    video_filter = f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
                    if fade_filters:
                        video_filter += "," + ",".join(fade_filters)

                    # Add text overlay to first video only (first 3 seconds of entire video)
                    if i == 0 and text_content:
                        text_filter = (
                            f"drawtext=text='{text_content}':fontsize=72:fontcolor=white:"
                            f"x=(w-text_w)/2:y=h-text_h-100:"
                            f"box=1:boxcolor=black@0.8:boxborderw=25:"
                            f"shadowcolor=black:shadowx=2:shadowy=2:"
                            f"enable='between(t,0,3)'"
                        )
                        video_filter += f",{text_filter}"

                    # Add second text overlay to last video only (from 3 seconds to end of video)
                    if i == len(image_paths) - 1 and second_text_content:
                        # Calculate when second text should start appearing in the final concatenated video
                        second_text_start = max(3.0, 0.0)  # Start after first text ends
                        second_text_filter = (
                            f"drawtext=text='{second_text_content}':fontsize=72:fontcolor=white:"
                            f"x=(w-text_w)/2:y=h-text_h-100:"
                            f"box=1:boxcolor=black@0.8:boxborderw=25:"
                            f"shadowcolor=black:shadowx=2:shadowy=2:"
                            f"enable='gte(t,0)'"  # Show throughout the last video
                        )
                        video_filter += f",{second_text_filter}"

                    single_cmd = [
                        "ffmpeg", "-y",
                        "-loop", "1",
                        "-t", str(video_duration),
                        "-i", str(img_path),
                        "-vf", video_filter,
                        "-c:v", "libx264",
                        "-pix_fmt", "yuv420p",
                        "-preset", "ultrafast",
                        "-crf", "28",
                        "-r", str(fps),
                        "-an",
                        str(temp_video)
                    ]

                    logger.info(f"Creating video {i+1}/{len(image_paths)} with fade effects (duration: {video_duration}s)")
                    logger.info(f"Filter: {video_filter}")
                    result = subprocess.run(single_cmd, capture_output=True, text=True, timeout=90)
                    if result.returncode != 0:
                        logger.error(f"Error creating video for image {i}: {result.stderr}")
                        return False

                    if not temp_video.exists() or temp_video.stat().st_size < 1000:
                        logger.error(f"Temp video was not created or is too small: {temp_video}")
                        return False

                    logger.info(f"Created temp video: {temp_video} (size: {temp_video.stat().st_size} bytes)")

                # Create concat file for final merge
                concat_file = temp_path / "concat.txt"
                with open(concat_file, 'w') as f:
                    for video in temp_videos:
                        video_path = str(video).replace('\\', '/')
                        f.write(f"file '{video_path}'\n")

                logger.info(f"Created concat file with {len(temp_videos)} videos")

                # Concatenate videos with stream copy for faster processing
                concat_cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_file),
                    "-c", "copy",
                    "-movflags", "+faststart",
                    str(output_path)
                ]

                logger.info(f"Concatenating videos with fade transitions")
                result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=180)
                if result.returncode != 0:
                    logger.error(f"Error concatenating videos: {result.stderr}")
                    return False

                # Check output file size
                if not output_path.exists() or output_path.stat().st_size < 1000:
                    logger.error("Output video file is empty or too small after processing.")
                    return False

                logger.info(f"Portrait slideshow with fade transitions created successfully: {output_path.stat().st_size} bytes")
                return True

    except subprocess.TimeoutExpired as e:
        logger.error(f"FFmpeg command timed out: {e}")
        return False
    except Exception as e:
        logger.error(f"Error creating video: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def create_inspix_video(
    original_image: Path,
    result_images: List[Path],
    output_path: Path,
    prompt_text: Optional[str] = None,
    style_names: Optional[List[str]] = None,
    logo_path: Optional[Path] = None,
    cta_text: str = "Link in Bio 👆",
    fps: int = 30,
    music_path: Optional[Path] = None
) -> bool:
    """
    Create complete 15-second video following the exact timeline:
    [0-1s] Hook Grid
    [1-3s] Original Photo
    [3-5s] Prompt Tease
    [5-12s] Results Showcase
    [12-14s] Branding
    [14-15s] Call-to-Action

    Optional background music will be added if music_path is provided.
    """
    try:
        logger.info("Creating inspix video with timeline segments")

        # Create temp directory for segments
        temp_dir = output_path.parent / f"segments_{uuid.uuid4().hex[:8]}"
        temp_dir.mkdir(exist_ok=True)

        try:
            segments = []

            # Auto-generate prompt text if not provided
            if not prompt_text:
                prompt_text = auto_generate_prompt_preview(len(result_images))

            # Auto-generate style names if not provided
            if not style_names or len(style_names) < len(result_images):
                style_names = [f"Style {i+1}" for i in range(len(result_images))]

            # [0-1s] Hook Grid
            logger.info("Creating segment 1/6: Hook Grid [0-1s]")
            segment1 = temp_dir / "segment1_hook_grid.mp4"
            if not create_hook_grid(result_images, segment1, fps):
                raise Exception("Failed to create hook grid segment")
            segments.append(segment1)
            gc.collect()  # Free memory after segment creation

            # [1-3s] Original Photo
            logger.info("Creating segment 2/6: Original Photo [1-3s]")
            segment2 = temp_dir / "segment2_original.mp4"
            if not create_original_photo_segment(original_image, segment2, fps):
                raise Exception("Failed to create original photo segment")
            segments.append(segment2)
            gc.collect()  # Free memory after segment creation

            # [3-5s] Prompt Tease
            logger.info("Creating segment 3/6: Prompt Tease [3-5s]")
            segment3 = temp_dir / "segment3_prompt.mp4"
            if not create_prompt_tease_segment(original_image, prompt_text, segment3, fps):
                raise Exception("Failed to create prompt tease segment")
            segments.append(segment3)
            gc.collect()  # Free memory after segment creation

            # [5-12s] Results Showcase
            logger.info("Creating segment 4/6: Results Showcase [5-12s]")
            segment4 = temp_dir / "segment4_results.mp4"
            if not create_results_showcase(result_images, style_names, segment4, fps):
                raise Exception("Failed to create results showcase segment")
            segments.append(segment4)
            gc.collect()  # Free memory after segment creation

            # [12-14s] Branding
            logger.info("Creating segment 5/6: Branding [12-14s]")
            segment5 = temp_dir / "segment5_branding.mp4"
            last_result = result_images[-1]
            if not create_branding_segment(last_result, logo_path, segment5, fps):
                raise Exception("Failed to create branding segment")
            segments.append(segment5)
            gc.collect()  # Free memory after segment creation

            # [14-15s] Call-to-Action
            logger.info("Creating segment 6/6: CTA [14-15s]")
            segment6 = temp_dir / "segment6_cta.mp4"
            if not create_cta_segment(last_result, cta_text, logo_path, segment6, fps):
                raise Exception("Failed to create CTA segment")
            segments.append(segment6)
            gc.collect()  # Free memory after segment creation

            # Concatenate all segments
            logger.info("Concatenating all segments into final video")
            concat_file = temp_dir / "concat.txt"
            with open(concat_file, 'w') as f:
                for segment in segments:
                    # Use absolute path to avoid FFmpeg path resolution issues
                    segment_path = str(segment.resolve()).replace('\\', '/')
                    f.write(f"file '{segment_path}'\n")

            # Concatenate with audio track (either background music or silent)
            memory_flags = get_memory_optimized_ffmpeg_flags()

            if music_path and music_path.exists():
                # Use provided background music, loop it to match video duration
                logger.info(f"Adding background music: {music_path}")
                concat_cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_file),
                    "-stream_loop", "-1",  # Loop audio indefinitely
                    "-i", str(music_path),
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-b:a", "128k",  # Higher quality for background music
                    "-pix_fmt", "yuv420p",
                    "-preset", "ultrafast",
                    "-crf", "30",
                    "-shortest",  # End when video ends
                    "-map", "0:v:0",  # Video from first input
                    "-map", "1:a:0",  # Audio from second input
                    "-movflags", "+faststart",
                    "-threads", "1",
                ] + memory_flags + [
                    str(output_path)
                ]
            else:
                # Use silent AAC audio track for Instagram compatibility
                logger.info("Adding silent audio track")
                concat_cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_file),
                    "-f", "lavfi",
                    "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-b:a", "64k",  # Reduced from 96k
                    "-pix_fmt", "yuv420p",
                    "-preset", "ultrafast",
                    "-crf", "30",
                    "-shortest",
                    "-movflags", "+faststart",
                    "-threads", "1",
                ] + memory_flags + [
                    str(output_path)
                ]

            logger.info("Running final concatenation with audio track")
            result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=VIDEO_TIMEOUT)

            if result.returncode != 0:
                logger.error(f"Final concatenation failed: {result.stderr}")
                return False

            # Delete segment files immediately after concatenation
            for segment in segments:
                if segment.exists():
                    segment.unlink()
            gc.collect()

            # Verify output
            if not output_path.exists() or output_path.stat().st_size < 10000:
                logger.error("Output video file is missing or too small")
                return False

            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"Video created successfully: {file_size_mb:.2f} MB")

            # Verify duration is approximately 15 seconds
            duration_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(output_path)
            ]
            duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=10)
            if duration_result.returncode == 0:
                try:
                    duration = float(duration_result.stdout.strip())
                    logger.info(f"Video duration: {duration:.2f} seconds")
                except:
                    pass

            return True

        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            gc.collect()

    except Exception as e:
        logger.error(f"Error creating inspix video: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def add_audio_to_video(video_path: Path, audio_path: Path, output_path: Path) -> bool:
    """Add audio track to video"""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-stream_loop", "-1",  # Loop audio indefinitely - moved before audio input
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",  # End when video (longest stream) ends
            "-map", "0:v:0",  # Video from first input
            "-map", "1:a:0",  # Audio from second input
            "-movflags", "+faststart",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"Error adding audio: {result.stderr}")
            return False

        return True
    except Exception as e:
        logger.error(f"Error adding audio: {e}")
        return False

@app.get("/")
async def root():
    """API health check"""
    ffmpeg_available = check_ffmpeg()
    return {
        "message": "FFmpeg Video Generator API",
        "status": "running",
        "ffmpeg_available": ffmpeg_available,
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "ffmpeg": check_ffmpeg(),
        "upload_dir": UPLOAD_DIR.exists(),
        "output_dir": OUTPUT_DIR.exists()
    }

@app.post("/generate-inspix-video")
async def generate_inspix_video(request: VideoGenerationRequest):
    """
    Generate a 15-second Instagram-ready video following the inspix timeline:
    [0-1s] Hook Grid - 2x2 grid of results with quick zooms
    [1-3s] Original Photo - Display with text overlay
    [3-5s] Prompt Tease - Show prompt text with original dimmed
    [5-12s] Results Showcase - Sequential display with transitions
    [12-14s] Branding - Show branding message with logo
    [14-15s] Call-to-Action - Display CTA text

    Technical Specs (EXTREME optimization for 512MB memory):
    - Resolution: 720x1280 (9:16) - Reduced for memory
    - Frame Rate: 24fps (reduced for memory efficiency)
    - Codec: H.264 (libx264, ultrafast preset, CRF 30)
    - Audio: Background music (128k AAC) if music_url provided, otherwise silent AAC track 64k
    - Duration: Exactly 15 seconds
    - Max Images: 4 result images (memory constraint)
    - Max File Size: 3MB per image/audio
    - Threads: 1 (prevents memory spikes)
    - Memory flags: bufsize 256k, maxrate 1M
    - Background Music: Optional music_url parameter for custom background music (will be looped to match video duration)
    """

    # Check FFmpeg availability
    if not check_ffmpeg():
        raise HTTPException(status_code=503, detail="FFmpeg not available")

    # Validate inputs
    if not request.original_image_url:
        raise HTTPException(
            status_code=400,
            detail="original_image_url is required"
        )

    if not request.result_image_urls or len(request.result_image_urls) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one result image URL is required"
        )

    if len(request.result_image_urls) > MAX_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_IMAGES} result images allowed (memory constraint)"
        )

    # Validate URL formats
    if not validate_image_url(request.original_image_url):
        raise HTTPException(
            status_code=400,
            detail="Invalid original_image_url format"
        )

    for i, url in enumerate(request.result_image_urls):
        if not validate_image_url(url):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid URL format for result_image_urls[{i}]"
            )

    if request.logo_url and not validate_image_url(request.logo_url):
        raise HTTPException(
            status_code=400,
            detail="Invalid logo_url format"
        )

    if request.music_url and not validate_audio_url(request.music_url):
        raise HTTPException(
            status_code=400,
            detail="Invalid music_url format"
        )

    # Validate style names count matches result images
    if request.style_names and len(request.style_names) != len(request.result_image_urls):
        raise HTTPException(
            status_code=400,
            detail=f"style_names count ({len(request.style_names)}) must match result_image_urls count ({len(request.result_image_urls)})"
        )

    # Generate unique ID for this request
    request_id = str(uuid.uuid4())
    request_dir = UPLOAD_DIR / request_id
    request_dir.mkdir(exist_ok=True)

    try:
        async with aiohttp.ClientSession() as session:
            # Download original image
            logger.info(f"Downloading original image from: {request.original_image_url}")
            extension = get_image_extension_from_url(request.original_image_url)
            original_image_path = request_dir / f"original{extension}"

            result = await download_image_from_url(
                session,
                request.original_image_url,
                original_image_path,
                validate_dimensions=True
            )

            if not result.get("success"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to download original image: {result.get('error', 'Unknown error')}"
                )

            # Download result images
            result_image_paths = []
            logger.info(f"Downloading {len(request.result_image_urls)} result images")

            for i, url in enumerate(request.result_image_urls):
                extension = get_image_extension_from_url(url)
                result_path = request_dir / f"result_{i:04d}{extension}"

                result = await download_image_from_url(
                    session,
                    url,
                    result_path,
                    validate_dimensions=True
                )

                if not result.get("success"):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to download result image {i+1}: {result.get('error', 'Unknown error')}"
                    )

                result_image_paths.append(result_path)

            # Force garbage collection after downloading images
            gc.collect()

            # Download logo if provided
            logo_path = None
            if request.logo_url:
                logger.info(f"Downloading logo from: {request.logo_url}")
                extension = get_image_extension_from_url(request.logo_url)
                logo_path = request_dir / f"logo{extension}"

                result = await download_image_from_url(session, request.logo_url, logo_path)

                if not result.get("success"):
                    logger.warning(f"Failed to download logo: {result.get('error')}. Continuing without logo.")
                    logo_path = None

            # Download background music if provided
            music_path = None
            if request.music_url:
                logger.info(f"Downloading background music from: {request.music_url}")
                extension = get_audio_extension_from_url(request.music_url)
                music_path = request_dir / f"music{extension}"

                success = await download_audio_from_url(session, request.music_url, music_path)

                if not success:
                    logger.warning(f"Failed to download music. Continuing without background music.")
                    music_path = None

        # Generate output video
        output_filename = f"inspix_{request_id}.mp4"
        output_path = OUTPUT_DIR / output_filename

        logger.info("Starting video generation (low memory mode)")
        success = create_inspix_video(
            original_image=original_image_path,
            result_images=result_image_paths,
            output_path=output_path,
            prompt_text=request.prompt_preview_text,
            style_names=request.style_names,
            logo_path=logo_path,
            cta_text=request.custom_cta_text,
            fps=24,  # Reduced from 30 for memory efficiency
            music_path=music_path
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate video"
            )

        # Clean up downloaded files and force garbage collection
        shutil.rmtree(request_dir, ignore_errors=True)
        gc.collect()

        if not output_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Video file was not created"
            )

        # Get video info
        file_size = output_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        # Return success response
        return {
            "message": "Inspix video created successfully (low memory mode)",
            "video_id": request_id,
            "download_url": f"/download/{output_filename}",
            "file_size": file_size,
            "file_size_mb": round(file_size_mb, 2),
            "duration_seconds": 15,
            "resolution": "720x1280",
            "fps": 24,
            "format": "mp4",
            "codec": "H.264 (CRF 30)",
            "audio": "AAC 128k (background music)" if music_path else "AAC 64k (silent)",
            "background_music_added": music_path is not None,
            "images_processed": {
                "original": 1,
                "results": len(result_image_paths),
                "logo": 1 if logo_path else 0
            },
            "optimization": "512MB memory mode"
        }

    except HTTPException:
        # Clean up on error and free memory
        shutil.rmtree(request_dir, ignore_errors=True)
        gc.collect()
        raise
    except Exception as e:
        # Clean up on error and free memory
        shutil.rmtree(request_dir, ignore_errors=True)
        gc.collect()
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/create-video")
async def create_video(
    image_urls: List[str] = Form(..., description="List of image URLs"),
    audio: Optional[UploadFile] = File(None, description="Optional audio file"),
    audio_url: Optional[str] = Form(None, description="Optional audio URL"),
    text_content: Optional[str] = Form(None, description="First text to display for first 3 seconds"),
    second_text_content: Optional[str] = Form(None, description="Second text to display from 3 seconds to end"),
    duration_per_image: float = Form(3.0, description="Duration per image in seconds"),
    transition_duration: float = Form(1.0, description="Transition duration in seconds"),
    fps: int = Form(25, description="Output video FPS")
):
    """Create video from image URLs with optional audio and text overlay"""

    # Check FFmpeg availability
    if not check_ffmpeg():
        raise HTTPException(status_code=503, detail="FFmpeg not available")

    # Validate inputs
    if not image_urls or len(image_urls) == 0:
        raise HTTPException(status_code=400, detail="At least one image URL is required")

    if len(image_urls) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_IMAGES} images allowed")

    # Validate that only one audio source is provided
    if audio and audio.filename and audio_url:
        raise HTTPException(status_code=400, detail="Provide either audio file or audio URL, not both")

    # Validate URLs
    for i, url in enumerate(image_urls):
        if not validate_image_url(url):
            raise HTTPException(status_code=400, detail=f"Invalid URL format for image {i+1}")

    if audio_url and not validate_audio_url(audio_url):
        raise HTTPException(status_code=400, detail="Invalid audio URL format")

    # Generate unique ID for this request
    request_id = str(uuid.uuid4())
    request_dir = UPLOAD_DIR / request_id
    request_dir.mkdir(exist_ok=True)

    try:
        # Download images from URLs
        image_paths = []
        async with aiohttp.ClientSession() as session:
            for i, url in enumerate(image_urls):
                # Get appropriate extension
                extension = get_image_extension_from_url(url)
                image_path = request_dir / f"image_{i:04d}{extension}"

                # Download image
                result = await download_image_from_url(session, url, image_path)
                if not result.get("success"):
                    error_msg = result.get("error", "Unknown error")
                    raise HTTPException(status_code=400, detail=f"Failed to download image {i+1} from URL: {url}. Error: {error_msg}")

                # Validate downloaded file exists and has content
                if not image_path.exists() or image_path.stat().st_size == 0:
                    raise HTTPException(status_code=400, detail=f"Downloaded image {i+1} is empty or corrupted")

                image_paths.append(image_path)

            # Handle audio if provided via URL
            audio_path = None
            if audio_url:
                # Get appropriate extension
                extension = get_audio_extension_from_url(audio_url)
                audio_path = request_dir / f"audio{extension}"

                # Download audio
                success = await download_audio_from_url(session, audio_url, audio_path)
                if not success:
                    raise HTTPException(status_code=400, detail=f"Failed to download audio from URL: {audio_url}")

                # Validate downloaded file exists and has content
                if not audio_path.exists() or audio_path.stat().st_size == 0:
                    raise HTTPException(status_code=400, detail="Downloaded audio is empty or corrupted")

        # Handle audio if provided as uploaded file
        if audio and audio.filename and not audio_url:
            if not validate_file_size(audio):
                raise HTTPException(status_code=413, detail="Audio file is too large")

            if not validate_audio_format(audio.filename):
                raise HTTPException(status_code=400, detail="Audio file has unsupported format")

            audio_path = request_dir / f"audio{Path(audio.filename).suffix}"
            await save_upload_file(audio, audio_path)

        # Create output video
        output_filename = f"video_{request_id}.mp4"
        temp_video_path = OUTPUT_DIR / f"temp_{output_filename}"
        final_video_path = OUTPUT_DIR / output_filename

        # Generate video from images with text overlay
        success = create_video_from_images(
            image_paths,
            temp_video_path if audio_path else final_video_path,
            duration_per_image,
            transition_duration,
            fps,
            text_content,
            second_text_content
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to create video from images")

        # Add audio if provided
        if audio_path:
            success = add_audio_to_video(temp_video_path, audio_path, final_video_path)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to add audio to video")

            # Clean up temp video
            if temp_video_path.exists():
                temp_video_path.unlink()

        # Clean up uploaded files
        shutil.rmtree(request_dir, ignore_errors=True)

        if not final_video_path.exists():
            raise HTTPException(status_code=500, detail="Video file was not created")

        # Return success response
        return {
            "message": "Video created successfully",
            "video_id": request_id,
            "download_url": f"/download/{output_filename}",
            "file_size": final_video_path.stat().st_size,
            "images_processed": len(image_paths),
            "audio_added": audio_path is not None,
            "audio_source": "url" if audio_url else ("file" if audio and audio.filename else None),
            "text_added": text_content is not None,
            "second_text_added": second_text_content is not None
        }

    except HTTPException:
        # Clean up on error
        shutil.rmtree(request_dir, ignore_errors=True)
        raise
    except Exception as e:
        # Clean up on error
        shutil.rmtree(request_dir, ignore_errors=True)
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/download/{filename}")
async def download_video(filename: str):
    """Download generated video"""
    file_path = OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="video/mp4"
    )

@app.delete("/cleanup/{video_id}")
async def cleanup_video(video_id: str):
    """Clean up generated video file"""
    file_path = OUTPUT_DIR / f"video_{video_id}.mp4"

    if file_path.exists():
        file_path.unlink()
        return {"message": "Video deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Video not found")

@app.get("/list-videos")
async def list_videos():
    """List all generated videos"""
    videos = []
    for file_path in OUTPUT_DIR.glob("video_*.mp4"):
        videos.append({
            "filename": file_path.name,
            "size": file_path.stat().st_size,
            "created": file_path.stat().st_ctime,
            "download_url": f"/download/{file_path.name}"
        })

    return {"videos": videos, "count": len(videos)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        timeout_keep_alive=300,  # 5 minutes for long-running video processing
        timeout_graceful_shutdown=30
    )