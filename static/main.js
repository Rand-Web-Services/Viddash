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
const advancedToggle = document.getElementById('advancedToggle');
const advancedPanel = document.getElementById('advancedPanel');
const videoStatus = document.getElementById('videoStatus');
const videoPresets = document.querySelectorAll('.preset-btn');
const presetSelect = document.getElementById('presetSelect');
const bestMergeBtn = document.getElementById('bestMergeBtn');
const copyPageBtn = document.getElementById('copyPageBtn');

const HINTS = {
  auto: 'Auto-detects site from the URL.',
  youtube: 'Public videos work. Private/unlisted may require cookies. Avoid rate limits.',
  instagram: 'Stories/Reels may need cookies. Ensure the post is accessible.',
  tiktok: 'Some links redirect; paste the canonical video URL.',
  facebook: 'Private or age-restricted videos require cookies (c_user, xs, datr).',
  twitter: 'X/Twitter may throttle. Use cookies if necessary.'
};
let lastResolveData = null;

function currentPlanRank() {
  const plan = window.viddashAuthState?.plan || 'free';
  return { free: 0, pro: 1, business: 2 }[plan] || 0;
}

function canUsePlan(requiredPlan) {
  if (!requiredPlan) return true;
  const requiredRank = { free: 0, pro: 1, business: 2 }[requiredPlan] || 0;
  return currentPlanRank() >= requiredRank;
}

function rememberPendingVideoUrl() {
  try {
    const url = urlInput?.value?.trim();
    if (url) localStorage.setItem('viddash-pending-video-url', url);
  } catch (err) {}
}

function restorePendingVideoUrl() {
  try {
    const pending = localStorage.getItem('viddash-pending-video-url');
    if (pending && urlInput && !urlInput.value) {
      urlInput.value = pending;
      setVideoStatus('Welcome back. Your video link is ready, so you can continue the download.', 'success');
      localStorage.removeItem('viddash-pending-video-url');
    }
  } catch (err) {}
}

function startBackgroundDownload(url) {
  if (!url) return;
  const frameId = 'viddashDownloadFrame';
  let frame = document.getElementById(frameId);
  if (!frame) {
    frame = document.createElement('iframe');
    frame.id = frameId;
    frame.name = frameId;
    frame.title = 'Viddash download';
    frame.hidden = true;
    frame.style.display = 'none';
    document.body.appendChild(frame);
  }
  frame.src = url;
}

function startBackgroundPost(path, fields) {
  if (!path) return;
  const frameId = 'viddashDownloadFrame';
  let frame = document.getElementById(frameId);
  if (!frame) {
    frame = document.createElement('iframe');
    frame.id = frameId;
    frame.name = frameId;
    frame.title = 'Viddash download';
    frame.hidden = true;
    frame.style.display = 'none';
    document.body.appendChild(frame);
  }
  const formEl = document.createElement('form');
  formEl.method = 'POST';
  formEl.action = path;
  formEl.target = frame.name;
  formEl.hidden = true;
  Object.entries(fields || {}).forEach(([name, value]) => {
    if (value === undefined || value === null || value === '') return;
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = name;
    input.value = value;
    formEl.appendChild(input);
  });
  document.body.appendChild(formEl);
  formEl.submit();
  window.setTimeout(() => formEl.remove(), 1000);
}

