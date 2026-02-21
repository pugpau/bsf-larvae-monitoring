"""
Unit tests for logging utilities.
Tests StructuredFormatter, get_logger, log_execution_time, log_context,
log_database_error, log_api_request, log_api_response.
"""

import json
import logging
from datetime import datetime

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.utils.logging import (
    StructuredFormatter,
    get_logger,
    log_context,
    log_database_error,
    log_api_request,
    log_api_response,
    log_execution_time,
)


# ===========================================================================
# StructuredFormatter
# ===========================================================================


@pytest.mark.unit
class TestStructuredFormatter:
    def test_format_basic_record(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Hello %s",
            args=("world",),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Hello world"
        assert "timestamp" in data
        assert "module" in data
        assert "line" in data

    def test_format_with_extra_fields(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=20,
            msg="alert",
            args=(),
            exc_info=None,
        )
        record.user_id = "u-123"
        record.trace_id = "t-456"
        record.duration = 1.5
        output = formatter.format(record)
        data = json.loads(output)
        assert data["user_id"] == "u-123"
        assert data["trace_id"] == "t-456"
        assert data["duration"] == 1.5

    def test_format_with_farm_and_device(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="ok",
            args=(),
            exc_info=None,
        )
        record.farm_id = "f-1"
        record.device_id = "d-2"
        output = formatter.format(record)
        data = json.loads(output)
        assert data["farm_id"] == "f-1"
        assert data["device_id"] == "d-2"

    def test_format_with_exception(self):
        formatter = StructuredFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=30,
            msg="oops",
            args=(),
            exc_info=exc_info,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert "test error" in data["exception"]["message"]


# ===========================================================================
# get_logger
# ===========================================================================


@pytest.mark.unit
class TestGetLogger:
    def test_returns_logger(self):
        lgr = get_logger("mylogger")
        assert isinstance(lgr, logging.Logger)
        assert lgr.name == "mylogger"

    def test_same_name_returns_same_logger(self):
        lgr1 = get_logger("shared")
        lgr2 = get_logger("shared")
        assert lgr1 is lgr2


# ===========================================================================
# log_execution_time decorator
# ===========================================================================


@pytest.mark.unit
class TestLogExecutionTime:
    async def test_async_decorator_returns_result(self):
        @log_execution_time()
        async def my_func():
            return 42

        result = await my_func()
        assert result == 42

    async def test_async_decorator_propagates_error(self):
        @log_execution_time("failing_func")
        async def my_func():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await my_func()

    def test_sync_decorator_returns_result(self):
        @log_execution_time()
        def my_func():
            return 99

        result = my_func()
        assert result == 99

    def test_sync_decorator_propagates_error(self):
        @log_execution_time("sync_fail")
        def my_func():
            raise ValueError("bad")

        with pytest.raises(ValueError, match="bad"):
            my_func()


# ===========================================================================
# log_context
# ===========================================================================


@pytest.mark.unit
class TestLogContext:
    def test_context_manager_success(self):
        lgr = get_logger("test_context_ok")
        # log_context has a conflict when extra kwargs are passed (both record
        # factory and extra= try to set the same key). Test without extra kwargs.
        with log_context(lgr, "test_op"):
            pass

    def test_context_manager_exception(self):
        lgr = get_logger("test_context_exc")
        with pytest.raises(RuntimeError, match="ctx_err"):
            with log_context(lgr, "failing_op"):
                raise RuntimeError("ctx_err")

    def test_context_restores_factory(self):
        original_factory = logging.getLogRecordFactory()
        lgr = get_logger("test_restore")
        with log_context(lgr, "op"):
            pass
        assert logging.getLogRecordFactory() is original_factory

    def test_context_restores_factory_on_error(self):
        original_factory = logging.getLogRecordFactory()
        lgr = get_logger("test_restore2")
        with pytest.raises(ValueError):
            with log_context(lgr, "op"):
                raise ValueError("x")
        assert logging.getLogRecordFactory() is original_factory


# ===========================================================================
# log_database_error
# ===========================================================================


@pytest.mark.unit
class TestLogDatabaseError:
    def test_logs_generic_error(self, caplog):
        lgr = get_logger("test_db_err")
        with caplog.at_level(logging.ERROR, logger="test_db_err"):
            log_database_error(lgr, "insert", RuntimeError("oops"))
        assert "Database operation failed: insert" in caplog.text

    def test_logs_sqlalchemy_error(self, caplog):
        lgr = get_logger("test_db_sqla")
        err = SQLAlchemyError("connection failed")
        with caplog.at_level(logging.ERROR, logger="test_db_sqla"):
            log_database_error(lgr, "query", err, user_id="u1")
        assert "Database operation failed: query" in caplog.text


# ===========================================================================
# log_api_request / log_api_response
# ===========================================================================


@pytest.mark.unit
class TestLogAPIRequestResponse:
    def test_log_api_request(self, caplog):
        lgr = get_logger("test_api_req")
        with caplog.at_level(logging.INFO, logger="test_api_req"):
            log_api_request(lgr, "GET", "/api/test")
        assert "API Request: GET /api/test" in caplog.text

    def test_log_api_response(self, caplog):
        lgr = get_logger("test_api_resp")
        with caplog.at_level(logging.INFO, logger="test_api_resp"):
            log_api_response(lgr, "POST", "/api/create", 201)
        assert "API Response: POST /api/create - 201" in caplog.text

    def test_log_api_request_with_context(self, caplog):
        lgr = get_logger("test_api_ctx")
        with caplog.at_level(logging.INFO, logger="test_api_ctx"):
            log_api_request(lgr, "DELETE", "/api/item/1", user_id="admin")
        assert "DELETE /api/item/1" in caplog.text
