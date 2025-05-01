from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_convert_usd_to_eur():
    data = {"value": "1", "from_currency": "USD", "to_currency": "EUR"}
    r = client.post("/api/v1/currency/convert", data=data)
    assert r.status_code == 200
    json = r.json()
    assert json["input"] == "1.0 USD"
    # Результат может меняться — просто проверим формат:
    parts = json["output"].split()
    assert len(parts) == 2
    assert parts[1] == "EUR"
    float(parts[0])  # должно конвертироваться в число без ошибки
