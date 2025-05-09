/* eslint-env browser */
/* global JSZip */

const fileInput   = document.getElementById("file-input");
const filesList   = document.getElementById("files-list");
const formatSel   = document.getElementById("format-select");
const qualityIn   = document.getElementById("quality-input");
const convertBtn  = document.getElementById("convert-button");
const resultsList = document.getElementById("results-list");
const downloadAll = document.getElementById("download-all");

let files = [];

/* ---------- 1. выбор файлов: показываем информацию ---------- */
fileInput.addEventListener("change", async () => {
  files = Array.from(fileInput.files);

  filesList.innerHTML   = "";
  resultsList.innerHTML = "";
  downloadAll.style.display = "none";

  for (const file of files) {
    const li  = document.createElement("li");
    li.textContent = `${file.name} — ${(file.size / 1024).toFixed(1)} KB`;

    /* берём размеры изображения */
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.src   = url;
    await img.decode();
    li.textContent += ` — ${img.width}×${img.height}px`;
    URL.revokeObjectURL(url);

    filesList.append(li);
  }
});

/* ---------- 2. кликаем «Конвертировать»: один запрос → ZIP ---------- */
convertBtn.addEventListener("click", async () => {
  if (files.length === 0) {
    alert("Сначала выберите файлы!");
    return;
  }

  resultsList.innerHTML   = "";
  downloadAll.style.display = "none";

  /* собираем форму */
  const form = new FormData();
  files.forEach(f => form.append("files", f));
  form.append("target_format", formatSel.value);
  form.append("quality",       qualityIn.value);

  /* отправляем */
  const res = await fetch("/api/v1/images/convert", {
    method: "POST",
    body:   form
  });

  if (!res.ok) {
    alert("Ошибка конвертации");
    return;
  }

  /* получили ZIP-архив */
  const zipBlob = await res.blob();
  const zip     = await JSZip.loadAsync(zipBlob);

  /* выводим каждый файл из архива */
  for (const [name, entry] of Object.entries(zip.files)) {
    if (entry.dir) continue;                       // пропускаем каталоги

    const blob = await entry.async("blob");
    const url  = URL.createObjectURL(blob);

    const li = document.createElement("li");
    li.innerHTML = `
      <img src="${url}" width="100" alt="${name}">
      <p>${name} — ${(blob.size / 1024).toFixed(1)} KB</p>
      <a href="${url}" download="${name}">Скачать</a>
    `;
    resultsList.append(li);
  }

  /* кнопка «Скачать всё» */
  const zipUrl = URL.createObjectURL(zipBlob);
  downloadAll.href           = zipUrl;
  downloadAll.download       = "converted_images.zip";
  downloadAll.style.display  = "inline-block";
});     // ← ← закрываем addEventListener
