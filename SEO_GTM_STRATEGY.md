# Viddash SEO + AEO Go-to-Market Strategy

## Positioning

Viddash should own the practical job-to-be-done category around preparing media for publishing:

> Convert, clean, resize, clip, transcribe, and download media in one browser workspace.

The moat is not a large number of thin tool pages. It is a connected set of useful tools backed by clear first-hand explanations, format guidance, workflow recipes, and trustworthy processing details.

## Search Growth Model

1. Capture high-intent utility searches with pages that complete the task immediately.
2. Answer adjacent questions on the same page so search and answer engines can understand when to cite it.
3. Link each tool to workflow guides and neighboring tools to move users from one task into a Viddash workflow.
4. Convert anonymous utility traffic into free accounts through useful limits, saved history, and repeat-use value.
5. Convert frequent creators to Pro when processing volume, file size, or batch needs increase.

## Intent Architecture

| Cluster | Primary page | Core intent | Supporting answers |
| --- | --- | --- | --- |
| Audio editing | `/audio-editor` | merge audio, trim MP3, podcast cleaner | formats, noise removal, loudness, privacy |
| Video conversion | `/video-converter` | convert video to MP4/MOV/WebM/GIF | codec choice, quality, compatibility |
| Video compression | `/video-compress` | reduce video file size | bitrate, quality loss, email/social limits |
| Video resizing | `/video-resizer` | resize video for Instagram/TikTok/YouTube | aspect ratios, crop vs fit, dimensions |
| Video clipping | `/video-clipper` | cut video by timestamps | highlight extraction, clip length, exports |
| Audio extraction | `/video-to-audio` | convert video to MP3/WAV/M4A | quality, format differences, copyright |
| Transcription | `/transcript-generator` | video to transcript/SRT/VTT | captions, timestamps, language support |
| Platform downloads | platform landing pages | download public videos with sound | supported URLs, quality, rights, troubleshooting |
| Creator workflow | `/guides` and future guide URLs | prepare media for a publishing outcome | tool combinations and tested settings |

Do not create dozens of format-pair pages until each page can offer genuinely distinct controls, examples, compatibility notes, and a working conversion experience.

## Page Standard

Every commercial tool page should contain:

- A title and H1 matching one clear task.
- A one-sentence direct answer before supporting detail.
- A working tool visible near the top of the page.
- A three-to-five-step usage explanation.
- Specific input/output formats and practical limits.
- A plain-language explanation of what processing changes.
- Five to eight questions based on real user uncertainty.
- Links to two adjacent tools and one relevant guide.
- Accurate privacy, account, and pricing information.
- WebApplication, BreadcrumbList, and visible FAQ-aligned structured data where applicable.

## AEO Writing Standard

- Lead answers with the answer, not scene-setting.
- Keep the first answer paragraph between roughly 40 and 80 words when the topic permits.
- Use the exact entity names consistently: `Viddash App`, `Audio Editor`, `Studio Voice`, and supported formats.
- State measurable facts such as file count, file size, output formats, and free allowance.
- Separate facts from marketing claims. Never call deterministic filtering AI or imply equivalence to a third-party model.
- Explain how results are produced and where limitations apply.
- Keep important answers in rendered HTML rather than loading them only after JavaScript runs.
- Add schema only for content that is visible on the same page.

## Trust and Entity Signals

- Keep About, Contact, Privacy, Terms, DMCA, pricing, and support details accurate and internally linked.
- Publish who builds or reviews substantial guides and why they are qualified.
- Add tested examples and methodology to guides instead of generic summaries.
- State how uploaded files are handled and deleted.
- Keep plan limits consistent across pricing, FAQ, tool pages, and API responses.
- Establish consistent organization profiles on relevant third-party platforms and link them when available.

## Technical Baseline

- One self-canonical URL per indexable page.
- Valid hreflang clusters only when the main page content is properly translated.
- Indexable pages only in XML sitemaps.
- `noindex,follow` for authentication and unfinished product pages.
- Crawl controls for API, admin, billing, and account routes.
- Unique titles and descriptions that describe the page rather than list keywords.
- Sitewide Organization and WebSite identity, plus page-specific schema.
- Descriptive social previews using a 1200x630 image.
- Fast server-rendered primary content with stable headings and links.
- No indexable search/filter parameter combinations unless intentionally designed as landing pages.

## International SEO Rule

Do not treat translated navigation as a translated page. Before an `es`, `fr`, `pt`, or `de` URL is promoted for indexing, translate its title, description, H1, tool instructions, trust copy, questions, errors, and internal links. Validate each locale with a native reviewer. Until then, English should remain the acquisition priority.

## 90-Day Execution

### Days 1-14: Foundation

- Ship metadata, schema, crawl, sitemap, and noindex corrections.
- Connect Google Search Console and Bing Webmaster Tools.
- Submit the sitemap and inspect representative tool URLs.
- Establish analytics events for organic landing, tool start, successful output, signup, and upgrade.
- Record a baseline by page, query, country, device, conversion rate, and indexed URL count.

### Days 15-45: Commercial Pages

- Upgrade the five highest-value tools to the full page standard.
- Start with audio editor, video converter, video compressor, transcript generator, and video resizer.
- Add tested format guidance and output examples.
- Build contextual links among related tools.
- Improve titles and snippets based on actual Search Console query language.

### Days 46-90: Authority and Distribution

- Publish two high-quality workflow guides per month, each based on a tested task.
- Prioritize topics such as podcast cleanup, social aspect ratios, reducing upload size without obvious quality loss, and choosing caption formats.
- Earn links through creator communities, integration partners, format references, and original benchmark data.
- Enable IndexNow when the deployment has a managed key and submission workflow.
- Review Bing AI Performance and search citation patterns where available.

## Measurement

North-star metric:

> Successful tool outputs started from non-branded organic and answer-engine referrals.

Supporting metrics:

- Non-branded impressions, clicks, and click-through rate.
- Number of landing pages receiving qualified organic traffic.
- Indexed-to-submitted URL ratio.
- Tool-start and successful-output rate by landing page.
- Organic visitor signup and paid conversion rate.
- Returning organic users within 30 days.
- AI citation and referral visibility where platforms expose it.
- Core Web Vitals and server error rate on organic landing pages.

## Guardrails

- No fabricated usage numbers, reviews, ratings, or unsupported superlatives.
- No mass-produced doorway pages for every file extension pair.
- No FAQ schema for hidden or absent answers.
- No fake freshness dates.
- No indexing of account, admin, API response, or unfinished documentation pages.
- No promise that structured data guarantees rich results or AI citations.
