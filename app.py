from flask import Flask, render_template, request, jsonify, Response
import subprocess
import json
import os
import requests
import tempfile
import shutil
from urllib.parse import urlparse
from flask import send_file
import socket
import ipaddress
from functools import wraps

try:
    # Optional rate limiting (only if dependency installed)
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except Exception:  # pragma: no cover
    Limiter = None
    get_remote_address = None


app = Flask(__name__)

# Optional: basic rate limiting if Flask-Limiter is installed
limiter = None
if Limiter and get_remote_address:
    limiter = Limiter(get_remote_address, app=app, default_limits=["200/hour"])  # global soft cap


# Security headers
@app.after_request
def add_security_headers(resp: Response):
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    # Minimal CSP allowing our domains and known CDNs used in the template
    csp = (
        "default-src 'self'; "
        "script-src 'self' https://pagead2.googlesyndication.com https://www.googletagmanager.com https://www.google.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://i.ytimg.com https://*.fbcdn.net https://*.googleusercontent.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    resp.headers.setdefault("Content-Security-Policy", csp)
    # HSTS should be set only when behind HTTPS in production
    if request.host and not request.host.startswith("localhost"):
        resp.headers.setdefault("Strict-Transport-Security", "max-age=15552000; includeSubDomains")
    return resp


# SSRF guard helpers
PRIVATE_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def is_private_host(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return True  # treat unresolvable as disallowed
    for family, *_ in infos:
        try:
            ip_str = infos[0][4][0] if family in (socket.AF_INET, socket.AF_INET6) else None
            if not ip_str:
                continue
            ip_obj = ipaddress.ip_address(ip_str)
            if any(ip_obj in net for net in PRIVATE_NETS):
                return True
        except Exception:
            continue
    return False


def run_yt_dlp(url: str, cookie_string: str | None = None) -> dict:
    """Run yt-dlp to retrieve metadata and formats for the provided URL.

    Returns a dict parsed from yt-dlp JSON output. For playlist-like outputs,
    returns the first item.
    """
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-warnings",
        "--no-call-home",
        "-R",
        "2",
        url,
    ]
    if cookie_string:
        # Pass cookies via header for private/restricted videos
        cmd.extend(["--add-header", f"Cookie: {cookie_string}"])
    completed = subprocess.run(
        cmd, capture_output=True, text=True, timeout=60, check=False
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(stderr or "yt-dlp failed")

    # Some URLs may output multiple JSON lines; use the first non-empty one.
    lines = [l for l in (completed.stdout or "").splitlines() if l.strip()]
    if not lines:
        raise RuntimeError("No output from yt-dlp")
    data = json.loads(lines[0])
    return data


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/privacy")
def privacy():
    return render_template("privacy.html")


@app.get("/terms")
def terms():
    return render_template("terms.html")


@app.get("/dmca")
def dmca():
    return render_template("dmca.html")


@app.get("/robots.txt")
def robots_txt():
    base = request.url_root.rstrip("/")
    body = f"""User-agent: *
Allow: /
Sitemap: {base}/sitemap.xml
"""
    return Response(body, mimetype="text/plain")


@app.get("/sitemap.xml")
def sitemap_xml():
    base = request.url_root.rstrip("/")
    urls = [
        f"{base}/",
        f"{base}/privacy",
        f"{base}/terms",
        f"{base}/dmca",
        f"{base}/facebook-downloader",
        f"{base}/youtube-downloader",
        f"{base}/tiktok-downloader",
    ]
    items = "".join(
        f"<url><loc>{u}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>" for u in urls
    )
    xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
        + items +
        "</urlset>"
    )
    return Response(xml, mimetype="application/xml")


@app.get("/facebook-downloader")
def page_facebook():
    return render_template("facebook-downloader.html")


@app.get("/youtube-downloader")
def page_youtube():
    return render_template("youtube-downloader.html")


@app.get("/tiktok-downloader")
def page_tiktok():
    return render_template("tiktok-downloader.html")


@app.post("/api/resolve")
def resolve():
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()
    cookie_string = (payload.get("cookieString") or "").strip() or None
    if not url:
        return jsonify({"error": "Missing url"}), 400

    try:
        info = run_yt_dlp(url, cookie_string=cookie_string)
        formats = info.get("formats") or []

        def human_size(n):
            try:
                n = int(n)
            except Exception:
                return None
            units = ["B", "KB", "MB", "GB", "TB"]
            i = 0
            f = float(n)
            while f >= 1024 and i < len(units) - 1:
                f /= 1024
                i += 1
            return f"{f:.1f} {units[i]}"

        result_formats = []
        for f in formats:
            if not f.get("url"):
                continue
            res = f.get("resolution")
            if not res:
                w = f.get("width")
                h = f.get("height")
                if w and h:
                    res = f"{w}x{h}"
            ext = (f.get("ext") or "").lower()
            protocol = (f.get("protocol") or "").lower()
            is_hls = ext == "m3u8" or "m3u8" in protocol
            is_dash = ext in ("mpd", "dash") or "dash" in protocol
            has_audio = (f.get("acodec") and f.get("acodec") != "none")
            has_video = (f.get("vcodec") and f.get("vcodec") != "none")
            item = {
                "format_id": f.get("format_id"),
                "ext": f.get("ext"),
                "resolution": res,
                "fps": f.get("fps"),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "filesize_human": human_size(
                    f.get("filesize") or f.get("filesize_approx")
                ),
                "vcodec": f.get("vcodec"),
                "acodec": f.get("acodec"),
                "tbr": f.get("tbr"),
                "url": f.get("url"),
                "format_note": f.get("format_note"),
                "protocol": f.get("protocol"),
                "is_hls": is_hls,
                "is_dash": is_dash,
                "has_audio": has_audio,
                "has_video": has_video,
            }
            result_formats.append(item)

        response = {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "webpage_url": info.get("webpage_url"),
            "formats": result_formats,
        }
        return jsonify(response)

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Resolver timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/proxy")
def proxy_download():
    target = request.args.get("url", type=str)
    if not target:
        return jsonify({"error": "Missing url"}), 400
    parsed = urlparse(target)
    if parsed.scheme not in ("http", "https"):
        return jsonify({"error": "Invalid url scheme"}), 400
    do_head = request.args.get("head", default="0") in ("1", "true", "True")

    # SSRF guard: block private/link-local/loopback destinations
    if not parsed.netloc:
        return jsonify({"error": "Invalid target"}), 400
    hostname = parsed.hostname or ""
    if is_private_host(hostname):
        return jsonify({"error": "Target not allowed"}), 403

    try:
        headers = {}
        # Forward Range for partial content support (video players, resumable downloads)
        if "Range" in request.headers:
            headers["Range"] = request.headers.get("Range")
        # Supply a reasonable UA to avoid some upstream blocks
        headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        )
        # Forward common headers if present
        if "Accept" in request.headers:
            headers["Accept"] = request.headers.get("Accept")
        if "Accept-Language" in request.headers:
            headers["Accept-Language"] = request.headers.get("Accept-Language")
        if "Origin" in request.headers:
            headers["Origin"] = request.headers.get("Origin")
        # Some CDNs are picky about these fetch headers
        for key in ("Sec-Fetch-Mode", "Sec-Fetch-Site", "Sec-Fetch-Dest"):
            if key in request.headers:
                headers[key] = request.headers.get(key)
        # Set a site-appropriate Referer for some CDNs
        netloc = parsed.netloc.lower()
        if "googlevideo.com" in netloc:
            headers.setdefault("Referer", "https://www.youtube.com/")
        elif "fbcdn" in netloc or "facebook.com" in netloc or "fna.fbcdn.net" in netloc:
            headers.setdefault("Referer", "https://www.facebook.com/")
        if do_head:
            resp = requests.head(target, headers=headers, allow_redirects=True, timeout=15)
            # Summarize useful headers
            subset = {
                k: v
                for k, v in resp.headers.items()
                if k in ("Content-Type", "Content-Length", "Accept-Ranges", "Content-Range", "Server", "Date", "Cache-Control")
            }
            return jsonify({
                "status": resp.status_code,
                "ok": resp.ok,
                "reason": resp.reason,
                "headers": subset,
                "final_url": str(resp.url),
            }), (200 if resp.ok else 502)

        upstream = requests.get(target, headers=headers, stream=True, timeout=30)
    except requests.RequestException as e:
        return jsonify({"error": f"Upstream error: {e}"}), 502

    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    # Enforce content type and size limits before streaming
    MAX_BYTES = 1_500_000_000  # ~1.5 GB cap
    allowed_types = ("video/", "audio/", "application/octet-stream")
    ctype = upstream.headers.get("Content-Type", "")
    if not any(ctype.startswith(pfx) for pfx in allowed_types):
        # allow if extension suggests media, else block
        return jsonify({"error": f"Disallowed content-type: {ctype}"}), 415

    cl_header = upstream.headers.get("Content-Length")
    try:
        if cl_header and int(cl_header) > MAX_BYTES:
            return jsonify({"error": "File too large"}), 413
    except Exception:
        pass

    resp_headers = {}
    ct = upstream.headers.get("Content-Type")
    if ct:
        resp_headers["Content-Type"] = ct
    cl = upstream.headers.get("Content-Length")
    if cl:
        resp_headers["Content-Length"] = cl
    cd = upstream.headers.get("Content-Disposition")
    if cd:
        resp_headers["Content-Disposition"] = cd
    cr = upstream.headers.get("Content-Range")
    if cr:
        resp_headers["Content-Range"] = cr

    total = 0

    def limited_generate():
        nonlocal total
        for chunk in upstream.iter_content(chunk_size=8192):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_BYTES:
                break
            yield chunk
        upstream.close()

    status = upstream.status_code
    return Response(limited_generate(), status=status, headers=resp_headers)


