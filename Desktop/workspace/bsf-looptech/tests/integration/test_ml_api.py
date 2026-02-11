"""Integration tests for ML prediction and model management API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from src.database.postgresql import Base, engine
from src.main import app


@pytest.fixture(scope="module", autouse=True)
async def init_test_db():
    """Create all tables before integration tests, drop after."""
    from src.auth.models import User, UserSession, LoginAttempt, APIKey

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Async test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Prediction Endpoints ──


@pytest.mark.integration
class TestFormulationPrediction:
    async def test_predict_formulation_returns_200(self, client):
        payload = {
            "analysis": {
                "pH": 7.2, "moisture": 78.5, "Pb": 0.008,
                "As": 0.002, "Cd": 0.001,
            },
            "waste_type": "汚泥（一般）",
        }
        response = await client.post("/api/v1/predict/formulation", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "recommendation" in data
        assert "confidence" in data
        assert "method" in data
        assert data["method"] in ("ml", "similarity", "rule")

    async def test_predict_formulation_heavy_metals(self, client):
        payload = {
            "analysis": {
                "pH": 11.5, "moisture": 25.0,
                "Pb": 0.06, "Cr6": 0.08, "As": 0.015,
            },
            "waste_type": "焼却灰",
        }
        response = await client.post("/api/v1/predict/formulation", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation"]["solidifierAmount"] > 0

    async def test_predict_formulation_with_record_id(self, client):
        payload = {
            "analysis": {"pH": 7.0, "moisture": 60.0},
            "waste_type": "汚泥（一般）",
            "waste_record_id": "550e8400-e29b-41d4-a716-446655440000",
        }
        response = await client.post("/api/v1/predict/formulation", json=payload)
        assert response.status_code == 200


@pytest.mark.integration
class TestElutionPrediction:
    async def test_predict_elution_clean(self, client):
        payload = {
            "analysis": {"pH": 7.0, "Pb": 0.005, "As": 0.003},
            "formulation": {"solidifierAmount": 200},
        }
        response = await client.post("/api/v1/predict/elution", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "passed" in data
        assert "confidence" in data
        assert "metal_predictions" in data

    async def test_predict_elution_heavy(self, client):
        payload = {
            "analysis": {"Pb": 0.06, "Cr6": 0.15, "Cd": 0.005},
            "formulation": {"solidifierAmount": 50},
        }
        response = await client.post("/api/v1/predict/elution", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["passed"], bool)


# ── Model Management Endpoints ──


@pytest.mark.integration
class TestModelManagement:
    async def test_list_models_empty(self, client):
        response = await client.get("/api/v1/ml/models")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_list_models_with_type_filter(self, client):
        response = await client.get("/api/v1/ml/models?model_type=classifier")
        assert response.status_code == 200

    async def test_activate_nonexistent_model(self, client):
        response = await client.put(
            "/api/v1/ml/models/550e8400-e29b-41d4-a716-446655440000/activate"
        )
        assert response.status_code == 404


# ── Analytics Endpoints ──


@pytest.mark.integration
class TestMLAnalytics:
    async def test_accuracy_returns_200(self, client):
        response = await client.get("/api/v1/ml/accuracy")
        assert response.status_code == 200

    async def test_accuracy_custom_days(self, client):
        response = await client.get("/api/v1/ml/accuracy?days=7")
        assert response.status_code == 200

    async def test_trends_returns_200(self, client):
        response = await client.get("/api/v1/ml/trends")
        assert response.status_code == 200

    async def test_trends_custom_months(self, client):
        response = await client.get("/api/v1/ml/trends?months=3")
        assert response.status_code == 200
