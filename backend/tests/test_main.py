from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "Welcome to the BSF Larvae Monitoring System API"

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
