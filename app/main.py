# app/main.py
"""
API-шлюз Web-Converter
 ├ /api/v1/images/convert     – пакетная конвертация, стримим ZIP on-the-fly
 ├ /api/v1/images/resize      – resize одного файла
 ├ /api/v1/files/convert/...  – DOCX → PDF
 ├ /api/v1/units/convert      – физ. величины
 └ /api/v1/currency/convert   – валюты
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import List

import httpx
import zipstream                       # ⬅ streaming-ZIP
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from pint import UnitRegistry
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.utils.image_tools import (
    SUPPORTED_INPUT_FMTS,
    SUPPORTED_OUTPUT_FMTS,
    convert_image,
)

# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Web Converter API", version="2.0.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
ureg = UnitRegistry()

MAX_FILES      = 50
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100 MiB
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница (конвертер изображений)"""
    return templates.TemplateResponse("image_convert.html", {"request": request})


# ============================================================================
# 1) Batch-convert → streaming ZIP
# ============================================================================
@app.post("/api/v1/images/convert", summary="Batch convert images → ZIP-stream")
async def convert_images(
    files: List[UploadFile] = File(...),
    target_format: str = Form(..., description="jpeg/png/webp/…"),
    quality: int = Form(80, ge=1, le=100),
):
    target_format = target_format.lower().strip()

    # ── валидация ───────────────────────────────────────────────────────────
    if target_format not in SUPPORTED_OUTPUT_FMTS:
        raise HTTPException(400, f"Формат «{target_format}» не поддерживается")
    if len(files) > MAX_FILES:
        raise HTTPException(413, f"Слишком много файлов (>{MAX_FILES})")
    total_size = sum(f.size or 0 for f in files)
    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(413, "Суммарный размер > 100 МБ")

    # ── собираем streaming-ZIP ──────────────────────────────────────────────
    z = zipstream.ZipFile(mode="w", compression=zipfile.ZIP_DEFLATED)

    for upload in files:
        raw = await upload.read()
        try:
            ext, data = convert_image(raw, target_format, quality)
        except Exception:
            # не изображение / битый файл — тихо пропускаем
            continue
        arcname = f"{Path(upload.filename).stem}.{ext}"
        z.writestr(arcname, data)

    headers = {
        "Content-Disposition": f'attachment; filename="converted_{target_format}.zip"'
    }
    return StreamingResponse(iter(z), media_type="application/zip", headers=headers)


# ============================================================================
# 2) Resize single
# ============================================================================
@app.post("/api/v1/images/resize", summary="Resize one image")
async def resize_image(
    file: UploadFile = File(...),
    width: int = Form(..., gt=0),
    height: int = Form(..., gt=0),
):
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_INPUT_FMTS:
        raise HTTPException(400, "Неподдерживаемый формат")

    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        raise HTTPException(400, "Не удалось открыть изображение")

    resized = img.resize((width, height))
    buf = io.BytesIO()
    save_fmt = "JPEG" if ext in {"jpeg", "jpg"} else ext.upper()
    resized.save(buf, save_fmt)
    buf.seek(0)

    mime = f"image/{'jpeg' if save_fmt == 'JPEG' else ext}"
    return StreamingResponse(
        buf,
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename=resized.{ext}"},
    )


@app.get("/resize", response_class=HTMLResponse)
async def resize_page(request: Request):
    return templates.TemplateResponse("image_resize.html", {"request": request})


# ============================================================================
# 3) DOCX → PDF
# ============================================================================
@app.get("/file", response_class=HTMLResponse)
async def file_page(request: Request):
    return templates.TemplateResponse("file_convert.html", {"request": request})


@app.post("/api/v1/files/convert/docx-to-pdf", summary="DOCX → PDF")
async def convert_docx_to_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "Загрузите файл .docx")

    data = await file.read()
    try:
        doc = Document(io.BytesIO(data))
    except Exception:
        raise HTTPException(400, "Не удалось прочитать DOCX")

    buf = io.BytesIO()
    canv = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    y = page_h - 40

    for para in doc.paragraphs:
        txt = para.text.strip()
        if not txt:
            y -= 14
            continue
        if y < 40:
            canv.showPage()
            y = page_h - 40
        canv.drawString(40, y, txt)
        y -= 14

    canv.save()
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=converted.pdf"},
    )


# ============================================================================
# 4) Units & Currency
# ============================================================================
@app.get("/units", response_class=HTMLResponse)
async def units_page(request: Request):
    return templates.TemplateResponse("unit_convert.html", {"request": request})


@app.post("/api/v1/units/convert", summary="Unit convert")
async def convert_units(
    value: float = Form(...), from_unit: str = Form(...), to_unit: str = Form(...)
):
    try:
        res = (value * ureg(from_unit)).to(to_unit)
    except Exception as exc:
        raise HTTPException(400, f"Ошибка конвертации: {exc}")
    return {"input": f"{value} {from_unit}", "output": f"{res.magnitude} {res.units}"}


@app.get("/currency", response_class=HTMLResponse)
async def currency_page(request: Request):
    return templates.TemplateResponse("currency_convert.html", {"request": request})


@app.post("/api/v1/currency/convert", summary="Currency convert")
async def convert_currency(
    value: float = Form(...), from_currency: str = Form(...), to_currency: str = Form(...)
):
    base, target = from_currency.strip().upper(), to_currency.strip().upper()
    url = f"https://open.er-api.com/v6/latest/{base}"

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(502, "Сервис курсов недоступен")

    if r.status_code != 200:
        raise HTTPException(502, "Ошибка сервиса курсов")

    data = r.json()
    if data.get("result") != "success" or "rates" not in data:
        raise HTTPException(502, "Неверный ответ API")

    if target not in data["rates"]:
        raise HTTPException(400, f"Неверная валюта: {target}")

    converted = value * data["rates"][target]
    return {"input": f"{value} {base}", "output": f"{converted:.4f} {target}"}
