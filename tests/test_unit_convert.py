from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_convert_km_to_m():
    data = {"value": "1", "from_unit": "km", "to_unit": "m"}
    r = client.post("/api/v1/units/convert", data=data)
    assert r.status_code == 200
    json = r.json()
    assert json["input"] == "1.0 km"
    assert json["output"].startswith("1000.0")
    assert "meter" in json["output"]
