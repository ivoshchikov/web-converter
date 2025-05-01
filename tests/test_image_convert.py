import io
from fastapi.testclient import TestClient
from app.main import app
from PIL import Image

client = TestClient(app)

def make_test_image(format="PNG", size=(10,10), color=(255,0,0)):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format)
    buf.seek(0)
    return buf

def test_convert_png_to_jpeg():
    buf = make_test_image(format="PNG")
    files = {"file": ("test.png", buf, "image/png")}
    data = {"target_format": "jpeg"}
    r = client.post("/api/v1/images/convert", files=files, data=data)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/jpeg")