function escapeAttribute(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

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

function setVideoStatus(message, type) {
  if (!videoStatus) return;
  videoStatus.textContent = message || '';
  videoStatus.className = type ? `form-text text-${type}` : 'form-text';
}

if (advancedToggle && advancedPanel) {
  advancedToggle.addEventListener('click', () => {
    const isHidden = advancedPanel.hasAttribute('hidden');
    if (isHidden) {
      advancedPanel.removeAttribute('hidden');
      advancedToggle.setAttribute('aria-expanded', 'true');
      advancedToggle.textContent = 'Hide advanced options';
    } else {
      advancedPanel.setAttribute('hidden', '');
      advancedToggle.setAttribute('aria-expanded', 'false');
      advancedToggle.textContent = 'Advanced options';
    }
  });
}

function renderResults(data) {
  if (!data) return;
  lastResolveData = data;
  result.classList.remove('d-none');
  titleEl.textContent = data.title || 'Untitled';
  if (data.thumbnail) {
    thumbEl.src = data.thumbnail;
  } else {
    thumbEl.src = '';
  }
  const duration = data.duration ? `${Math.floor(data.duration/60)}m ${Math.floor(data.duration%60)}s` : '';
  const pageUrl = data.webpage_url || '';
  metaEl.textContent = [data.uploader, duration, pageUrl].filter(Boolean).join(' • ');
  formatsTbody.innerHTML = '';
  const formats = Array.isArray(data.formats) ? data.formats : [];
  if (!result.dataset.preset) result.dataset.preset = 'best';
  const preset = result.dataset.preset || '';
  const forceMerge = false;
  const getSize = (f) => (f.filesize || f.filesize_approx || 0);
  const isProgressive = (f) => (f.has_audio && f.has_video && !f.is_hls && !f.is_dash);
  const isAudioOnly = (f) => (f.has_audio && !f.has_video && !f.is_hls && !f.is_dash);
  const hasProgressive = formats.some(isProgressive);
  const bestProgressive = formats.filter(isProgressive).sort((a, b) => (b.tbr || 0) - (a.tbr || 0))[0];

  if (bestMergeBtn) {
    if (bestProgressive?.url) {
      bestMergeBtn.href = `/api/proxy?url=${encodeURIComponent(bestProgressive.url)}`;
      bestMergeBtn.textContent = 'Best download (A+V)';
      bestMergeBtn.classList.add('download-action');
      bestMergeBtn.dataset.requiresLogin = 'true';
      delete bestMergeBtn.dataset.requiresPlan;
      bestMergeBtn.classList.remove('d-none');
    } else if (pageUrl) {
      const mergeParams = new URLSearchParams();
      mergeParams.set('url', pageUrl);
      bestMergeBtn.href = `/api/merge?${mergeParams.toString()}`;
      bestMergeBtn.dataset.mergeUrl = pageUrl;
      delete bestMergeBtn.dataset.mergeFormat;
      bestMergeBtn.textContent = 'Best MP4 (with audio)';
      bestMergeBtn.classList.add('download-action');
      bestMergeBtn.dataset.requiresLogin = 'true';
      bestMergeBtn.dataset.requiresPlan = 'pro';
      bestMergeBtn.classList.remove('d-none');
    } else {
      bestMergeBtn.classList.add('d-none');
    }
  }
  if (copyPageBtn) {
    if (pageUrl) {
      copyPageBtn.classList.remove('d-none');
      copyPageBtn.onclick = async () => {
        try {
          await navigator.clipboard.writeText(pageUrl);
          copyPageBtn.textContent = 'Copied';
          setTimeout(() => (copyPageBtn.textContent = 'Copy page link'), 1200);
        } catch (err) {
          copyPageBtn.textContent = 'Copy failed';
          setTimeout(() => (copyPageBtn.textContent = 'Copy page link'), 1200);
        }
      };
    } else {
      copyPageBtn.classList.add('d-none');
    }
  }

  let recommendedId = '';
  if (preset === 'best') {
    const candidates = formats.filter(isProgressive);
    const best = candidates.sort((a, b) => (b.tbr || 0) - (a.tbr || 0))[0];
    recommendedId = best?.format_id || '';
  } else if (preset === 'small') {
    const candidates = formats.filter(isProgressive);
    const smallest = candidates.sort((a, b) => getSize(a) - getSize(b))[0];
    recommendedId = smallest?.format_id || '';
  } else if (preset === 'audio') {
    const candidates = formats.filter(isAudioOnly);
    const best = candidates.sort((a, b) => (b.tbr || 0) - (a.tbr || 0))[0];
    recommendedId = best?.format_id || '';
  }
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
    const isRecommended = !!(recommendedId && f.format_id === recommendedId);
    const recBadge = isRecommended ? '<span class="badge text-bg-primary ms-1">Recommended</span>' : '';
    const avBadge = f.has_audio && f.has_video
      ? '<span class="badge text-bg-success ms-1" title="Audio + Video">A+V</span>'
      : (f.has_video
        ? '<span class="badge text-bg-warning ms-1" title="Video only (no audio)">V-only</span>'
        : (f.has_audio
          ? '<span class="badge text-bg-info ms-1" title="Audio only (no video)">A-only</span>'
          : ''));

    if (f.is_hls || f.is_dash) {
      tr.innerHTML = `
        <td>${quality} <span class="badge text-bg-secondary ms-1">HLS/DASH</span> ${recBadge}</td>
        <td>${ext.toUpperCase()}</td>
        <td>${size}</td>
        <td class="text-end">
          <button class="btn btn-sm btn-secondary" disabled title="Streaming playlist; use a progressive format or download via dedicated tools.">Stream-only</button>
        </td>
      `;
    } else {
      // Progressive gets direct proxy download; otherwise force merged MP4 to ensure audio.
      const isProgressiveRow = !!(f.has_audio && f.has_video);
      const isAudioOnlyRow = !!(f.has_audio && !f.has_video);
      const isVideoOnly = !!(f.has_video && !f.has_audio);
      const proxied = f.url ? `/api/proxy?url=${encodeURIComponent(f.url)}` : '';
      const mergeParams = new URLSearchParams();
      if (pageUrl) mergeParams.set('url', pageUrl);
      if (f.format_id && f.has_video) mergeParams.set('format', f.format_id);
      const mergeHref = `/api/merge?${mergeParams.toString()}`;
      const mergeAttrs = `data-merge-url="${escapeAttribute(pageUrl)}" data-merge-format="${escapeAttribute(f.format_id || '')}"`;
      const showMerge = !!pageUrl && (f.has_video || isProgressiveRow || isVideoOnly);
      tr.innerHTML = `
        <td>${quality} ${avBadge} ${recBadge}</td>
        <td>${ext.toUpperCase()}</td>
        <td>${size}</td>
        <td class="text-end d-flex gap-2 justify-content-end">
          ${(!forceMerge && isProgressiveRow && proxied) ? `<a class="btn btn-sm btn-success download-action" href="${proxied}" data-requires-login="true">Direct (A+V)</a>` : ''}
          ${(!isAudioOnlyRow && showMerge) ? `<a class="btn btn-sm btn-primary download-action" href="${mergeHref}" ${mergeAttrs} data-requires-login="true" data-requires-plan="pro" title="Download merged MP4 via server">MP4 (with audio)</a>` : ''}
          ${f.url ? `<button class="btn btn-sm btn-outline-secondary copy-link" data-url="${f.url}">Copy link</button>` : ''}
        </td>
      `;
      if (isRecommended) tr.classList.add('preset-row');
    }
    formatsTbody.appendChild(tr);
  });
  if (!hasProgressive) {
    setVideoStatus('No direct audio+video format found. Use “MP4 (with audio)” for a merged download.', 'warning');
  } else {
    const platform = platformSelect?.value || 'auto';
    const extra = (platform === 'facebook' || platform === 'twitter')
      ? ' For Facebook/X, use “MP4 (with audio)” to ensure sound.'
      : '';
    setVideoStatus(`Tip: If a direct download is silent, use “Best MP4 (with audio)”.${extra}`, 'muted');
  }
}

