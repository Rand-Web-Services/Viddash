# Viddash Project Sitemap

Use this as the working map for page-level changes. The Flask app lives in `app.py`, page templates live in `templates/`, and shared frontend assets live in `static/`.

## Shared Layout

| Area | File | Notes |
| --- | --- | --- |
| Shared header | `templates/partials/site-header.html` | Common main menu across the app. Includes primary tool links, mobile menu behavior, dark-mode toggle, and Lucide setup. |
| Shared footer | `templates/partials/site-footer.html` | Common footer links and year script. |
| Main styles | `static/styles.css` | Global app styling, responsive layout, dark mode, tool cards, pricing, FAQ, converter pages. |
| Homepage JS | `static/main.js` | Homepage downloader/image converter behavior, image progress, tabs. |
| App pages JS | `static/pages.js` | Tools search/filter, pricing billing toggle, video converter upload/progress. |
| Brand assets | `static/viddash-logo.png`, `static/viddash-latest.png` | Logo and design reference asset. |

## Marketing / Product Pages

| URL | Template | Purpose | Related JS/CSS |
| --- | --- | --- | --- |
| `/` | `templates/index.html` | Homepage with video URL downloader and image conversion panel. | `static/main.js`, `static/styles.css` |
| `/tools` | `templates/tools.html` | All Tools catalog with search and filters. | `static/pages.js` |
| `/pricing` | `templates/pricing.html` | Pricing plans with monthly/yearly toggle. | `static/pages.js` |
| `/resources` | `templates/resources.html` | Blog/resources landing page. | `static/pages.js` |
| `/faq` | `templates/faq.html` | FAQ page. | `static/pages.js` |

## Core Tool Pages

| URL | Template | Purpose | Main API(s) |
| --- | --- | --- | --- |
| `/video-converter` | `templates/video-converter.html` | Upload and convert videos to MP4, MOV, AVI, MKV, WebM, GIF. | `POST /api/video/convert-file` |
| `/video-to-audio` | `templates/video-to-audio.html` | Convert video URL/file to audio. | `POST /api/video-to-audio`, `POST /api/video-to-audio-file` |
| `/video-resizer` | `templates/video-resizer.html` | Resize/crop videos to platform presets. | `POST /api/video/resize`, `POST /api/video/resize-batch` |
| `/video-export` | `templates/video-export.html` | Multi-platform video export ZIP. | `POST /api/video/resize-batch` |
| `/video-compress` | `templates/video-compress.html` | Batch video compression to target sizes. | `POST /api/video/compress-batch` |
| `/video-watermark` | `templates/video-watermark.html` | Add logo/text watermark to videos. | `POST /api/video/watermark` |
| `/video-clipper` | `templates/video-clipper.html` | Cut one or more clips from a video. | `POST /api/video/clip` |
| `/video-thumbnails` | `templates/video-thumbnails.html` | Generate thumbnail ZIP/best frame. | `POST /api/video/thumbnails` |
| `/transcript-generator` | `templates/transcript-generator.html` | Generate transcripts from URL or file. | `POST /api/transcribe`, `POST /api/transcribe-file` |
| `/utm-builder` | `templates/utm-builder.html` | Generate UTM tracking CSVs. | `POST /api/utm/csv` |

## Downloader / SEO Pages

| URL | Template | Purpose | Main API(s) |
| --- | --- | --- | --- |
| `/facebook-downloader` | `templates/facebook-downloader.html` | Facebook downloader landing page. | Links to homepage downloader |
| `/youtube-downloader` | `templates/youtube-downloader.html` | YouTube downloader landing page. | Links to homepage downloader |
| `/tiktok-downloader` | `templates/tiktok-downloader.html` | TikTok downloader landing page. | Links to homepage downloader |

## Legal / Utility Pages

| URL | Template / Handler | Purpose |
| --- | --- | --- |
| `/privacy` | `templates/privacy.html` | Privacy policy. |
| `/terms` | `templates/terms.html` | Terms of service. |
| `/dmca` | `templates/dmca.html` | DMCA/contact page. |
| `/robots.txt` | `app.py::robots_txt` | Robots file. |
| `/sitemap.xml` | `app.py::sitemap_xml` | Search-engine XML sitemap. |
| `/target=image` | `templates/index.html` | Fallback for typo-style image target path. |

## API Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/resolve` | POST | Resolve URL formats with `yt-dlp`. |
| `/api/proxy` | GET | Proxy direct media download URL. |
| `/api/merge` | GET | Merge best video/audio to MP4. |
| `/api/video-to-audio` | POST | Convert URL video to audio. |
| `/api/video-to-audio-file` | POST | Convert uploaded media to audio. |
| `/api/video/convert-file` | POST | Convert uploaded video to target format. |
| `/api/video/resize` | POST | Resize uploaded video to one preset. |
| `/api/video/resize-batch` | POST | Export multiple resized video variants. |
| `/api/video/compress-batch` | POST | Compress video to target file sizes. |
| `/api/video/watermark` | POST | Add image/text watermark. |
| `/api/utm/csv` | POST | Generate UTM CSV. |
| `/api/video/clip` | POST | Cut video clip ZIP. |
| `/api/video/thumbnails` | POST | Generate thumbnail ZIP/best frame. |
| `/api/image/resize` | POST | Resize/convert images, including PNG to WebP bulk jobs. |
| `/api/transcribe` | POST | Generate transcript from video URL. |
| `/api/transcribe-file` | POST | Generate transcript from uploaded file. |
| `/api/max-upload-size` | GET | Return configured upload limit. |

## Page Work Notes

- For menu changes, edit `templates/partials/site-header.html`.
- For footer/legal link changes, edit `templates/partials/site-footer.html`.
- For visual system, responsive layout, and dark mode, edit `static/styles.css`.
- For homepage downloader/image converter behavior, edit `static/main.js`.
- For all-tools filtering, pricing toggle, and video converter progress, edit `static/pages.js`.
- For new routes, add the `@app.get(...)` handler in `app.py`, then add the template under `templates/`.
