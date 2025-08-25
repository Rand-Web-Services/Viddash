# Viddash (Flask)

Viddash is a free, lightweight video downloader powered by Flask and yt-dlp. It can resolve and download videos from popular platforms (e.g., Facebook, YouTube, TikTok, Instagram, X/Twitter) with options to merge audio+video to MP4.

## Features
- Paste a supported video URL and get available formats/qualities.
- Direct download links rendered in the UI.
- Built with Flask + Bootstrap on Windows.

## Prerequisites
- Windows 10/11
- Python 3.10+ (3.11 recommended)
- Internet access
- Optional but recommended: FFmpeg (needed to merge separate audio/video formats)
  - Install via Chocolatey: `choco install ffmpeg` (requires Chocolatey)

## Setup
```powershell
# In the project root
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```powershell
python app.py
```
Open http://localhost:5000 in your browser.

## Usage
1. Paste a video URL from a supported site (public videos recommended).
2. Click Download to fetch available formats.
3. Click a format's Download button to open the direct link.

> Note: Some private/age-restricted videos may not be accessible without authentication. You can pass cookies for private videos in the UI when needed.

## Troubleshooting
- If you see errors containing `yt-dlp` not found, ensure it is installed via requirements and your Python environment is active.
- If some downloads fail or have no audio, try installing FFmpeg (for merging audio/video) or choose a progressive format if available.
- Corporate networks or proxies may block requests; test on a home network.

## Legal
This tool is for educational purposes. Respect copyright and the terms of service of the platforms you use.