function handleProtectedDownload(link, event) {
  event.preventDefault();
  const requiresLogin = link.dataset.requiresLogin === 'true';
  const requiredPlan = link.dataset.requiresPlan || '';
  if (requiresLogin && !window.viddashAuthState?.authenticated) {
    rememberPendingVideoUrl();
    window.viddashShowLoginPrompt?.();
    setVideoStatus('Create a free account to start your download. We kept your video link on this page.', 'warning');
    return true;
  }
  if (requiredPlan && !canUsePlan(requiredPlan)) {
    rememberPendingVideoUrl();
    window.viddashShowUpgradePrompt?.();
    setVideoStatus('Merged MP4 downloads need Pro. Use a Direct (A+V) option if one is available, or upgrade for server-side merging.', 'warning');
    return true;
  }
  const originalText = link.textContent;
  const isMerged = requiredPlan === 'pro';
  const href = link.getAttribute('href');
  setVideoStatus(
    isMerged
      ? 'Preparing your merged MP4 in the background. Stay on this page; your browser will save the file when it is ready.'
      : 'Download started in the background. Check your browser downloads or Downloads folder if you do not see it.',
    'success'
  );
  link.classList.add('disabled');
  link.setAttribute('aria-busy', 'true');
  link.textContent = isMerged ? 'Preparing download...' : 'Starting download...';
  if (isMerged && link.dataset.mergeUrl) {
    startBackgroundPost('/api/merge', {
      url: link.dataset.mergeUrl,
      format: link.dataset.mergeFormat || '',
      cookies: cookieInput?.value?.trim() || '',
    });
  } else {
    startBackgroundDownload(href);
  }
  window.setTimeout(() => {
    link.classList.remove('disabled');
    link.removeAttribute('aria-busy');
    link.textContent = originalText;
    setVideoStatus(
      isMerged
        ? 'The merged download should start automatically when ready. You can continue using Viddash while it prepares.'
        : 'If the file did not appear, check your browser downloads bar or Downloads folder, then try another format.',
      'muted'
    );
  }, isMerged ? 12000 : 5000);
  return true;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearAlert();
  result.classList.add('d-none');
  setVideoStatus('');

  const url = urlInput.value.trim();
  if (!url) {
    showAlert('warning', 'Please paste a video URL.');
    return;
  }

  try {
    setLoading(true);
    setVideoStatus('Fetching available formats…', 'muted');
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
      if (window.viddashHandleApiAuth?.(data)) return;
      throw new Error(data.error || `Request failed (${res.status})`);
    }
    renderResults(data);
    setVideoStatus('Formats ready. Choose a download.', 'success');
  } catch (err) {
    showAlert('danger', err.message || 'Failed to resolve video link.');
    setVideoStatus('Could not fetch formats. Try again or use cookies for private videos.', 'danger');
  } finally {
    setLoading(false);
  }
});

