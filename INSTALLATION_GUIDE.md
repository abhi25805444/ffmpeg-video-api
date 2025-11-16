# 📦 Installation Guide

## Error: ModuleNotFoundError: No module named 'PIL'

This error occurs when the required Python packages are not installed. Here are multiple solutions:

## Solution 1: Docker/Container Environment (Recommended for `/app/main.py`)

If you're running this in Docker, add to your `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Or use `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
    environment:
      - PORT=8000
```

## Solution 2: Local Python Installation

### Step 1: Install Python (if not already installed)

Download from: https://www.python.org/downloads/

**Important:** During installation, check "Add Python to PATH"

### Step 2: Verify Installation

```bash
python --version
# or
python3 --version
```

### Step 3: Install Dependencies

```bash
# Navigate to project directory
cd D:\AndroidSdk\StudioProjects\ffmpeg-video-api

# Install packages
python -m pip install -r requirements.txt

# Or install individually:
python -m pip install fastapi uvicorn aiohttp aiofiles Pillow python-multipart pydantic
```

## Solution 3: Using Virtual Environment (Recommended for Local Development)

```bash
# Navigate to project
cd D:\AndroidSdk\StudioProjects\ffmpeg-video-api

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Solution 4: Using Conda

```bash
# Create conda environment
conda create -n ffmpeg-api python=3.11

# Activate environment
conda activate ffmpeg-api

# Install dependencies
pip install -r requirements.txt
```

## Required Packages

The `requirements.txt` includes:

- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **aiohttp** - Async HTTP client
- **aiofiles** - Async file operations
- **Pillow** - Image processing (provides PIL)
- **python-multipart** - Form data parsing
- **pydantic** - Data validation

## Verify Installation

After installing, verify all packages are installed:

```bash
python -c "import fastapi, uvicorn, aiohttp, aiofiles, PIL; print('✅ All packages installed')"
```

## Common Issues

### Issue 1: "python is not recognized"

**Solution:** Add Python to PATH or use full path:
```bash
C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe -m pip install -r requirements.txt
```

### Issue 2: Permission Denied

**Solution:** Run as administrator or use `--user` flag:
```bash
python -m pip install --user -r requirements.txt
```

### Issue 3: SSL Certificate Error

**Solution:** Use trusted host:
```bash
python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

## FFmpeg Installation

Don't forget to install FFmpeg:

### Windows:
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

### Linux:
```bash
sudo apt update
sudo apt install ffmpeg
```

### Mac:
```bash
brew install ffmpeg
```

### Verify FFmpeg:
```bash
ffmpeg -version
```

## Running the Application

After installing all dependencies:

```bash
# Direct run
python main.py

# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Testing Installation

Run the test script:

```bash
python test_inspix_api.py
```

## Need Help?

1. Check Python version: `python --version` (requires 3.8+)
2. Check pip version: `python -m pip --version`
3. List installed packages: `python -m pip list`
4. Check FFmpeg: `ffmpeg -version`

---

**Note:** If you're running in a container (Docker), make sure the Dockerfile includes all dependencies and FFmpeg installation.
