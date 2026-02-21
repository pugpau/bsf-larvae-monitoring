"""Integration tests for recipe version management API endpoints."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.database.postgresql import Base


@pytest.fixture
async def api_session():
    """Fresh DB + session for integration tests."""
    from src.auth.models import User  # noqa: F401 — FK target for activity_logs

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
#  Helpers
# ══════════════════════════════════════

async def _create_recipe(client: AsyncClient, **overrides) -> dict:
    payload = {
        "name": "テストレシピ",
        "waste_type": "汚泥",
        "status": "draft",
        "details": [
            {
                "material_id": str(uuid.uuid4()),
                "material_type": "solidification",
                "addition_rate": 150.0,
                "order_index": 0,
            },
        ],
        **overrides,
    }
    r = await client.post("/api/v1/recipes", json=payload)
    assert r.status_code == 201
    return r.json()


async def _update_recipe(client: AsyncClient, recipe_id: str, data: dict) -> dict:
    r = await client.put(f"/api/v1/recipes/{recipe_id}", json=data)
    assert r.status_code == 200
    return r.json()


# ══════════════════════════════════════
#  Version List
# ══════════════════════════════════════

class TestVersionList:
    @pytest.mark.asyncio
    async def test_empty_version_list(self, client):
        """New recipe should have no versions."""
        recipe = await _create_recipe(client)
        r = await client.get(f"/api/v1/recipes/{recipe['id']}/versions")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_version_created_on_update(self, client):
        """Updating a recipe should create version history."""
        recipe = await _create_recipe(client)
        await _update_recipe(client, recipe["id"], {"name": "更新後"})

        r = await client.get(f"/api/v1/recipes/{recipe['id']}/versions")
        assert r.status_code == 200
        versions = r.json()
        assert len(versions) == 1
        assert versions[0]["version"] == 1

    @pytest.mark.asyncio
    async def test_version_list_not_found(self, client):
        """Should return 404 for non-existent recipe."""
        r = await client.get(
            f"/api/v1/recipes/00000000-0000-0000-0000-000000000000/versions"
        )
        assert r.status_code == 404


# ══════════════════════════════════════
#  Get Version Detail
# ══════════════════════════════════════

class TestGetVersion:
    @pytest.mark.asyncio
    async def test_get_version_detail(self, client):
        """Should return full version snapshot with details."""
        recipe = await _create_recipe(client)
        await _update_recipe(client, recipe["id"], {"name": "v2"})

        r = await client.get(f"/api/v1/recipes/{recipe['id']}/versions/1")
        assert r.status_code == 200
        body = r.json()
        assert body["version"] == 1
        assert body["name"] == "テストレシピ"
        assert "details" in body
        assert len(body["details"]) >= 1

    @pytest.mark.asyncio
    async def test_get_version_not_found(self, client):
        """Should return 404 for non-existent version."""
        recipe = await _create_recipe(client)
        r = await client.get(f"/api/v1/recipes/{recipe['id']}/versions/999")
        assert r.status_code == 404


# ══════════════════════════════════════
#  Rollback
# ══════════════════════════════════════

class TestRollback:
    @pytest.mark.asyncio
    async def test_rollback_via_api(self, client):
        """POST rollback should restore recipe to target version."""
        recipe = await _create_recipe(client)
        await _update_recipe(client, recipe["id"], {"name": "v2名"})
        await _update_recipe(client, recipe["id"], {"name": "v3名"})

        r = await client.post(
            f"/api/v1/recipes/{recipe['id']}/versions/1/rollback"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "テストレシピ"
        assert body["current_version"] == 4

    @pytest.mark.asyncio
    async def test_rollback_not_found(self, client):
        """Rollback to non-existent version should return 404."""
        recipe = await _create_recipe(client)
        r = await client.post(
            f"/api/v1/recipes/{recipe['id']}/versions/999/rollback"
        )
        assert r.status_code == 404


# ══════════════════════════════════════
#  Diff
# ══════════════════════════════════════

# ══════════════════════════════════════
#  Detail-Level Versioning
# ══════════════════════════════════════

class TestDetailVersioning:
    @pytest.mark.asyncio
    async def test_add_detail_creates_version(self, client):
        """POST detail should create a version snapshot."""
        recipe = await _create_recipe(client)
        r = await client.post(
            f"/api/v1/recipes/{recipe['id']}/details",
            json={
                "material_id": str(uuid.uuid4()),
                "material_type": "suppressant",
                "addition_rate": 5.0,
                "order_index": 1,
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert body["current_version"] == 2

        # Check version history
        r2 = await client.get(f"/api/v1/recipes/{recipe['id']}/versions")
        assert r2.status_code == 200
        versions = r2.json()
        assert len(versions) == 1
        assert versions[0]["version"] == 1

    @pytest.mark.asyncio
    async def test_remove_detail_creates_version(self, client):
        """DELETE detail should create a version snapshot."""
        recipe = await _create_recipe(client)
        detail_id = recipe["details"][0]["id"]
        r = await client.delete(
            f"/api/v1/recipes/{recipe['id']}/details/{detail_id}"
        )
        assert r.status_code == 200

        r2 = await client.get(f"/api/v1/recipes/{recipe['id']}/versions")
        versions = r2.json()
        assert len(versions) == 1
        assert versions[0]["change_summary"] == "明細削除"


# ══════════════════════════════════════
#  Diff with Current
# ══════════════════════════════════════

class TestDiffWithCurrent:
    @pytest.mark.asyncio
    async def test_diff_with_current_endpoint(self, client):
        """GET diff/current should compare version with live recipe."""
        recipe = await _create_recipe(client)
        await _update_recipe(client, recipe["id"], {"name": "v2名"})
        await _update_recipe(client, recipe["id"], {"name": "v3名"})

        r = await client.get(
            f"/api/v1/recipes/{recipe['id']}/versions/1/diff/current"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["version_from"] == 1
        assert body["version_to"] == 3
        changed_fields = {c["field"] for c in body["header_changes"]}
        assert "name" in changed_fields

    @pytest.mark.asyncio
    async def test_diff_with_current_not_found(self, client):
        """diff/current with non-existent version should return 404."""
        recipe = await _create_recipe(client)
        r = await client.get(
            f"/api/v1/recipes/{recipe['id']}/versions/999/diff/current"
        )
        assert r.status_code == 404


# ══════════════════════════════════════
#  Diff (between stored versions)
# ══════════════════════════════════════

class TestDiff:
    @pytest.mark.asyncio
    async def test_diff_between_versions(self, client):
        """Diff should return header_changes between two versions."""
        recipe = await _create_recipe(client)
        await _update_recipe(client, recipe["id"], {
            "name": "v2名",
            "status": "active",
        })
        await _update_recipe(client, recipe["id"], {"name": "v3名"})

        r = await client.get(
            f"/api/v1/recipes/{recipe['id']}/versions/1/diff/2"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["version_from"] == 1
        assert body["version_to"] == 2
        changed_fields = {c["field"] for c in body["header_changes"]}
        assert "name" in changed_fields

    @pytest.mark.asyncio
    async def test_diff_not_found(self, client):
        """Diff with non-existent version should return 404."""
        recipe = await _create_recipe(client)
        r = await client.get(
            f"/api/v1/recipes/{recipe['id']}/versions/1/diff/999"
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_diff_same_version_rejected(self, client):
        """Diff v1 vs v1 should return 400 (same version)."""
        recipe = await _create_recipe(client)
        await _update_recipe(client, recipe["id"], {"name": "v2名"})

        r = await client.get(
            f"/api/v1/recipes/{recipe['id']}/versions/1/diff/1"
        )
        assert r.status_code == 400


# ══════════════════════════════════════
#  Security: UUID Validation
# ══════════════════════════════════════

class TestUUIDValidation:
    """Malformed UUIDs should return 422 from FastAPI path validation."""

    @pytest.mark.asyncio
    async def test_get_recipe_malformed_uuid(self, client):
        r = await client.get("/api/v1/recipes/not-a-uuid")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_update_recipe_malformed_uuid(self, client):
        r = await client.put(
            "/api/v1/recipes/not-a-uuid",
            json={"name": "test"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_recipe_malformed_uuid(self, client):
        r = await client.delete("/api/v1/recipes/not-a-uuid")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_versions_malformed_uuid(self, client):
        r = await client.get("/api/v1/recipes/not-a-uuid/versions")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_rollback_malformed_uuid(self, client):
        r = await client.post("/api/v1/recipes/not-a-uuid/versions/1/rollback")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_add_detail_malformed_uuid(self, client):
        r = await client.post(
            "/api/v1/recipes/not-a-uuid/details",
            json={
                "material_id": str(uuid.uuid4()),
                "material_type": "solidification",
                "addition_rate": 10.0,
            },
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_remove_detail_malformed_uuid(self, client):
        r = await client.delete("/api/v1/recipes/not-a-uuid/details/also-bad")
        assert r.status_code == 422


# ══════════════════════════════════════
#  Security: Status Enum Validation
# ══════════════════════════════════════

class TestStatusValidation:
    """Invalid status values should be rejected by Pydantic."""

    @pytest.mark.asyncio
    async def test_create_invalid_status(self, client):
        payload = {
            "name": "テスト",
            "waste_type": "汚泥",
            "status": "INVALID_STATUS",
        }
        r = await client.post("/api/v1/recipes", json=payload)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_update_invalid_status(self, client):
        recipe = await _create_recipe(client)
        r = await client.put(
            f"/api/v1/recipes/{recipe['id']}",
            json={"status": "INVALID_STATUS"},
        )
        assert r.status_code == 422


# ══════════════════════════════════════
#  Security: Cross-Recipe Detail Deletion
# ══════════════════════════════════════

class TestCrossRecipeDeletion:
    @pytest.mark.asyncio
    async def test_delete_detail_from_wrong_recipe(self, client):
        """Deleting a detail using another recipe's ID should fail."""
        recipe_a = await _create_recipe(client, name="Recipe A")
        recipe_b = await _create_recipe(client, name="Recipe B")
        detail_a_id = recipe_a["details"][0]["id"]

        r = await client.delete(
            f"/api/v1/recipes/{recipe_b['id']}/details/{detail_a_id}"
        )
        assert r.status_code == 404