formatsTbody?.addEventListener('click', async (e) => {
  const downloadLink = e.target?.closest('.download-action');
  if (downloadLink && handleProtectedDownload(downloadLink, e)) return;

  const btn = e.target?.closest('.copy-link');
  if (!btn) return;
  const url = btn.getAttribute('data-url');
  if (!url) return;
  try {
    await navigator.clipboard.writeText(url);
    btn.textContent = 'Copied';
    setTimeout(() => (btn.textContent = 'Copy link'), 1200);
  } catch (err) {
    btn.textContent = 'Copy failed';
    setTimeout(() => (btn.textContent = 'Copy link'), 1200);
  }
});

bestMergeBtn?.addEventListener('click', (e) => {
  handleProtectedDownload(bestMergeBtn, e);
});

if (videoPresets.length) {
  videoPresets.forEach(btn => {
    btn.addEventListener('click', () => {
      const preset = btn.getAttribute('data-preset') || '';
      result.dataset.preset = preset;
      if (presetSelect) presetSelect.value = preset;
      setVideoStatus(`Preset set: ${btn.textContent}.`, 'muted');
      if (lastResolveData) renderResults(lastResolveData);
    });
  });
}

presetSelect?.addEventListener('change', () => {
  const preset = presetSelect.value || 'best';
  if (result) result.dataset.preset = preset;
  const matchingButton = document.querySelector(`.preset-btn[data-preset="${preset}"]`);
  setVideoStatus(`Preset set: ${matchingButton?.textContent || presetSelect.selectedOptions[0]?.textContent || preset}.`, 'muted');
  if (lastResolveData) renderResults(lastResolveData);
});

