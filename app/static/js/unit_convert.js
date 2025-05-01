document.getElementById("unit-form").addEventListener("submit", async e => {
    e.preventDefault();
    const form = e.target;
    const data = new FormData(form);
    const resDiv = document.getElementById("unit-result");
    resDiv.textContent = "Конвертация…";
  
    try {
      const res = await fetch("/api/v1/units/convert", {
        method: "POST",
        body: data
      });
      if (!res.ok) throw new Error(`Ошибка ${res.status}`);
      const json = await res.json();
      resDiv.textContent = `${json.input} = ${json.output}`;
    } catch (err) {
      resDiv.textContent = `Ошибка: ${err.message}`;
    }
  });
  