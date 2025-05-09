/* eslint-env browser */
/* global JSZip */

/* ---------- DOM-ссылки ---------- */
const dropZone    = document.getElementById('drop-zone');
const fileInput   = document.getElementById('file-input');
const filesList   = document.getElementById('files-list');
const clearBtn    = document.getElementById('clear-list');

const formatSel   = document.getElementById('format-select');
const qualityIn   = document.getElementById('quality-input');
const convertBtn  = document.getElementById('convert-button');
const progressBar = document.getElementById('total-progress');

const resultsList = document.getElementById('results-list');
const downloadAll = document.getElementById('download-all');

let files = [];

/* ---------------------------------------------------------- */
/*  helpers                                                   */
/* ---------------------------------------------------------- */
function saveSettings () {
  localStorage.setItem('imgConvFmt', formatSel.value);
  localStorage.setItem('imgConvQ',   qualityIn.value);
}
function loadSettings () {
  const fmt = localStorage.getItem('imgConvFmt');
  const q   = localStorage.getItem('imgConvQ');
  if (fmt) formatSel.value = fmt;
  if (q)   qualityIn.value = q;
}

function renderFileList () {
  filesList.innerHTML   = '';
  resultsList.innerHTML = '';
  downloadAll.style.display = 'none';
  clearBtn.style.display    = files.length ? 'inline-block' : 'none';

  files.forEach(async (file, idx) => {
    const li   = document.createElement('li');
    li.className = 'file-item';

    /* превью-иконка */
    const thumb = document.createElement('img');
    thumb.width = 60;
    thumb.height = 60;
    thumb.alt  = file.name;
    thumb.src  = URL.createObjectURL(file);
    thumb.onload = () => URL.revokeObjectURL(thumb.src);

    /* подпись */
    const caption = document.createElement('span');
    caption.textContent = `${file.name}  · ${(file.size/1024).toFixed(1)} KB`;

    /* кнопка удаления */
    const btnDel = document.createElement('button');
    btnDel.className = 'file-remove';
    btnDel.innerHTML = '&times;';
    btnDel.title = 'Удалить';
    btnDel.addEventListener('click', () => {
      files.splice(idx, 1);
      renderFileList();
    });

    li.append(thumb, caption, btnDel);
    filesList.append(li);
  });
}

/* ---------------------------------------------------------- */
/*  1. Drag-and-Drop + клики + paste                          */
/* ---------------------------------------------------------- */
dropZone.addEventListener('click', () => fileInput.click());

['dragenter','dragover'].forEach(evt =>
  dropZone.addEventListener(evt, e => {
    e.preventDefault(); dropZone.classList.add('drag-over');
  }));
['dragleave','drop'].forEach(evt =>
  dropZone.addEventListener(evt, e => {
    e.preventDefault(); dropZone.classList.remove('drag-over');
  }));

dropZone.addEventListener('drop', e => {
  files.push(...[...e.dataTransfer.files].filter(f => f.type.startsWith('image/')));
  renderFileList();
});

fileInput.addEventListener('change', () => {
  files.push(...Array.from(fileInput.files));
  fileInput.value = '';          // сброс выбора
  renderFileList();
});

document.addEventListener('paste', e => {
  const imgs = [...e.clipboardData.items].filter(i => i.type.startsWith('image/'));
  imgs.forEach(i => files.push(i.getAsFile()));
  if (imgs.length) renderFileList();
});

/* очистка списка */
clearBtn.addEventListener('click', () => { files = []; renderFileList(); });

/* ---------------------------------------------------------- */
/*  2.  Конвертация                                           */
/* ---------------------------------------------------------- */
convertBtn.addEventListener('click', async () => {
  if (!files.length) { alert('Сначала выберите файлы!'); return; }

  saveSettings();

  const form = new FormData();
  files.forEach(f => form.append('files', f));
  form.append('target_format', formatSel.value);
  form.append('quality',       qualityIn.value);

  progressBar.value = 0;
  progressBar.style.display = 'block';

  const res = await fetch('/api/v1/images/convert', { method: 'POST', body: form });
  if (!res.ok) { alert('Ошибка конвертации'); progressBar.style.display='none'; return; }

  /* читаем поток с прогрессом */
  const reader      = res.body.getReader();
  const chunks      = [];
  let   received    = 0;
  const contentLen  = +res.headers.get('Content-Length') || 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    received += value.length;
    if (contentLen) progressBar.value = received / contentLen * 100;
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
      <p>${name} — ${(blob.size/1024).toFixed(1)} KB</p>
      <a href="${url}" download="${name}">Скачать</a>
    `;
    resultsList.append(li);
  }

  const zipUrl = URL.createObjectURL(zipBlob);
  downloadAll.href = zipUrl;
  downloadAll.download = 'converted_images.zip';
  downloadAll.style.display = 'inline-block';

  progressBar.style.display = 'none';
});

/* ---------- init ---------- */
loadSettings();