document.querySelectorAll('[data-tool-tab]').forEach((tab) => {
  tab.addEventListener('click', () => {
    const target = tab.getAttribute('data-tool-tab');
    document.querySelectorAll('[data-tool-tab]').forEach((btn) => btn.classList.toggle('active', btn === tab));
    document.querySelectorAll('[data-tool-pane]').forEach((pane) => {
      pane.classList.toggle('active', pane.getAttribute('data-tool-pane') === target);
    });
  });
});

restorePendingVideoUrl();

const imageForm = document.getElementById('imageForm');
const imageInput = document.getElementById('imageInput');
const imageDrop = document.getElementById('imageDrop');
const imgWidth = document.getElementById('imgWidth');
const imgHeight = document.getElementById('imgHeight');
const imgFormat = document.getElementById('imgFormat');
const imgQuality = document.getElementById('imgQuality');
const imgQualityVal = document.getElementById('imgQualityVal');
const imageStatus = document.getElementById('imageStatus');
const imageSubmit = document.getElementById('imageSubmit');
const presetBar = document.getElementById('presetBar');
const imageProgress = document.getElementById('imageProgress');
const imageProgressLabel = document.getElementById('imageProgressLabel');
const imageProgressPercent = document.getElementById('imageProgressPercent');
const imageProgressBar = document.getElementById('imageProgressBar');
const imageProgressDetail = document.getElementById('imageProgressDetail');
const MAX_IMAGE_BYTES = 25 * 1024 * 1024;
const MAX_IMAGE_TOTAL_BYTES = 100 * 1024 * 1024;
let imageProgressTimer = null;

function setImageStatus(message, type) {
  imageStatus.textContent = message || '';
  imageStatus.className = type ? `form-text text-${type}` : 'form-text';
}

function getFilenameFromDisposition(disposition) {
  if (!disposition) return null;
  const match = /filename\*=UTF-8''([^;]+)|filename="?([^"]+)"?/i.exec(disposition);
  return decodeURIComponent(match?.[1] || match?.[2] || '');
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 MB';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(unit < 2 ? 0 : 1)} ${units[unit]}`;
}

function setImageProgress(percent, label, detail) {
  if (!imageProgress || !imageProgressBar || !imageProgressLabel || !imageProgressPercent) return;
  const safePercent = Math.max(0, Math.min(100, Math.round(percent)));
  imageProgress.hidden = false;
  imageProgressBar.style.width = `${safePercent}%`;
  imageProgressPercent.textContent = `${safePercent}%`;
  imageProgressLabel.textContent = label || 'Processing files...';
  imageProgress.querySelector('.progress-track')?.setAttribute('aria-valuenow', String(safePercent));
  if (imageProgressDetail && detail) imageProgressDetail.textContent = detail;
}

function resetImageProgress() {
  if (imageProgressTimer) {
    clearInterval(imageProgressTimer);
    imageProgressTimer = null;
  }
  if (imageProgress) imageProgress.hidden = true;
  if (imageProgressBar) imageProgressBar.style.width = '0%';
}

function selectedImageSummary(files) {
  const list = Array.from(files || []);
  const totalBytes = list.reduce((sum, file) => sum + (file.size || 0), 0);
  const largest = list.reduce((max, file) => Math.max(max, file.size || 0), 0);
  return { count: list.length, totalBytes, largest };
}

function startProcessingProgress(fileCount, modeLabel) {
  if (imageProgressTimer) clearInterval(imageProgressTimer);
  let current = 62;
  const estimatedSeconds = Math.min(45, Math.max(6, Math.ceil(fileCount * 0.9)));
  const step = Math.max(1, 34 / estimatedSeconds);
  imageProgressTimer = setInterval(() => {
    current = Math.min(96, current + step);
    const doneEstimate = Math.min(fileCount, Math.max(1, Math.floor((current - 62) / 34 * fileCount)));
    setImageProgress(
      current,
      `${modeLabel} ${fileCount} image${fileCount === 1 ? '' : 's'}...`,
      `Processing ${doneEstimate} of ${fileCount}. The download will start automatically when the ZIP is ready.`
    );
    if (current >= 96) {
      clearInterval(imageProgressTimer);
      imageProgressTimer = null;
    }
  }, 1000);
}

