#!/usr/bin/env python3
"""
Test script for the Inspix Video Generation API
"""

import requests
import time
import json

# API Configuration
API_BASE_URL = "http://localhost:8000"
GENERATE_ENDPOINT = f"{API_BASE_URL}/generate-inspix-video"

def test_video_generation():
    """Test the inspix video generation endpoint"""

    print("🎬 Testing Inspix Video Generation API\n")

    # Example request data
    request_data = {
        "original_image_url": "https://picsum.photos/1200/1200",  # Sample image
        "result_image_urls": [
            "https://picsum.photos/1200/1200?random=1",
            "https://picsum.photos/1200/1200?random=2",
            "https://picsum.photos/1200/1200?random=3",
            "https://picsum.photos/1200/1200?random=4"
        ],
        "prompt_preview_text": "Epic cinematic transformation with AI",
        "style_names": [
            "Cinematic",
            "Vibrant Colors",
            "Moody & Dark",
            "Dramatic HDR"
        ],
        # "logo_url": "https://example.com/logo.png",  # Optional
        "custom_cta_text": "Link in Bio 👆"
    }

    print(f"📤 Sending request to: {GENERATE_ENDPOINT}\n")
    print(f"📋 Request data:")
    print(json.dumps(request_data, indent=2))
    print("\n⏳ Generating video (this may take 60-180 seconds)...\n")

    try:
        start_time = time.time()

        # Send request with extended timeout
        response = requests.post(
            GENERATE_ENDPOINT,
            json=request_data,
            timeout=300  # 5 minutes timeout
        )

        elapsed_time = time.time() - start_time

        # Check response
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Video generated in {elapsed_time:.1f} seconds\n")
            print(f"📊 Response:")
            print(json.dumps(result, indent=2))

            # Download the video
            download_url = f"{API_BASE_URL}{result['download_url']}"
            print(f"\n📥 Downloading video from: {download_url}")

            video_response = requests.get(download_url)
            if video_response.status_code == 200:
                filename = f"inspix_test_{result['video_id']}.mp4"
                with open(filename, 'wb') as f:
                    f.write(video_response.content)
                print(f"✅ Video saved as: {filename}")
                print(f"📦 File size: {result['file_size_mb']} MB")
            else:
                print(f"❌ Failed to download video: HTTP {video_response.status_code}")

        elif response.status_code == 400:
            print(f"❌ Bad Request (400)")
            print(f"Error: {response.json()}")

        elif response.status_code == 503:
            print(f"❌ Service Unavailable (503)")
            print(f"Error: FFmpeg is not available on this system")

        else:
            print(f"❌ Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.Timeout:
        print("❌ Request timed out. Video generation takes 60-180 seconds.")
        print("Please increase the timeout or try again.")

    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error. Is the API running at {API_BASE_URL}?")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_health_check():
    """Test the health check endpoint"""
    print("\n🏥 Testing Health Check Endpoint\n")

    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ API is healthy")
            print(f"FFmpeg available: {result.get('ffmpeg', False)}")
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")

def test_minimal_request():
    """Test with minimal required fields"""
    print("\n🎬 Testing Minimal Request (only required fields)\n")

    request_data = {
        "original_image_url": "https://picsum.photos/1200/1200",
        "result_image_urls": [
            "https://picsum.photos/1200/1200?random=1",
            "https://picsum.photos/1200/1200?random=2"
        ]
        # All other fields are optional and will be auto-generated
    }

    print(f"📋 Request data:")
    print(json.dumps(request_data, indent=2))
    print("\n⏳ Generating video...\n")

    try:
        start_time = time.time()
        response = requests.post(
            GENERATE_ENDPOINT,
            json=request_data,
            timeout=300
        )
        elapsed_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Video generated in {elapsed_time:.1f} seconds")
            print(f"Video ID: {result['video_id']}")
            print(f"File size: {result['file_size_mb']} MB")
        else:
            print(f"❌ Failed: HTTP {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("  Inspix Video Generation API - Test Suite")
    print("=" * 60)

    # Run tests
    test_health_check()
    print("\n" + "=" * 60 + "\n")

    # Choose which test to run
    print("Select test to run:")
    print("1. Full request (with all optional fields)")
    print("2. Minimal request (only required fields)")
    print("3. Both")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == "1":
        test_video_generation()
    elif choice == "2":
        test_minimal_request()
    elif choice == "3":
        test_video_generation()
        print("\n" + "=" * 60 + "\n")
        test_minimal_request()
    else:
        print("Invalid choice. Running full test...")
        test_video_generation()

    print("\n" + "=" * 60)
    print("  Test Complete")
    print("=" * 60)
