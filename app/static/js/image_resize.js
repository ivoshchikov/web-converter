document.getElementById("resize-form").addEventListener("submit", async e => {
    e.preventDefault();
    const form = e.target;
    const data = new FormData(form);
    const result = document.getElementById("resize-result");
    result.textContent = "Идёт обработка…";
  
    try {
      const res = await fetch("/api/v1/images/resize", {
        method: "POST",
        body: data
      });
      if (!res.ok) throw new Error(`Ошибка ${res.status}`);
      const blob = await res.blob();
      const ext = form.width.value && form.height.value ? res.headers.get("Content-Type").split("/")[1] : "png";
      const url = URL.createObjectURL(blob);
      result.innerHTML = `<a href="${url}" download="resized.${ext}">Скачать изменённое изображение</a>`;
    } catch (err) {
      result.textContent = `Ошибка: ${err.message}`;
    }
  });
  