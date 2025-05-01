document.getElementById("file-form").addEventListener("submit", async e => {
    e.preventDefault();
    const form = e.target;
    const data = new FormData(form);
    const resDiv = document.getElementById("file-result");
    resDiv.textContent = "Конвертация…";
  
    try {
      const res = await fetch("/api/v1/files/convert/docx-to-pdf", {
        method: "POST",
        body: data
      });
      if (!res.ok) throw new Error(`Ошибка ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      resDiv.innerHTML =
        `<a href="${url}" download="converted.pdf">Скачать PDF</a>`;
    } catch (err) {
      resDiv.textContent = `Ошибка: ${err.message}`;
    }
  });
  