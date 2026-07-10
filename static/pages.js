(function () {
  if (window.lucide) window.lucide.createIcons();

  const toolSearch = document.getElementById('toolSearch');
  const filterButtons = document.querySelectorAll('[data-filter]');
  const toolCards = document.querySelectorAll('.catalog-grid .tool-card');
  let activeFilter = 'all';

  function filterTools() {
    const query = (toolSearch?.value || '').trim().toLowerCase();
    toolCards.forEach((card) => {
      const matchesText = card.textContent.toLowerCase().includes(query);
      const matchesFilter = activeFilter === 'all' || card.dataset.category === activeFilter;
      card.hidden = !(matchesText && matchesFilter);
    });
  }

  toolSearch?.addEventListener('input', filterTools);
  filterButtons.forEach((button) => {
    button.addEventListener('click', () => {
      activeFilter = button.dataset.filter || 'all';
      filterButtons.forEach((item) => item.classList.toggle('active', item === button));
      filterTools();
    });
  });

  const billingButtons = document.querySelectorAll('[data-billing]');
  const paidPrices = document.querySelectorAll('.price[data-monthly][data-yearly]');
  const billingInputs = document.querySelectorAll('[data-billing-input]');

  function setBilling(period) {
    billingButtons.forEach((button) => {
      const active = button.dataset.billing === period;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    billingInputs.forEach((input) => {
      input.value = period;
    });
    paidPrices.forEach((price) => {
      const amount = period === 'yearly' ? price.dataset.yearly : price.dataset.monthly;
      const suffix = period === 'yearly' ? '/year' : '/month';
      const yearlyMonthly = price.dataset.yearlyMonthly || Math.round(Number(price.dataset.yearly) / 12);
      const monthlyEquivalent = period === 'yearly'
        ? `<small>$${yearlyMonthly}/mo billed yearly</small>`
        : '';
      price.innerHTML = `$${amount}<span>${suffix}</span>${monthlyEquivalent}`;
    });
  }

  billingButtons.forEach((button) => {
    button.addEventListener('click', () => setBilling(button.dataset.billing || 'monthly'));
  });

  const formatSelect = document.getElementById('videoOutputFormat');
  document.querySelectorAll('.format-option').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.format-option').forEach((item) => item.classList.toggle('active', item === button));
      if (formatSelect) formatSelect.value = button.dataset.format || 'mp4';
    });
  });

  const form = document.getElementById('videoConvertForm');
  if (!form) return;

  const fileInput = document.getElementById('videoConvertFile');
  const submit = document.getElementById('videoConvertSubmit');
  const status = document.getElementById('videoConvertStatus');
  const progress = document.getElementById('videoConvertProgress');
  const label = document.getElementById('videoConvertLabel');
  const percent = document.getElementById('videoConvertPercent');
  const bar = document.getElementById('videoConvertBar');
  const detail = document.getElementById('videoConvertDetail');
  let timer = null;

  function setProgress(value, title, text) {
    const safe = Math.max(0, Math.min(100, Math.round(value)));
    progress.hidden = false;
    label.textContent = title;
    percent.textContent = `${safe}%`;
    bar.style.width = `${safe}%`;
    detail.textContent = text;
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const file = fileInput.files?.[0];
    if (!file) {
      status.textContent = 'Choose a video file first.';
      status.className = 'form-text text-danger';
      return;
    }

    const fd = new FormData();
    fd.append('file', file);
    fd.append('format', formatSelect?.value || 'mp4');
    fd.append('quality', document.getElementById('videoQuality')?.value || 'balanced');
    fd.append('resolution', document.getElementById('videoResolution')?.value || 'original');
    fd.append('fps', document.getElementById('videoFps')?.value || 'original');
    if (document.getElementById('removeAudio')?.checked) fd.append('remove_audio', '1');

    submit.disabled = true;
    submit.textContent = 'Converting...';
    status.textContent = 'Uploading video. Keep this page open until the download starts.';
    status.className = 'form-text text-muted';

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/video/convert-file');
    xhr.responseType = 'blob';
    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return;
      setProgress((e.loaded / e.total) * 55, 'Uploading video...', `${(e.loaded / 1024 / 1024).toFixed(1)} MB uploaded.`);
    };
    xhr.upload.onload = () => {
      let current = 60;
      setProgress(current, 'Upload complete.', 'Viddash is converting your video now.');
      timer = setInterval(() => {
        current = Math.min(96, current + 3);
        setProgress(current, 'Converting video...', 'The download will start automatically when ready.');
        if (current >= 96) clearInterval(timer);
      }, 1000);
    };
    xhr.onload = async () => {
      if (timer) clearInterval(timer);
      if (xhr.status >= 200 && xhr.status < 300) {
        setProgress(100, 'Ready to download.', 'Conversion complete. Starting download now.');
        const filename = /filename="?([^"]+)"?/i.exec(xhr.getResponseHeader('Content-Disposition') || '')?.[1] || `viddash-converted.${formatSelect?.value || 'mp4'}`;
        downloadBlob(xhr.response, filename);
        status.textContent = 'Done! Your converted video is downloading.';
        status.className = 'form-text text-success';
      } else {
        let message = `Conversion failed (${xhr.status})`;
        try {
          const data = JSON.parse(await xhr.response.text());
          if (window.viddashHandleApiAuth?.(data)) {
            message = 'Please sign up to continue.';
          } else {
            message = data.error || message;
          }
        } catch (err) {}
        status.textContent = message;
        status.className = 'form-text text-danger';
      }
      submit.disabled = false;
      submit.innerHTML = 'Convert Now <i data-lucide="arrow-right"></i>';
      if (window.lucide) window.lucide.createIcons();
    };
    xhr.onerror = () => {
      if (timer) clearInterval(timer);
      status.textContent = 'Upload failed. Please try again.';
      status.className = 'form-text text-danger';
      submit.disabled = false;
      submit.innerHTML = 'Convert Now <i data-lucide="arrow-right"></i>';
      if (window.lucide) window.lucide.createIcons();
    };
    xhr.send(fd);
  });
})();
