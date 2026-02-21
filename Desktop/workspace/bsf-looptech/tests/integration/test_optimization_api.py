"""Integration tests for PuLP optimization API endpoints."""

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


@pytest.mark.integration
class TestOptimizeFormulation:
    async def test_optimize_clean_waste(self, client):
        """Clean waste should return optimal solution."""
        payload = {
            "analysis": {
                "pH": 7.2, "moisture": 55.0,
                "Pb": 0.005, "As": 0.003, "Cd": 0.001,
            },
            "waste_type": "汚泥（一般）",
            "waste_weight": 1.0,
        }
        response = await client.post("/api/v1/optimize/formulation", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "optimal"
        assert data["total_cost"] > 0
        assert "solidifierType" in data["recommendation"]

    async def test_optimize_heavy_waste(self, client):
        """Heavy waste returns a valid response (optimal or infeasible)."""
        payload = {
            "analysis": {
                "pH": 11.5, "moisture": 25.0,
                "Pb": 0.06, "Cr6": 0.08, "As": 0.015,
            },
            "waste_type": "焼却灰",
            "waste_weight": 1.0,
        }
        response = await client.post("/api/v1/optimize/formulation", json=payload)
        assert response.status_code == 200
        data = response.json()
        # May be infeasible with default materials if severity is too high
        assert data["status"] in ("optimal", "infeasible")
        assert data["solver_time_ms"] >= 0
        if data["status"] == "optimal":
            assert len(data["cost_breakdown"]) >= 1

    async def test_optimize_with_budget(self, client):
        """Budget constraint should be respected."""
        payload = {
            "analysis": {"pH": 7.0, "moisture": 55.0, "Pb": 0.005},
            "waste_type": "汚泥（一般）",
            "waste_weight": 1.0,
            "max_budget": 5000.0,
        }
        response = await client.post("/api/v1/optimize/formulation", json=payload)
        assert response.status_code == 200
        data = response.json()
        if data["status"] == "optimal":
            assert data["total_cost"] <= 5000.0

    async def test_optimize_impossible_budget(self, client):
        """Impossibly low budget should return infeasible."""
        payload = {
            "analysis": {"pH": 7.0, "moisture": 55.0, "Pb": 0.005},
            "waste_type": "汚泥（一般）",
            "waste_weight": 1.0,
            "max_budget": 1.0,
        }
        response = await client.post("/api/v1/optimize/formulation", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "infeasible"

    async def test_optimize_empty_analysis(self, client):
        """Empty analysis should still return a result."""
        payload = {
            "analysis": {},
            "waste_type": "汚泥（一般）",
            "waste_weight": 1.0,
        }
        response = await client.post("/api/v1/optimize/formulation", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("optimal", "infeasible", "error")

    async def test_optimize_response_has_reasoning(self, client):
        """Response should include human-readable reasoning."""
        payload = {
            "analysis": {"pH": 7.0, "moisture": 60.0, "Pb": 0.005},
            "waste_type": "汚泥（一般）",
            "waste_weight": 1.0,
        }
        response = await client.post("/api/v1/optimize/formulation", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data["reasoning"]) > 0

    async def test_optimize_constraints_info(self, client):
        """Response should report constraint details."""
        payload = {
            "analysis": {"pH": 7.0, "moisture": 55.0},
            "waste_type": "汚泥（一般）",
            "waste_weight": 1.0,
        }
        response = await client.post("/api/v1/optimize/formulation", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "constraints_satisfied" in data
