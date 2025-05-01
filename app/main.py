from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
import io
from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import httpx
from fastapi import Form, HTTPException

app = FastAPI(title="Web Converter API", version="1.0.0")

# Монтируем статику и шаблоны
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Страница конвертера
@app.get("/", response_class=HTMLResponse)
async def image_page(request: Request):
    return templates.TemplateResponse("image_convert.html", {"request": request})

# Эндпоинт конвертации (как раньше)
@app.post("/api/v1/images/convert")
async def convert_image(
    file: UploadFile = File(...),
    target_format: str = Form(...)
):
    fmt = target_format.strip().lower()
    if fmt not in ("jpeg", "png", "webp"):
        raise HTTPException(400, "Неподдерживаемый формат")
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents))
    except:
        raise HTTPException(400, "Не удалось открыть изображение")
    buf = io.BytesIO()
    img.save(buf, fmt.upper())
    buf.seek(0)
    mime = f"image/{'jpeg' if fmt=='jpeg' else fmt}"
    return StreamingResponse(buf, media_type=mime, headers={
        "Content-Disposition": f"attachment; filename=converted.{fmt}"
    })

@app.post("/api/v1/images/resize", summary="Изменение размера изображения")
async def resize_image(
    file: UploadFile = File(...),
    width: int = Form(..., gt=0),
    height: int = Form(..., gt=0)
):
    # Определим формат по расширению исходного файла
    fmt = (file.filename.rsplit(".", 1)[-1]).lower()
    if fmt not in ("jpeg", "jpg", "png", "webp"):
        raise HTTPException(400, "Неподдерживаемый формат")

    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data))
    except:
        raise HTTPException(400, "Не удалось открыть изображение")

    # Изменяем размер
    resized = img.resize((width, height))

    buf = io.BytesIO()
    # Для JPEG используем формат JPEG
    save_fmt = "JPEG" if fmt in ("jpeg", "jpg") else fmt.upper()
    resized.save(buf, save_fmt)
    buf.seek(0)

    mime = f"image/{'jpeg' if save_fmt=='JPEG' else fmt}"
    return StreamingResponse(buf, media_type=mime, headers={
        "Content-Disposition": f"attachment; filename=resized.{fmt}"
    })

@app.get("/resize", response_class=HTMLResponse)
async def resize_page(request: Request):
    return templates.TemplateResponse("image_resize.html", {"request": request})

@app.get("/file", response_class=HTMLResponse)
async def file_page(request: Request):
    return templates.TemplateResponse("file_convert.html", {"request": request})

@app.post("/api/v1/files/convert/docx-to-pdf", summary="Конвертация DOCX → PDF")
async def convert_docx_to_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "Загрузите файл .docx")

    data = await file.read()
    # Читаем DOCX из памяти
    try:
        doc = Document(io.BytesIO(data))
    except Exception:
        raise HTTPException(400, "Не удалось прочитать DOCX")

    # Генерируем PDF в буфер
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 40  # отступ сверху

    # Записываем параграфы
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            y -= 14
            continue
        # Если строка не помещается, новая страница
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

@app.get("/file", response_class=HTMLResponse)
async def file_page(request: Request):
    return templates.TemplateResponse("file_convert.html", {"request": request})

from pint import UnitRegistry

ureg = UnitRegistry()

@app.get("/units", response_class=HTMLResponse)
async def units_page(request: Request):
    return templates.TemplateResponse("unit_convert.html", {"request": request})

@app.post("/api/v1/units/convert", summary="Конвертация величин")
async def convert_units(
    value: float = Form(..., description="Численное значение"),
    from_unit: str = Form(..., description="Исходная единица (например, km)"),
    to_unit: str = Form(..., description="Целевая единица (например, m)")
):
    try:
        q = value * ureg(from_unit)
        result = q.to(to_unit)
    except Exception as e:
        raise HTTPException(400, f"Ошибка конвертации: {e}")
    return {"input": f"{value} {from_unit}", "output": f"{result.magnitude} {result.units}"}

@app.get("/currency", response_class=HTMLResponse)
async def currency_page(request: Request):
    return templates.TemplateResponse("currency_convert.html", {"request": request})

@app.post("/api/v1/currency/convert", summary="Конвертация валют")
async def convert_currency(
    value: float = Form(..., description="Сумма"),
    from_currency: str = Form(..., description="Исходная валюта, например USD"),
    to_currency: str = Form(..., description="Целевая валюта, например EUR")
):
    from_cur = from_currency.strip().upper()
    to_cur = to_currency.strip().upper()
    # Новый URL — получаем все курсы от from_cur
    url = f"https://open.er-api.com/v6/latest/{from_cur}"

    # Запрашиваем
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(502, "Сервис курсов недоступен")

    if resp.status_code != 200:
        raise HTTPException(502, "Сервис курсов вернул ошибку")

    data = resp.json()
    # Проверяем, что получили валидный ответ
    if data.get("result") != "success" or "rates" not in data:
        raise HTTPException(502, f"Ошибка данных от сервиса: {data.get('error-type','unknown')}")

    rates = data["rates"]
    if to_cur not in rates:
        raise HTTPException(400, f"Неверная целевая валюта: {to_cur}")

    rate = rates[to_cur]
    converted = value * rate

    return {
        "input": f"{value} {from_cur}",
        "output": f"{converted:.4f} {to_cur}"
    }