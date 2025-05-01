document.getElementById("convert-form").addEventListener("submit", async e => {
    e.preventDefault();
    const form = e.target;
    const data = new FormData(form);
    document.getElementById("result").textContent = "Идёт конвертация…";
    try {
      const res = await fetch("/api/v1/images/convert", { method: "POST", body: data });
      if (!res.ok) throw new Error(`Ошибка ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      document.getElementById("result").innerHTML =
        `<a href="${url}" download="converted.${data.get("target_format")}">Скачать файл</a>`;
    } catch (err) {
      document.getElementById("result").textContent = `Ошибка: ${err.message}`;
    }
  });
  