# app/main.py

from __future__ import annotations

import io
import os
import tempfile
import zipfile
from pathlib import Path
from typing import List

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from pint import UnitRegistry
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.utils.image_tools import convert_image

# -----------------------------------------------------------------------------
# Базовая настройка приложения
# -----------------------------------------------------------------------------
app = FastAPI(title="Web Converter API", version="1.0.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

ureg = UnitRegistry()

# -----------------------------------------------------------------------------
# Константы
# -----------------------------------------------------------------------------
MAX_FILES = 50
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100 MiB
ALLOWED_FMTS = {"jpeg", "png", "webp", "tiff", "bmp"}

def stream_file(path: str, chunk: int = 64 * 1024):
    """Генератор: отдаем файл частями, чтобы не держать всё в памяти"""
    with open(path, "rb") as f:
        while data := f.read(chunk):
            yield data

# -----------------------------------------------------------------------------
# 1) Главная страница – мульти-конвертер изображений
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def image_page(request: Request):
    return templates.TemplateResponse("image_convert.html", {"request": request})

@app.post("/api/v1/images/convert", summary="Batch convert images → streaming ZIP")
async def convert_images(
    files: List[UploadFile] = File(..., description="Несколько файлов"),
    target_format: str = Form(..., description="jpeg/png/webp/…"),
    quality: int = Form(80, description="Качество JPEG 1-100"),
):
    target_format = target_format.lower().strip()

    # валидация
    if target_format not in ALLOWED_FMTS:
        raise HTTPException(400, f"Формат «{target_format}» не поддерживается")
    if len(files) > MAX_FILES:
        raise HTTPException(413, f"Слишком много файлов (>{MAX_FILES})")
    total_size = sum(f.size or 0 for f in files)
    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(413, "Суммарный размер > 100 МБ")

    # готовим временный ZIP-файл
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_name = tmp.name
    tmp.close()

    with zipfile.ZipFile(tmp_name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for upload in files:
            raw = await upload.read()
            try:
                ext, data = convert_image(raw, target_format, quality)
            except Exception:
                continue
            arcname = f"{Path(upload.filename).stem}.{ext}"
            zf.writestr(arcname, data)

    headers = {
        "Content-Disposition": f'attachment; filename="converted_images_{target_format}.zip"'
    }
    resp = StreamingResponse(
        stream_file(tmp_name),
        media_type="application/zip",
        headers=headers
    )
    # удалим файл после завершения отдачи
    resp.background = lambda: os.remove(tmp_name)
    return resp

# -----------------------------------------------------------------------------
# 2) Изменение размера одного изображения
# -----------------------------------------------------------------------------
@app.post("/api/v1/images/resize", summary="Изменение размера одного изображения")
async def resize_image(
    file: UploadFile = File(...),
    width: int = Form(..., gt=0),
    height: int = Form(..., gt=0),
):
    fmt = file.filename.rsplit(".", 1)[-1].lower()
    if fmt not in ("jpeg", "jpg", "png", "webp"):
        raise HTTPException(400, "Неподдерживаемый формат")

    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        raise HTTPException(400, "Не удалось открыть изображение")

    resized = img.resize((width, height))
    buf = io.BytesIO()
    save_fmt = "JPEG" if fmt in ("jpeg", "jpg") else fmt.upper()
    resized.save(buf, save_fmt)
    buf.seek(0)

    mime = f"image/{'jpeg' if save_fmt == 'JPEG' else fmt}"
    return StreamingResponse(
        buf,
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename=resized.{fmt}"}
    )

@app.get("/resize", response_class=HTMLResponse)
async def resize_page(request: Request):
    return templates.TemplateResponse("image_resize.html", {"request": request})

# -----------------------------------------------------------------------------
# 3) DOCX → PDF
# -----------------------------------------------------------------------------
@app.get("/file", response_class=HTMLResponse)
async def file_page(request: Request):
    return templates.TemplateResponse("file_convert.html", {"request": request})

@app.post("/api/v1/files/convert/docx-to-pdf", summary="Конвертация DOCX → PDF")
async def convert_docx_to_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "Загрузите файл .docx")

    data = await file.read()
    try:
        doc = Document(io.BytesIO(data))
    except Exception:
        raise HTTPException(400, "Не удалось прочитать DOCX")

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 40
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            y -= 14
            continue
        if y < 40:
            c.showPage()
            y = h - 40
        c.drawString(40, y, text)
        y -= 14
    c.save()
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=converted.pdf"}
    )

# -----------------------------------------------------------------------------
# 4) Конвертер величин
# -----------------------------------------------------------------------------
@app.get("/units", response_class=HTMLResponse)
async def units_page(request: Request):
    return templates.TemplateResponse("unit_convert.html", {"request": request})

@app.post("/api/v1/units/convert", summary="Конвертация величин")
async def convert_units(
    value: float = Form(...),
    from_unit: str = Form(...),
    to_unit: str = Form(...),
):
    try:
        result = (value * ureg(from_unit)).to(to_unit)
    except Exception as exc:
        raise HTTPException(400, f"Ошибка конвертации: {exc}")
    return {"input": f"{value} {from_unit}", "output": f"{result.magnitude} {result.units}"}

# -----------------------------------------------------------------------------
# 5) Конвертер валют
# -----------------------------------------------------------------------------
@app.get("/currency", response_class=HTMLResponse)
async def currency_page(request: Request):
    return templates.TemplateResponse("currency_convert.html", {"request": request})

@app.post("/api/v1/currency/convert", summary="Конвертация валют")
async def convert_currency(
    value: float = Form(...),
    from_currency: str = Form(...),
    to_currency: str = Form(...),
):
    from_cur = from_currency.upper().strip()
    to_cur = to_currency.upper().strip()

    url = f"https://open.er-api.com/v6/latest/{from_cur}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(502, "Сервис курсов недоступен")

    if resp.status_code != 200:
        raise HTTPException(502, "Сервис курсов вернул ошибку")
    data = resp.json()
    if data.get("result") != "success" or "rates" not in data:
        raise HTTPException(502, "Неверные данные от сервиса")

    rates = data["rates"]
    if to_cur not in rates:
        raise HTTPException(400, f"Неверная валюта: {to_cur}")

    converted = value * rates[to_cur]
    return {"input": f"{value} {from_cur}", "output": f"{converted:.4f} {to_cur}"}
