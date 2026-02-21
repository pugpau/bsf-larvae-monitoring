"""Integration tests for Knowledge CSV import endpoint (Phase 2-6)."""

import io
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.postgresql import Base, engine
from src.main import app


@pytest.fixture(scope="module", autouse=True)
async def init_test_db():
    """Create all tables before tests, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


def _make_csv(rows: list[list[str]], with_bom: bool = False) -> bytes:
    """Build CSV bytes from rows (first row is header)."""
    lines = [",".join(row) for row in rows]
    content = "\n".join(lines)
    if with_bom:
        content = "\ufeff" + content
    return content.encode("utf-8")


@pytest.mark.integration
class TestKnowledgeCSVImport:
    """POST /api/v1/knowledge/import-csv"""

    @pytest.mark.asyncio
    @patch("src.api.routes.chat.get_embedding", new_callable=AsyncMock, return_value=None)
    async def test_import_valid_csv(self, mock_embed, client):
        """Import 2 valid rows from CSV."""
        csv_data = _make_csv([
            ["title", "content", "source_type"],
            ["BSF温度管理", "最適温度は27-30度です。", "csv"],
            ["基材配合", "C/N比15-25が最適です。", "csv"],
        ])
        resp = await client.post(
            "/api/v1/knowledge/import-csv",
            files={"file": ("knowledge.csv", csv_data, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 2
        assert data["skipped"] == 0
        assert data["errors"] == []

    @pytest.mark.asyncio
    @patch("src.api.routes.chat.get_embedding", new_callable=AsyncMock, return_value=None)
    async def test_import_with_bom(self, mock_embed, client):
        """BOM-prefixed CSV should work (Excel export format)."""
        csv_data = _make_csv([
            ["title", "content", "source_type"],
            ["テスト項目", "テスト内容です。", "manual"],
        ], with_bom=True)
        resp = await client.post(
            "/api/v1/knowledge/import-csv",
            files={"file": ("test.csv", csv_data, "text/csv")},
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 1

    @pytest.mark.asyncio
    @patch("src.api.routes.chat.get_embedding", new_callable=AsyncMock, return_value=None)
    async def test_import_empty_rows_skipped(self, mock_embed, client):
        """Rows with empty title or content should be skipped."""
        csv_data = _make_csv([
            ["title", "content", "source_type"],
            ["", "content without title", "csv"],
            ["title without content", "", "csv"],
            ["Valid Title", "Valid Content", "csv"],
        ])
        resp = await client.post(
            "/api/v1/knowledge/import-csv",
            files={"file": ("test.csv", csv_data, "text/csv")},
        )
        data = resp.json()
        assert data["imported"] == 1
        assert data["skipped"] == 2
        assert len(data["errors"]) == 2

    @pytest.mark.asyncio
    @patch("src.api.routes.chat.get_embedding", new_callable=AsyncMock, return_value=None)
    async def test_import_default_source_type(self, mock_embed, client):
        """Missing source_type should default to 'csv'."""
        csv_data = _make_csv([
            ["title", "content", "source_type"],
            ["タイトル", "コンテンツ", ""],
        ])
        resp = await client.post(
            "/api/v1/knowledge/import-csv",
            files={"file": ("test.csv", csv_data, "text/csv")},
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 1

    @pytest.mark.asyncio
    async def test_import_empty_file(self, client):
        """Empty CSV file (header only) should import 0."""
        csv_data = _make_csv([["title", "content", "source_type"]])
        resp = await client.post(
            "/api/v1/knowledge/import-csv",
            files={"file": ("empty.csv", csv_data, "text/csv")},
        )
        data = resp.json()
        assert data["imported"] == 0
        assert data["skipped"] == 0
