# ──────────────── app/Dockerfile ────────────────
FROM python:3.12-slim

# ─── базовые переменные окружения ───────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1         \
    PORT=8080                  \
    PATH="/root/.local/bin:$PATH"

# ─── Системные библиотеки для Pillow / reportlab ─
#     без жёстких версий, чтобы работать и в bookworm, и в trixie
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo-dev   \
        zlib1g-dev            \
        libwebp-dev           \
        libtiff-dev           \
        libopenjp2-7          \
        libfreetype6          \
        liblcms2-2            \
    && rm -rf /var/lib/apt/lists/*

# ─── Python-зависимости ─────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ─── проект ─────────────────────────────────────
COPY . .

# ─── Cloud Run слушает 8080 ─────────────────────
EXPOSE 8080
CMD ["uvicorn","app.main:app",            \
     "--host","0.0.0.0","--port","8080", \
     "--proxy-headers",                  \
     "--forwarded-allow-ips","*"         \
]
# ────────────────────────────────────────────────
