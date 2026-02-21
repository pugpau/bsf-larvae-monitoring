"""Unit tests for activity logging service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.activity.service import ActivityService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def activity_service(mock_session):
    return ActivityService(mock_session)


class TestActivityServiceLogEvent:
    """Tests for ActivityService.log_event()."""

    @pytest.mark.asyncio
    async def test_log_event_creates_entry(self, activity_service, mock_session):
        result = await activity_service.log_event(
            event_type="FORMULATION_ACCEPT",
            entity_type="formulation",
            entity_id="abc-123",
            action="accept",
            title="配合案を承認",
        )
        assert result["event_type"] == "FORMULATION_ACCEPT"
        assert result["entity_type"] == "formulation"
        assert result["action"] == "accept"
        assert result["title"] == "配合案を承認"
        assert result["severity"] == "info"
        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_log_event_with_metadata(self, activity_service, mock_session):
        result = await activity_service.log_event(
            event_type="DELIVERY_DELIVERED",
            entity_type="delivery",
            entity_id="def-456",
            action="delivered",
            title="搬入完了",
            metadata={"actual_weight": 150.0},
        )
        assert result["metadata_json"] == {"actual_weight": 150.0}

    @pytest.mark.asyncio
    async def test_log_event_with_severity(self, activity_service, mock_session):
        result = await activity_service.log_event(
            event_type="FORMULATION_REJECT",
            entity_type="formulation",
            entity_id="ghi-789",
            action="reject",
            title="配合案を却下",
            severity="warning",
        )
        assert result["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_log_event_with_description(self, activity_service, mock_session):
        result = await activity_service.log_event(
            event_type="FORMULATION_VERIFY",
            entity_type="formulation",
            entity_id="jkl-012",
            action="verify",
            title="溶出試験不合格",
            description="Pb基準超過",
            severity="warning",
        )
        assert result["description"] == "Pb基準超過"

    @pytest.mark.asyncio
    async def test_log_event_swallows_exceptions(self, activity_service, mock_session):
        """Activity logging should never break the main workflow."""
        mock_session.execute.side_effect = Exception("DB error")
        result = await activity_service.log_event(
            event_type="TEST",
            entity_type="test",
            entity_id="test-id",
            action="test",
            title="Test",
        )
        assert result == {}


class TestActivityServiceConvenience:
    """Tests for convenience methods."""

    @pytest.mark.asyncio
    async def test_log_formulation_event(self, activity_service, mock_session):
        result = await activity_service.log_formulation_event(
            action="accept",
            formulation_id="abc-123",
            title="配合案を承認",
        )
        assert result["event_type"] == "FORMULATION_ACCEPT"
        assert result["entity_type"] == "formulation"
        assert result["entity_id"] == "abc-123"

    @pytest.mark.asyncio
    async def test_log_delivery_event(self, activity_service, mock_session):
        result = await activity_service.log_delivery_event(
            action="delivered",
            schedule_id="def-456",
            title="搬入完了",
        )
        assert result["event_type"] == "DELIVERY_DELIVERED"
        assert result["entity_type"] == "delivery"
        assert result["entity_id"] == "def-456"


class TestActivityServiceFeed:
    """Tests for get_feed() and get_entity_activity()."""

    @pytest.mark.asyncio
    async def test_get_feed_empty(self, activity_service, mock_session):
        # Mock empty count and empty rows
        count_mock = MagicMock()
        count_mock.scalar.return_value = 0
        rows_mock = MagicMock()
        rows_mock.fetchall.return_value = []
        mock_session.execute.side_effect = [count_mock, rows_mock]

        result = await activity_service.get_feed(limit=10, offset=0)
        assert result["items"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_feed_with_filters(self, activity_service, mock_session):
        count_mock = MagicMock()
        count_mock.scalar.return_value = 0
        rows_mock = MagicMock()
        rows_mock.fetchall.return_value = []
        mock_session.execute.side_effect = [count_mock, rows_mock]

        result = await activity_service.get_feed(
            event_type="FORMULATION_ACCEPT",
            entity_type="formulation",
            severity="info",
        )
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_entity_activity_empty(self, activity_service, mock_session):
        rows_mock = MagicMock()
        rows_mock.fetchall.return_value = []
        mock_session.execute.return_value = rows_mock

        result = await activity_service.get_entity_activity("formulation", "abc")
        assert result == []
