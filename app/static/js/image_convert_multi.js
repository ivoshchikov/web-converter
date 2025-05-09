
const fileInput   = document.getElementById("file-input");
const filesList   = document.getElementById("files-list");
const formatSel   = document.getElementById("format-select");
const qualityIn   = document.getElementById("quality-input");
const convertBtn  = document.getElementById("convert-button");
const resultsList = document.getElementById("results-list");
const downloadAll = document.getElementById("download-all");

let files = [];

// 1) При выборе файлов — читаем метаданные и показываем список
fileInput.addEventListener("change", async () => {
  files = Array.from(fileInput.files);
  filesList.innerHTML = "";
  resultsList.innerHTML = "";
  downloadAll.style.display = "none";

  for (const file of files) {
    const li = document.createElement("li");
    li.textContent = `${file.name} — ${(file.size/1024).toFixed(1)} KB`;
    // для получения размера/разрешения можно взять Image:
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.src = url;
    await img.decode();
    li.textContent += ` — ${img.width}×${img.height}px`;
    URL.revokeObjectURL(url);
    filesList.append(li);
  }
});

// 2) При клике «Конвертировать» — шлём один запрос для каждого файла
convertBtn.addEventListener("click", async () => {
  if (files.length === 0) return alert("Сначала выберите файлы!");
  resultsList.innerHTML = "";
  downloadAll.style.display = "none";

  const form = new FormData();
files.forEach(f => form.append('files', f));
form.append('target_format', formatSel.value);
form.append('quality', qualityIn.value);

const res = await fetch('/api/v1/images/convert', {
  method: 'POST',
  body: form
});
if (!res.ok) return alert('Ошибка конвертации');
  // получили готовый ZIP
  const zipBlob   = await res.blob();
  const zipObj    = await JSZip.loadAsync(zipBlob);   // читаем содержимое
  resultsList.innerHTML = "";

  // для каждого файла внутри архива показываем превью
  for (const [name, file] of Object.entries(zipObj.files)) {
    if (file.dir) continue;           // пропускаем каталоги
    const blob = await file.async("blob");
    const url  = URL.createObjectURL(blob);

    const li = document.createElement("li");
    li.innerHTML = `
      <img src="${url}" width="100" alt="${name}" />
      <p>${name} — ${(blob.size/1024).toFixed(1)} KB</p>
      <a href="${url}" download="${name}">Скачать</a>
    `;
    resultsList.append(li);
  }

  // ссылка «Скачать всё»
  const zurl = URL.createObjectURL(zipBlob);
  downloadAll.href        = zurl;
  downloadAll.download    = "converted_images.zip";
  downloadAll.style.display = "inline-block";