# Setup Guide

## Prerequisites

- Python 3.12+
- pip
- ffmpeg (for video thumbnails)
- Git (optional)

## Installation

### Option 1: Install from source

```bash
git clone https://github.com/rkriad585/localfs.git
cd localfs
pip install -e .
python main.py
```

The first run will check for missing dependencies and offer to install them.

### Option 2: Docker

```bash
docker build -t localfs .
docker run -p 5000:5000 -v ./media:/app/media -v ./data:/app/data localfs
```

### Option 3: Installer script

**Linux / macOS:**

```bash
curl -fsSL https://raw.githubusercontent.com/rkriad585/localfs/main/installer.sh | sh
```

**Windows (PowerShell):**

```powershell
irm https://raw.githubusercontent.com/rkriad585/localfs/main/installer.ps1 | iex
```

## First Run

1. Place files to share in the `media/` directory.
2. Start the server:
   ```bash
   python main.py
   ```
3. Open the printed **Access URL** in your browser.
4. Enter the access key if prompted.

## Installing ffmpeg

Required for video thumbnail generation.

**Debian/Ubuntu:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add the `bin` directory to your PATH.
