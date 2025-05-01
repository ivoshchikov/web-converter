import io
from fastapi.testclient import TestClient
from app.main import app
from PIL import Image

client = TestClient(app)

def make_test_image(format="PNG", size=(10,10), color=(0,255,0)):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format)
    buf.seek(0)
    return buf

def test_resize_image():
    buf = make_test_image(format="PNG", size=(10,10))
    files = {"file": ("test.png", buf, "image/png")}
    data = {"width": "5", "height": "5"}
    r = client.post("/api/v1/images/resize", files=files, data=data)
    assert r.status_code == 200
    # проверяем, что получили картинку и она уменьшилась
    img = Image.open(io.BytesIO(r.content))
    assert img.size == (5, 5)