function postImageFormWithProgress(formData, fileCount, modeLabel) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/image/resize');
    xhr.responseType = 'blob';

    xhr.upload.addEventListener('progress', (event) => {
      if (!event.lengthComputable) {
        setImageProgress(12, `Uploading ${fileCount} image${fileCount === 1 ? '' : 's'}...`, 'Upload started. Preparing files for conversion.');
        return;
      }
      const uploadPercent = Math.round((event.loaded / event.total) * 55);
      setImageProgress(
        Math.max(4, uploadPercent),
        `Uploading ${fileCount} image${fileCount === 1 ? '' : 's'}...`,
        `${formatBytes(event.loaded)} of ${formatBytes(event.total)} uploaded.`
      );
    });
    xhr.upload.addEventListener('load', () => {
      setImageProgress(60, 'Upload complete.', 'Server is converting and packaging your images now.');
      startProcessingProgress(fileCount, modeLabel);
    });

    xhr.addEventListener('load', async () => {
      if (imageProgressTimer) {
        clearInterval(imageProgressTimer);
        imageProgressTimer = null;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve({
          blob: xhr.response,
          disposition: xhr.getResponseHeader('Content-Disposition')
        });
        return;
      }
      let message = `Resize failed (${xhr.status})`;
      try {
        const text = await xhr.response.text();
        const data = JSON.parse(text);
        if (window.viddashHandleApiAuth?.(data)) {
          reject(new Error('Please sign up to continue.'));
          return;
        }
        message = data.error || message;
      } catch (err) {
        // Keep the HTTP status message when the response is not JSON.
      }
      reject(new Error(message));
    });

    xhr.addEventListener('error', () => reject(new Error('Network error while uploading images.')));
    xhr.addEventListener('abort', () => reject(new Error('Image conversion was cancelled.')));
    xhr.send(formData);
    setImageProgress(3, 'Preparing upload...', `Max batch: ${formatBytes(MAX_IMAGE_TOTAL_BYTES)} total, ${formatBytes(MAX_IMAGE_BYTES)} per image.`);
  });
}

if (imgQuality && imgQualityVal) {
  imgQualityVal.textContent = imgQuality.value;
  imgQuality.addEventListener('input', () => {
    imgQualityVal.textContent = imgQuality.value;
  });
}

if (imageDrop && imageInput) {
  imageDrop.addEventListener('dragover', (e) => {
    e.preventDefault();
    imageDrop.classList.add('dragover');
  });
  imageDrop.addEventListener('dragleave', () => {
    imageDrop.classList.remove('dragover');
  });
  imageDrop.addEventListener('drop', (e) => {
    e.preventDefault();
    imageDrop.classList.remove('dragover');
    if (e.dataTransfer?.files?.length) {
      imageInput.files = e.dataTransfer.files;
    }
  });
}

imageInput?.addEventListener('change', () => {
  resetImageProgress();
  const summary = selectedImageSummary(imageInput.files);
  if (!summary.count) {
    setImageStatus('', '');
    return;
  }
  const limitText = `Max batch: ${formatBytes(MAX_IMAGE_TOTAL_BYTES)} total, ${formatBytes(MAX_IMAGE_BYTES)} per image.`;
  if (summary.largest > MAX_IMAGE_BYTES || summary.totalBytes > MAX_IMAGE_TOTAL_BYTES) {
    setImageStatus(`${summary.count} image${summary.count === 1 ? '' : 's'} selected (${formatBytes(summary.totalBytes)}). ${limitText}`, 'danger');
    return;
  }
  setImageStatus(`${summary.count} image${summary.count === 1 ? '' : 's'} selected (${formatBytes(summary.totalBytes)}). ${limitText}`, 'muted');
});


