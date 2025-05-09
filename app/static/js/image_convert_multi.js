/* eslint-env browser */
/* global JSZip */
/* ---------- DOM-ссылки ---------- */
const dropZone     = document.getElementById('drop-zone');
const fileInput    = document.getElementById('file-input');
const filesList    = document.getElementById('files-list');
const formatSel    = document.getElementById('format-select');
const qualityIn    = document.getElementById('quality-input');
const convertBtn   = document.getElementById('convert-button');
const progressBar  = document.getElementById('total-progress');
const resultsList  = document.getElementById('results-list');
const downloadAll  = document.getElementById('download-all');

let files = [];

/* ---------------------------------------------------------- */
/*  helpers                                                   */
/* ---------------------------------------------------------- */
function renderFileList () {
  filesList.innerHTML   = '';
  resultsList.innerHTML = '';
  downloadAll.style.display = 'none';

  files.forEach(async (file) => {
    const li  = document.createElement('li');
    li.textContent = `${file.name} — ${(file.size / 1024).toFixed(1)} KB`;

    /* размеры изображения */
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.src   = url;
    await img.decode();
    li.textContent += ` — ${img.width}×${img.height}px`;
    URL.revokeObjectURL(url);

    filesList.append(li);
  });
}

/* ---------------------------------------------------------- */
/*  1. Drag-and-Drop + клики                                  */
/* ---------------------------------------------------------- */
dropZone.addEventListener('click', () => fileInput.click());

['dragenter', 'dragover'].forEach(evt =>
  dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  })
);

['dragleave', 'drop'].forEach(evt =>
  dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
  })
);

dropZone.addEventListener('drop', (e) => {
  files = [...e.dataTransfer.files].filter(f => f.type.startsWith('image/'));
  renderFileList();
});

/* input[type=file]  */
fileInput.addEventListener('change', () => {
  files = Array.from(fileInput.files);
  renderFileList();
});

/* ---------------------------------------------------------- */
/*  2. Paste-from-clipboard                                   */
/* ---------------------------------------------------------- */
document.addEventListener('paste', (e) => {
  const imgs = [...e.clipboardData.items].filter(i => i.type.startsWith('image/'));
  if (!imgs.length) return;

  imgs.forEach(i => files.push(i.getAsFile()));
  renderFileList();
});

/* ---------------------------------------------------------- */
/*  3.  Конвертация                                           */
/* ---------------------------------------------------------- */
convertBtn.addEventListener('click', async () => {
  if (files.length === 0) {
    alert('Сначала выберите файлы!');
    return;
  }

  /* форма для одного запроса */
  const form = new FormData();
  files.forEach(f => form.append('files', f));
  form.append('target_format', formatSel.value);
  form.append('quality',       qualityIn.value);

  progressBar.value   = 0;
  progressBar.style.display = 'block';

  const res = await fetch('/api/v1/images/convert', { method: 'POST', body: form });
  if (!res.ok) { alert('Ошибка конвертации'); progressBar.style.display='none'; return; }

  /* тянем ZIP c прогрессом */
  const reader = res.body.getReader();
  const chunks = [];
  let received = 0;
  const contentLen = +res.headers.get('Content-Length') || 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    received += value.length;
    if (contentLen) progressBar.value = (received / contentLen) * 100;
  }
  progressBar.value = 100;

  const zipBlob = new Blob(chunks);
  const zip     = await JSZip.loadAsync(zipBlob);
  resultsList.innerHTML = '';

  for (const [name, entry] of Object.entries(zip.files)) {
    if (entry.dir) continue;
    const blob = await entry.async('blob');
    const url  = URL.createObjectURL(blob);

    const li = document.createElement('li');
    li.innerHTML = `
      <img src="${url}" width="100" alt="${name}">
      <p>${name} — ${(blob.size / 1024).toFixed(1)} KB</p>
      <a href="${url}" download="${name}">Скачать</a>
    `;
    resultsList.append(li);
  }

  /* «Скачать всё» */
  const zipUrl = URL.createObjectURL(zipBlob);
  downloadAll.href = zipUrl;
  downloadAll.download = 'converted_images.zip';
  downloadAll.style.display = 'inline-block';

  progressBar.style.display = 'none';
});
