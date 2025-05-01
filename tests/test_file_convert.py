import io
from fastapi.testclient import TestClient
from app.main import app
from docx import Document

client = TestClient(app)

def make_test_docx():
    doc = Document()
    doc.add_paragraph("Hello, Web Converter!")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def test_convert_docx_to_pdf():
    buf = make_test_docx()
    files = {"file": ("test.docx", buf, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    r = client.post("/api/v1/files/convert/docx-to-pdf", files=files)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    # Минимальная проверка: PDF начинается со строки %PDF
    assert r.content.startswith(b"%PDF")
