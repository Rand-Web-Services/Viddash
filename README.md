# Viddash (Flask)

Viddash is a free, lightweight video downloader and transcriber powered by Flask and yt-dlp. It can resolve and download videos from popular platforms (e.g., Facebook, YouTube, TikTok, Instagram, X/Twitter) with options to merge audio+video to MP4, and generate transcripts from video captions or audio.

## Features
- **Video Downloading**: Paste a supported video URL and get available formats/qualities.
- **Format Selection**: Direct download links or server-side MP4 merge (audio+video).
- **Transcript Generation** (NEW): Extract captions automatically or use AI to transcribe audio.
  - Hybrid approach: tries caption extraction first, then falls back to Whisper audio transcription
  - Export as JSON, SRT, VTT, or plain text
  - Supports multiple languages
- **Image Resizing**: Batch resize images with SEO-friendly filenames
- **Private Video Support**: Use cookies to access age-restricted or private videos
- **Built with Flask + Bootstrap** on Windows

## Prerequisites
- Windows 10/11
- Python 3.10+ (3.11 recommended)
- Internet access
- Optional but recommended: FFmpeg (needed to merge separate audio/video formats)
  - Install via Chocolatey: `choco install ffmpeg` (requires Chocolatey)
- Optional: For transcript generation (faster-whisper and pysrt are included in requirements.txt)

## Setup
```powershell
# In the project root
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

### ⚡ Development Mode (Recommended - Auto-reload on file changes)
**Option 1: Using dev.bat (easiest)**
```powershell
# Simply run the batch script - it automatically enables debug mode
.\dev.bat
```

**Option 2: Manual setup**
```powershell
set FLASK_ENV=development
set FLASK_DEBUG=1
set SSLKEYLOGFILE=
python -m flask --app app run
```

### Production Run (no auto-reload)
```powershell
python app.py
```

Open http://localhost:5000 in your browser.

**Note**: In development mode (`FLASK_DEBUG=1`), the server automatically reloads whenever you modify any Python files. This is perfect for active development!

## Production Deployment Checklist

Set these environment variables before starting the Docker/Gunicorn app for customer traffic:

```powershell
set VIDDASH_ENV=production
set VIDDASH_SECRET_KEY=<strong random secret>
set DATABASE_URL=postgresql://user:password@host:5432/viddash
set RATELIMIT_STORAGE_URI=redis://host:6379/0
set MAX_UPLOAD_SIZE_MB=100
set STRIPE_RESTRICTED_KEY=<rk_live_...>
set STRIPE_WEBHOOK_SECRET=<whsec_...>
set STRIPE_PRICE_PRO_MONTHLY=<price_...>
set STRIPE_PRICE_PRO_YEARLY=<price_...>
set STRIPE_PRICE_BUSINESS_MONTHLY=<price_...>
set STRIPE_PRICE_BUSINESS_YEARLY=<price_...>
```

Production mode intentionally refuses to boot with the development secret, local SQLite, in-memory rate limits, or upload limits above the hard cap. Heavy media-processing APIs require a paid plan; URL resolving and proxying require login.

For the low-cost DigitalOcean Droplet setup, see [DIGITALOCEAN_DEPLOYMENT.md](DIGITALOCEAN_DEPLOYMENT.md). It uses Docker Compose with Caddy, Postgres, Redis, and the Flask/Gunicorn app.

## Usage

### Video Downloader
1. Paste a video URL from a supported site (public videos recommended).
2. Click Download to fetch available formats.
3. Click a format's Download button to open the direct link.

> Note: Some private/age-restricted videos may not be accessible without authentication. You can pass cookies for private videos in the UI when needed.

### Transcript Generator
1. Go to `/transcript-generator` or click the link from the home page.
2. **Option A - From URL**: Paste a video URL and click "Generate Transcript".
3. **Option B - Upload File**: Select a local video or audio file and upload it.
4. View the transcript in the format of your choice (JSON, SRT, VTT, TXT).
5. Download or copy to clipboard.

**Hybrid Approach**:
- For URLs: First tries to extract captions directly from the video (instant, no processing needed). If captions are not available, uses Whisper AI to transcribe the audio (takes 1-2 min per 10 min of video).
- For Files: Whisper AI transcription of uploaded video/audio files.
- Supports private/restricted videos with authentication cookies (URL method only)

**Supported File Formats**:
- Video: MP4, WebM, AVI, MOV, MKV, FLV, WMV, M4V, 3GP, MPG, MPEG, TS, M3U8
- Audio: WAV, MP3, M4A, FLAC, OGG, and more

**Configuration**:
- By default, max upload size is 500 MB
- Configure max upload size with environment variable: `set MAX_UPLOAD_SIZE_MB=1000` (max 1024 MB / 1 GB hard limit)
- Example with custom 800 MB limit:
  ```powershell
  set MAX_UPLOAD_SIZE_MB=800
  python app.py
  ```

## Troubleshooting
- If you see errors containing `yt-dlp` not found, ensure it is installed via requirements and your Python environment is active.
- If some downloads fail or have no audio, try installing FFmpeg (for merging audio/video) or choose a progressive format if available.
- For transcript generation: If Whisper is slow, it's using CPU by default (int8 mode). This works but may take time on older machines.
- For file uploads: FFmpeg is required to extract audio from video files. Install via Chocolatey: `choco install ffmpeg`
- File upload fails with "413 Payload Too Large"? Increase the max upload size: `set MAX_UPLOAD_SIZE_MB=1000` (up to 1024 MB limit)
- Corporate networks or proxies may block requests; test on a home network.

## Legal
This tool is for educational purposes. Respect copyright and the terms of service of the platforms you use.
