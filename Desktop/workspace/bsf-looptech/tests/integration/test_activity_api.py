"""Integration tests for activity API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.postgresql import Base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


@pytest.fixture
async def api_session():
    """Fresh DB + session for integration tests."""
    # Ensure auth models (User table) are registered before create_all
    from src.auth.models import User  # noqa: F401

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session, engine
        await session.rollback()
    await engine.dispose()


@pytest.fixture
async def client(api_session):
    """HTTPX async client hitting the FastAPI app."""
    session, engine = api_session
    from src.main import app
    from src.database.postgresql import get_async_session

    async def override():
        yield session

    app.dependency_overrides[get_async_session] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ══════════════════════════════════════
#  Activity Feed API
# ══════════════════════════════════════


@pytest.mark.asyncio
class TestActivityFeedAPI:
    """Tests for GET /api/v1/activity/feed."""

    async def test_empty_feed(self, client):
        r = await client.get("/api/v1/activity/feed")
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_feed_with_limit(self, client):
        r = await client.get("/api/v1/activity/feed?limit=10&offset=0")
        assert r.status_code == 200
        data = r.json()
        assert data["limit"] == 10
        assert data["offset"] == 0

    async def test_feed_filter_by_event_type(self, client):
        r = await client.get("/api/v1/activity/feed?event_type=FORMULATION_ACCEPT")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0

    async def test_feed_filter_by_entity_type(self, client):
        r = await client.get("/api/v1/activity/feed?entity_type=formulation")
        assert r.status_code == 200

    async def test_feed_filter_by_severity(self, client):
        r = await client.get("/api/v1/activity/feed?severity=warning")
        assert r.status_code == 200

    async def test_feed_invalid_severity(self, client):
        r = await client.get("/api/v1/activity/feed?severity=invalid")
        assert r.status_code == 422

    async def test_feed_limit_bounds(self, client):
        r = await client.get("/api/v1/activity/feed?limit=0")
        assert r.status_code == 422

        r = await client.get("/api/v1/activity/feed?limit=300")
        assert r.status_code == 422


@pytest.mark.asyncio
class TestEntityActivityAPI:
    """Tests for GET /api/v1/activity/{entity_type}/{entity_id}."""

    async def test_entity_activity_empty(self, client):
        r = await client.get("/api/v1/activity/formulation/nonexistent-id")
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_entity_activity_with_limit(self, client):
        r = await client.get("/api/v1/activity/delivery/some-id?limit=5")
        assert r.status_code == 200


@pytest.mark.asyncio
class TestActivityIntegrationWithService:
    """Tests that activity events get created via the service layer."""

    async def test_create_and_retrieve_activity(self, api_session):
        """Create an activity via service, then query via repository."""
        session, _ = api_session
        from src.activity.service import ActivityService

        svc = ActivityService(session)

        # Create an activity
        entry = await svc.log_event(
            event_type="FORMULATION_ACCEPT",
            entity_type="formulation",
            entity_id="test-form-id",
            action="accept",
            title="テスト配合承認",
            severity="info",
            metadata={"source_type": "ml"},
        )
        assert entry["event_type"] == "FORMULATION_ACCEPT"
        assert entry["entity_id"] == "test-form-id"

        # Retrieve via feed
        feed = await svc.get_feed(limit=10)
        assert feed["total"] == 1
        assert feed["items"][0]["title"] == "テスト配合承認"

    async def test_create_multiple_and_filter(self, api_session):
        session, _ = api_session
        from src.activity.service import ActivityService

        svc = ActivityService(session)

        await svc.log_formulation_event(
            action="accept", formulation_id="f1", title="Accept 1",
        )
        await svc.log_formulation_event(
            action="reject", formulation_id="f2", title="Reject 1", severity="warning",
        )
        await svc.log_delivery_event(
            action="delivered", schedule_id="d1", title="Delivered 1",
        )

        # All
        feed = await svc.get_feed()
        assert feed["total"] == 3

        # Filter by entity_type
        feed = await svc.get_feed(entity_type="formulation")
        assert feed["total"] == 2

        feed = await svc.get_feed(entity_type="delivery")
        assert feed["total"] == 1

        # Filter by severity
        feed = await svc.get_feed(severity="warning")
        assert feed["total"] == 1

    async def test_entity_activity_retrieval(self, api_session):
        session, _ = api_session
        from src.activity.service import ActivityService

        svc = ActivityService(session)

        await svc.log_formulation_event(
            action="recommend", formulation_id="target-id", title="Recommend",
        )
        await svc.log_formulation_event(
            action="accept", formulation_id="target-id", title="Accept",
        )
        await svc.log_formulation_event(
            action="accept", formulation_id="other-id", title="Accept other",
        )

        items = await svc.get_entity_activity("formulation", "target-id")
        assert len(items) == 2
        assert all(i["entity_id"] == "target-id" for i in items)
