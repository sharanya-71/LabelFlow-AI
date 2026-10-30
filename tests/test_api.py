from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_compliance_screening():
    text = """
    Device name: DemoCare Sensor
    Manufacturer: Example Medical Devices Ltd.
    Lot number: LOT123
    Expiry date: 2030-12
    UDI: 12345678901234
    Warning: Read instructions for use (IFU).
    """
    response = client.post("/check-compliance", json={"text": text})
    assert response.status_code == 200
    assert response.json()["checks_total"] == 7


def test_empty_compliance_text():
    response = client.post("/check-compliance", json={"text": ""})
    assert response.status_code == 400


def test_label_draft_generation():
    payload = {
        "device_name": "DemoCare Monitoring Sensor",
        "manufacturer": "Example Medical Devices Ltd.",
        "model_number": "DC-100",
        "lot_number": "LOT-2026-0042",
        "expiry_date": "2030-12-31",
        "udi": "TEST-UDI-001",
        "warnings": "Do not use if damaged.",
        "instructions": "Read instructions before use.",
        "storage_conditions": "Store in a dry location."
    }
    response = client.post("/generate-label-draft", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "draft_generated"
    assert "DemoCare Monitoring Sensor" in response.json()["label_draft"]


def test_audit_history_endpoint():
    response = client.get("/audit-history?limit=100")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert isinstance(result["history"], list)


def test_invalid_draft_request():
    response = client.post(
        "/generate-label-draft",
        json={"device_name": "", "manufacturer": ""}
    )
    assert response.status_code == 400
