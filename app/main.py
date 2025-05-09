# app/main.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from PIL import Image
import io, zipfile
from pathlib import Path
from typing import List

from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

import httpx
from pint import UnitRegistry

app = FastAPI(title="Web Converter API", version="1.0.0")

# Монтируем статику и шаблоны
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

ureg = UnitRegistry()

# Главная страница — теперь с мульти-конвертером
@app.get("/", response_class=HTMLResponse)
async def image_page(request: Request):
    return templates.TemplateResponse("image_convert.html", {"request": request})

# НОВЫЙ эндпоинт: пакетная конвертация сразу нескольких изображений
@app.post("/api/v1/images/convert", summary="Batch convert images to ZIP")
async def convert_images_multi(
    files: List[UploadFile] = File(..., description="Выберите несколько файлов"),
    target_format: str = Form(..., description="Целевой формат"),
    quality: int = Form(80, description="Качество JPEG (1–100)")
):
    fmt = target_format.strip().lower()
    # список поддерживаемых форматов — расширяйте по желанию
    allowed = ("jpeg", "png", "webp", "tiff", "bmp")
    if fmt not in allowed:
        raise HTTPException(400, f"Неподдерживаемый формат: {fmt}")

    # Создаём ZIP в памяти
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for upload in files:
            data = await upload.read()
            try:
                img = Image.open(io.BytesIO(data))
            except Exception:
                # пропускаем некорректные файлы
                continue

            out_buffer = io.BytesIO()
            save_kwargs = {}
            # для JPEG укажем качество
            if fmt in ("jpeg", "jpg"):
                save_fmt = "JPEG"
                save_kwargs["quality"] = max(1, min(quality, 100))
            else:
                save_fmt = fmt.upper()

            img.save(out_buffer, save_fmt, **save_kwargs)
            out_buffer.seek(0)

            # имя внутри архива — исходное имя, но с новым расширением
            name = Path(upload.filename).stem + f".{fmt}"
            zipf.writestr(name, out_buffer.read())

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=converted_images_{fmt}.zip"
        }
    )

# Эндпоинт ресайза
@app.post("/api/v1/images/resize", summary="Изменение размера изображения")
async def resize_image(
    file: UploadFile = File(...),
    width: int = Form(..., gt=0),
    height: int = Form(..., gt=0)
):
    fmt = file.filename.rsplit(".", 1)[-1].lower()
    if fmt not in ("jpeg", "jpg", "png", "webp"):
        raise HTTPException(400, "Неподдерживаемый формат")

    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data))
    except:
        raise HTTPException(400, "Не удалось открыть изображение")

    resized = img.resize((width, height))
    buf = io.BytesIO()
    save_fmt = "JPEG" if fmt in ("jpeg","jpg") else fmt.upper()
    resized.save(buf, save_fmt)
    buf.seek(0)

    mime = f"image/{'jpeg' if save_fmt=='JPEG' else fmt}"
    return StreamingResponse(buf, media_type=mime, headers={
        "Content-Disposition": f"attachment; filename=resized.{fmt}"
    })

@app.get("/resize", response_class=HTMLResponse)
async def resize_page(request: Request):
    return templates.TemplateResponse("image_resize.html", {"request": request})

# DOCX → PDF
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
    width, height = A4
    y = height - 40
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            y -= 14
            continue
        if y < 40:
            c.showPage()
            y = height - 40
        c.drawString(40, y, text)
        y -= 14
    c.save()
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=converted.pdf"}
    )

# Конвертер величин
@app.get("/units", response_class=HTMLResponse)
async def units_page(request: Request):
    return templates.TemplateResponse("unit_convert.html", {"request": request})

@app.post("/api/v1/units/convert", summary="Конвертация величин")
async def convert_units(
    value: float = Form(...),
    from_unit: str = Form(...),
    to_unit: str = Form(...)
):
    try:
        q = value * ureg(from_unit)
        result = q.to(to_unit)
    except Exception as e:
        raise HTTPException(400, f"Ошибка конвертации: {e}")
    return {"input": f"{value} {from_unit}", "output": f"{result.magnitude} {result.units}"}

# Конвертер валют
@app.get("/currency", response_class=HTMLResponse)
async def currency_page(request: Request):
    return templates.TemplateResponse("currency_convert.html", {"request": request})

@app.post("/api/v1/currency/convert", summary="Конвертация валют")
async def convert_currency(
    value: float = Form(...),
    from_currency: str = Form(...),
    to_currency: str = Form(...)
):
    from_cur = from_currency.strip().upper()
    to_cur = to_currency.strip().upper()
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
