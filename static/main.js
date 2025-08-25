const form = document.getElementById('downloadForm');
const urlInput = document.getElementById('urlInput');
const submitBtn = document.getElementById('submitBtn');
const alertBox = document.getElementById('alertBox');
const alertDiv = alertBox?.querySelector('.alert');
const result = document.getElementById('result');
const titleEl = document.getElementById('title');
const thumbEl = document.getElementById('thumb');
const metaEl = document.getElementById('meta');
const formatsTbody = document.getElementById('formats');
const cookieInput = document.getElementById('cookieInput');
const platformSelect = document.getElementById('platformSelect');
const platformHint = document.getElementById('platformHint');

const HINTS = {
  auto: 'Auto-detects site from the URL.',
  youtube: 'Public videos work. Private/unlisted may require cookies. Avoid rate limits.',
  instagram: 'Stories/Reels may need cookies. Ensure the post is accessible.',
  tiktok: 'Some links redirect; paste the canonical video URL.',
  facebook: 'Private or age-restricted videos require cookies (c_user, xs, datr).',
  twitter: 'X/Twitter may throttle. Use cookies if necessary.'
};

function updateHint() {
  const key = platformSelect?.value || 'auto';
  platformHint.textContent = HINTS[key] || '';
}
updateHint();
platformSelect?.addEventListener('change', updateHint);

function showAlert(type, message) {
  alertBox.style.display = 'block';
  alertDiv.className = `alert alert-${type}`;
  alertDiv.textContent = message;
}

function clearAlert() {
  alertBox.style.display = 'none';
  alertDiv.textContent = '';
  alertDiv.className = 'alert';
}

function setLoading(loading) {
  submitBtn.disabled = loading;
  submitBtn.textContent = loading ? 'Resolving…' : 'Download';
}

function renderResults(data) {
  if (!data) return;
  result.classList.remove('d-none');
  titleEl.textContent = data.title || 'Untitled';
  if (data.thumbnail) {
    thumbEl.src = data.thumbnail;
  } else {
    thumbEl.src = '';
  }
  const duration = data.duration ? `${Math.floor(data.duration/60)}m ${Math.floor(data.duration%60)}s` : '';
  metaEl.textContent = [data.uploader, duration, data.webpage_url].filter(Boolean).join(' • ');

  formatsTbody.innerHTML = '';
  const formats = Array.isArray(data.formats) ? data.formats : [];
  // Prefer progressive (has audio+video) and higher bitrate first
  formats.sort((a, b) => {
    const aprog = (a.has_audio && a.has_video && !a.is_hls && !a.is_dash) ? 1 : 0;
    const bprog = (b.has_audio && b.has_video && !b.is_hls && !b.is_dash) ? 1 : 0;
    if (bprog !== aprog) return bprog - aprog;
    return (b.tbr || 0) - (a.tbr || 0);
  });

  formats.forEach(f => {
    const tr = document.createElement('tr');
    const quality = f.resolution || f.format_note || '';
    const ext = f.ext || '';
    const size = f.filesize_human || '';
    const pageUrl = data.webpage_url || '';
    const cookiesVal = cookieInput?.value?.trim();
    const avBadge = f.has_audio && f.has_video
      ? '<span class="badge text-bg-success ms-1" title="Audio + Video">A+V</span>'
      : (f.has_video
        ? '<span class="badge text-bg-warning ms-1" title="Video only (no audio)">V-only</span>'
        : (f.has_audio
          ? '<span class="badge text-bg-info ms-1" title="Audio only (no video)">A-only</span>'
          : ''));

    if (f.is_hls || f.is_dash) {
      tr.innerHTML = `
        <td>${quality} <span class="badge text-bg-secondary ms-1">HLS/DASH</span></td>
        <td>${ext.toUpperCase()}</td>
        <td>${size}</td>
        <td class="text-end">
          <button class="btn btn-sm btn-secondary" disabled title="Streaming playlist; use a progressive format or download via dedicated tools.">Stream-only</button>
        </td>
      `;
    } else {
      // Progressive gets direct proxy download; otherwise expose Merge (MP4)
      const isProgressive = !!(f.has_audio && f.has_video);
      const proxied = f.url ? `/api/proxy?url=${encodeURIComponent(f.url)}` : '';
      const mergeParams = new URLSearchParams();
      if (pageUrl) mergeParams.set('url', pageUrl);
      if (f.format_id) mergeParams.set('format', f.format_id);
      if (cookiesVal) mergeParams.set('cookies', cookiesVal);
      const mergeHref = `/api/merge?${mergeParams.toString()}`;
      const showMerge = !!pageUrl; // always show merge/download

      tr.innerHTML = `
        <td>${quality} ${avBadge}</td>
        <td>${ext.toUpperCase()}</td>
        <td>${size}</td>
        <td class="text-end d-flex gap-2 justify-content-end">
          ${isProgressive && proxied ? `<a class="btn btn-sm btn-success" href="${proxied}" target="_blank" rel="noopener noreferrer">Download</a>` : ''}
          ${showMerge ? `<a class="btn btn-sm btn-primary" href="${mergeHref}" target="_blank" rel="noopener noreferrer" title="Download merged MP4 via server">Download</a>` : ''}
        </td>
      `;
    }
    formatsTbody.appendChild(tr);
  });
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearAlert();
  result.classList.add('d-none');

  const url = urlInput.value.trim();
  if (!url) {
    showAlert('warning', 'Please paste a Facebook video URL.');
    return;
  }

  try {
    setLoading(true);
    const body = { url };
    const cookieString = cookieInput?.value?.trim();
    if (cookieString) body.cookieString = cookieString;
    const res = await fetch('/api/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || `Request failed (${res.status})`);
    }
    renderResults(data);
  } catch (err) {
    showAlert('danger', err.message || 'Failed to resolve video link.');
  } finally {
    setLoading(false);
  }
});
