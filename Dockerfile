# ⇢ app/Dockerfile
FROM python:3.12-slim

# ──────────────────────────────────────────────────────────────────────────────
# базовая установка
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt
COPY . .

# ──────────────────────────────────────────────────────────────────────────────
# Cloud Run ожидает, что контейнер слушает 8080
EXPOSE 8080
ENV PORT=8080

# ──────────────────────────────────────────────────────────────────────────────
# ▸ ключи --proxy-headers и --forwarded-allow-ips="*"
CMD ["uvicorn", "app.main:app",            \
     "--host", "0.0.0.0", "--port", "8080",\
     "--proxy-headers",                    \
     "--forwarded-allow-ips", "*"          \
]