@app.get("/api/merge")
def merge_download():
    """
    Download and merge best video+audio (or selected format) into a single MP4.
    Query params:
      - url: original webpage URL (required)
      - format: optional yt-dlp format selector or format_id to prioritize
      - cookies: optional raw Cookie header string
    """
    page_url = request.args.get("url", type=str)
    if not page_url:
        return jsonify({"error": "Missing url"}), 400
    cookie_string = request.args.get("cookies")
    prefer = request.args.get("format")

    # Build yt-dlp command to merge to mp4
    # Strategy: try specific format if given; otherwise bestvideo+bestaudio fallback, then best
    fmt_selector = None
    if prefer:
        # If user passes a simple format_id, prefer it combined with bestaudio when possible
        # Otherwise they can pass a full selector like "bv*+ba/b".
        if "+" in prefer or "/" in prefer:
            fmt_selector = prefer
        else:
            fmt_selector = f"{prefer}+bestaudio/b"
    else:
        fmt_selector = "bv*+ba/b[ext=mp4]/best"

    tmpdir = tempfile.mkdtemp(prefix="merge_")
    # Output template: safe default name
    outtmpl = "%(title).80B.%(ext)s"

    cmd = [
        "yt-dlp",
        "--no-warnings",
        "--no-call-home",
        "--no-playlist",
        "--restrict-filenames",
        "--max-filesize",
        "1500M",
        "-f",
        fmt_selector,
        "--merge-output-format",
        "mp4",
        "-o",
        outtmpl,
        page_url,
    ]
    if cookie_string:
        cmd.extend(["--add-header", f"Cookie: {cookie_string}"])

    try:
        completed = subprocess.run(
            cmd,
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=1200,
            check=False,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": "Merge timed out"}), 504
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": str(e)}), 500

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        # sanitize potential sensitive lines
        redacted = []
        for line in stderr.splitlines():
            if "cookie:" in line.lower() or "set-cookie" in line.lower():
                continue
            redacted.append(line)
        stderr = "\n".join(redacted).strip()
        # Common hint: FFmpeg missing
        if "ffmpeg" in stderr.lower():
            hint = " FFmpeg may be required for merging. Install FFmpeg and ensure it's in PATH."
        else:
            hint = ""
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": (stderr or "yt-dlp failed") + hint}), 502

    # Determine output file by scanning tmpdir
    def list_files(root):
        out = []
        for name in os.listdir(root):
            p = os.path.join(root, name)
            if os.path.isfile(p):
                out.append(p)
        return out

    files = list_files(tmpdir)
    # Prefer mp4
    mp4s = [p for p in files if p.lower().endswith(".mp4")]
    filename = None
    if mp4s:
        # choose largest mp4
        filename = max(mp4s, key=lambda p: os.path.getsize(p))
    elif files:
        # fallback: largest file
        filename = max(files, key=lambda p: os.path.getsize(p))

    if not filename or not os.path.exists(filename):
        err_snippet = (completed.stderr or "").strip().splitlines()[-5:]
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({
            "error": "Merged file not found",
            "details": "\n".join(err_snippet)
        }), 500

    # Stream file to client, then cleanup directory after response is closed
    def cleanup(response):
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        finally:
            return response

    resp = send_file(
        filename,
        as_attachment=True,
        download_name=os.path.basename(filename),
        mimetype="video/mp4",
        conditional=True,
        max_age=0,
    )
    return cleanup(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
