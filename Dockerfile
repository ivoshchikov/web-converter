# ───────────────────────── app/Dockerfile ─────────────────────────
FROM python:3.12-slim

# ─── базовые переменные окружения ─────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1         \
    PORT=8080                  \
    PATH="/root/.local/bin:$PATH"

# ─── системные зависимости Pillow / reportlab / lxml ──────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        libwebp-dev     \
        libtiff5        \
        libopenjp2-7    \
    && rm -rf /var/lib/apt/lists/*

# ─── Python deps ──────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ─── проект ───────────────────────────────────────────────────────
COPY . .

# ─── Cloud Run слушает 8080 ───────────────────────────────────────
EXPOSE 8080

# ─── запуск uvicorn ───────────────────────────────────────────────
CMD ["uvicorn", "app.main:app",               \
     "--host", "0.0.0.0", "--port", "8080",   \
     "--proxy-headers",                       \
     "--forwarded-allow-ips", "*"             \
]
# ──────────────────────────────────────────────────────────────────
