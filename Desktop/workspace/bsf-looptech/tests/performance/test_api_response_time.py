"""
Performance tests: verify all major API endpoints respond within 500ms.

Uses the same test infrastructure as integration tests:
- SQLite in-memory (aiosqlite)
- SKIP_AUTH=true
- RATE_LIMIT_PER_MINUTE=999999
"""

import time

import pytest
from httpx import AsyncClient, ASGITransport

from src.database.postgresql import Base, engine
from src.main import app

# Maximum acceptable response time in seconds
MAX_RESPONSE_TIME = 0.5


@pytest.fixture(scope="module", autouse=True)
async def init_test_db():
    """Create all tables before performance tests, drop after."""
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


async def _measure(client: AsyncClient, method: str, url: str, **kwargs) -> float:
    """Execute request and return elapsed time in seconds."""
    start = time.perf_counter()
    response = getattr(client, method)
    await response(url, **kwargs)
    return time.perf_counter() - start


@pytest.mark.performance
class TestHealthEndpointPerformance:
    """Health and readiness probes."""

    async def test_health_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/health")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /health took {elapsed:.3f}s"

    async def test_ready_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/ready")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /ready took {elapsed:.3f}s"

    async def test_root_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/")
        assert elapsed < MAX_RESPONSE_TIME, f"GET / took {elapsed:.3f}s"


@pytest.mark.performance
class TestWasteApiPerformance:
    """Waste record and recommendation endpoints."""

    async def test_get_records_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/api/waste/records")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /api/waste/records took {elapsed:.3f}s"

    async def test_recommend_under_500ms(self, client, sample_waste_analysis):
        payload = {"analysis": sample_waste_analysis, "wasteType": "汚泥（一般）"}
        elapsed = await _measure(client, "post", "/api/waste/recommend", json=payload)
        assert elapsed < MAX_RESPONSE_TIME, f"POST /api/waste/recommend took {elapsed:.3f}s"


@pytest.mark.performance
class TestMaterialsApiPerformance:
    """Materials CRUD endpoints."""

    async def test_get_suppliers_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/api/v1/suppliers")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /api/v1/suppliers took {elapsed:.3f}s"

    async def test_get_solidification_materials_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/api/v1/solidification-materials")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /api/v1/solidification-materials took {elapsed:.3f}s"

    async def test_get_leaching_suppressants_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/api/v1/leaching-suppressants")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /api/v1/leaching-suppressants took {elapsed:.3f}s"

    async def test_get_recipes_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/api/v1/recipes")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /api/v1/recipes took {elapsed:.3f}s"


@pytest.mark.performance
class TestMLApiPerformance:
    """ML prediction and model management endpoints."""

    async def test_predict_formulation_under_500ms(self, client, sample_waste_analysis):
        payload = {
            "waste_type": "汚泥（一般）",
            "ph": sample_waste_analysis["pH"],
            "moisture": sample_waste_analysis["moisture"],
            "heavy_metals": {
                "Pb": sample_waste_analysis["Pb"],
                "As": sample_waste_analysis["As"],
                "Cd": sample_waste_analysis["Cd"],
            },
        }
        elapsed = await _measure(client, "post", "/api/v1/predict/formulation", json=payload)
        assert elapsed < MAX_RESPONSE_TIME, f"POST /api/v1/predict/formulation took {elapsed:.3f}s"

    async def test_predict_elution_under_500ms(self, client, sample_waste_analysis):
        payload = {
            "waste_type": "汚泥（一般）",
            "ph": sample_waste_analysis["pH"],
            "solidifier_type": "普通ポルトランドセメント",
            "solidifier_amount": 150,
            "heavy_metals": {
                "Pb": sample_waste_analysis["Pb"],
                "As": sample_waste_analysis["As"],
            },
        }
        elapsed = await _measure(client, "post", "/api/v1/predict/elution", json=payload)
        assert elapsed < MAX_RESPONSE_TIME, f"POST /api/v1/predict/elution took {elapsed:.3f}s"

    async def test_get_models_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/api/v1/ml/models")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /api/v1/ml/models took {elapsed:.3f}s"

    async def test_get_accuracy_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/api/v1/ml/accuracy")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /api/v1/ml/accuracy took {elapsed:.3f}s"


@pytest.mark.performance
class TestOptimizationApiPerformance:
    """Optimization endpoint."""

    async def test_optimize_under_500ms(self, client, sample_waste_analysis):
        payload = {
            "waste_type": "汚泥（一般）",
            "ph": sample_waste_analysis["pH"],
            "moisture": sample_waste_analysis["moisture"],
            "heavy_metals": {
                "Pb": sample_waste_analysis["Pb"],
                "As": sample_waste_analysis["As"],
            },
        }
        elapsed = await _measure(client, "post", "/api/v1/optimization/optimize", json=payload)
        assert elapsed < MAX_RESPONSE_TIME, f"POST /api/v1/optimization/optimize took {elapsed:.3f}s"


@pytest.mark.performance
class TestBatchApiPerformance:
    """Batch job management endpoints."""

    async def test_get_jobs_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/api/v1/batch/jobs")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /api/v1/batch/jobs took {elapsed:.3f}s"

    async def test_get_status_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/api/v1/batch/status")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /api/v1/batch/status took {elapsed:.3f}s"


@pytest.mark.performance
class TestKPIApiPerformance:
    """KPI dashboard endpoints."""

    async def test_kpi_realtime_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/api/v1/kpi/realtime")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /api/v1/kpi/realtime took {elapsed:.3f}s"

    async def test_kpi_trends_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/api/v1/kpi/trends")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /api/v1/kpi/trends took {elapsed:.3f}s"

    async def test_kpi_alerts_under_500ms(self, client):
        elapsed = await _measure(client, "get", "/api/v1/kpi/alerts")
        assert elapsed < MAX_RESPONSE_TIME, f"GET /api/v1/kpi/alerts took {elapsed:.3f}s"


@pytest.mark.performance
class TestChatApiPerformance:
    """Chat / RAG endpoints."""

    async def test_create_session_under_500ms(self, client):
        payload = {"title": "パフォーマンステストセッション"}
        elapsed = await _measure(client, "post", "/api/v1/chat/sessions", json=payload)
        assert elapsed < MAX_RESPONSE_TIME, f"POST /api/v1/chat/sessions took {elapsed:.3f}s"