if (presetBar) {
  presetBar.addEventListener('click', (e) => {
    const btn = e.target?.closest('button');
    if (!btn) return;
    const w = btn.getAttribute('data-w');
    const h = btn.getAttribute('data-h');
    const format = btn.getAttribute('data-format');
    const clearSize = btn.getAttribute('data-clear-size') === 'true';
    if (clearSize) {
      if (imgWidth) imgWidth.value = '';
      if (imgHeight) imgHeight.value = '';
    } else {
      if (imgWidth) imgWidth.value = w || '';
      if (imgHeight) imgHeight.value = h || '';
    }
    if (format && imgFormat) imgFormat.value = format;
    const label = format === 'webp' && clearSize ? 'PNG to WebP' : `${w}x${h}`;
    setImageStatus(`Preset applied: ${label}.`, 'muted');
  });
}

imageForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  setImageStatus('');
  resetImageProgress();

  const files = imageInput?.files;
  if (!files || files.length === 0) {
    setImageStatus('Please select one or more images.', 'danger');
    return;
  }
  const summary = selectedImageSummary(files);
  if (summary.largest > MAX_IMAGE_BYTES) {
    setImageStatus(`One image is ${formatBytes(summary.largest)}. Max per image is ${formatBytes(MAX_IMAGE_BYTES)}.`, 'danger');
    return;
  }
  if (summary.totalBytes > MAX_IMAGE_TOTAL_BYTES) {
    setImageStatus(`This batch is ${formatBytes(summary.totalBytes)}. Max batch size is ${formatBytes(MAX_IMAGE_TOTAL_BYTES)}.`, 'danger');
    return;
  }
  const w = imgWidth?.value?.trim();
  const h = imgHeight?.value?.trim();
  const selectedFormat = imgFormat?.value || 'original';
  if (!w && !h && selectedFormat === 'original') {
    setImageStatus('Enter a size or choose an output format like WebP.', 'danger');
    return;
  }

  const fd = new FormData();
  Array.from(files).forEach((file) => fd.append('images', file));
  if (w) fd.append('width', w);
  if (h) fd.append('height', h);
  if (selectedFormat) fd.append('format', selectedFormat);
  if (imgQuality?.value) fd.append('quality', imgQuality.value);

  try {
    imageSubmit.disabled = true;
    const modeLabel = selectedFormat === 'webp' && !w && !h ? 'Converting' : 'Processing';
    imageSubmit.textContent = `${modeLabel}...`;
    setImageStatus(
      `${summary.count} image${summary.count === 1 ? '' : 's'} selected (${formatBytes(summary.totalBytes)}). Max batch: ${formatBytes(MAX_IMAGE_TOTAL_BYTES)} total, ${formatBytes(MAX_IMAGE_BYTES)} per image.`,
      'muted'
    );

    const response = await postImageFormWithProgress(fd, summary.count, modeLabel);
    setImageProgress(100, 'Ready to download.', `${summary.count} image${summary.count === 1 ? '' : 's'} finished. Starting download now.`);
    const blob = response.blob;
    const filename = getFilenameFromDisposition(response.disposition) || 'viddash-images.zip';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setImageStatus('Done! Your converted images are downloading.', 'success');
  } catch (err) {
    resetImageProgress();
    setImageStatus(err.message || 'Failed to resize images.', 'danger');
  } finally {
    imageSubmit.disabled = false;
    imageSubmit.textContent = 'Resize & Download';
  }
});

// Auto-scroll to target if present in URL
(function() {
  const urlParams = new URLSearchParams(window.location.search);
  const target = urlParams.get('target');
  const path = window.location.pathname;
  if (target === 'image' || path.includes('target=image')) {
    const imageTab = document.querySelector('[data-tool-tab="image"]');
    if (imageTab) imageTab.click();
    const el = document.getElementById('video-tool-form') || document.getElementById('imageForm');
    if (el) {
      setTimeout(() => {
        el.scrollIntoView({ behavior: 'smooth' });
      }, 300);
    }
  }
})();
