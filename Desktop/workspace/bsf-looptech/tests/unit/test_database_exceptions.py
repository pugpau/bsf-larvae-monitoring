"""
Unit tests for custom database exception classes.
"""

import pytest

from src.database.exceptions import (
    DatabaseError,
    ConnectionError,
    ValidationError,
    NotFoundError,
    DuplicateError,
    ConstraintError,
    TransactionError,
    RepositoryError,
)


@pytest.mark.unit
class TestDatabaseExceptions:
    def test_database_error_message(self):
        err = DatabaseError("test error")
        assert str(err) == "test error"
        assert err.message == "test error"
        assert err.original_error is None

    def test_database_error_with_original(self):
        orig = ValueError("original")
        err = DatabaseError("wrapped", original_error=orig)
        assert err.original_error is orig
        assert err.message == "wrapped"

    def test_connection_error(self):
        err = ConnectionError("connection failed")
        assert isinstance(err, DatabaseError)
        assert str(err) == "connection failed"

    def test_validation_error(self):
        err = ValidationError("invalid data")
        assert isinstance(err, DatabaseError)
        assert err.message == "invalid data"

    def test_not_found_error(self):
        err = NotFoundError("record not found")
        assert isinstance(err, DatabaseError)

    def test_duplicate_error(self):
        err = DuplicateError("duplicate entry")
        assert isinstance(err, DatabaseError)

    def test_constraint_error(self):
        err = ConstraintError("constraint violated")
        assert isinstance(err, DatabaseError)

    def test_transaction_error(self):
        err = TransactionError("transaction failed", original_error=RuntimeError("tx"))
        assert isinstance(err, DatabaseError)
        assert err.original_error is not None

    def test_repository_error(self):
        err = RepositoryError("repo error")
        assert isinstance(err, DatabaseError)

    def test_all_exceptions_are_catchable_as_database_error(self):
        exceptions = [
            ConnectionError("a"),
            ValidationError("b"),
            NotFoundError("c"),
            DuplicateError("d"),
            ConstraintError("e"),
            TransactionError("f"),
            RepositoryError("g"),
        ]
        for exc in exceptions:
            with pytest.raises(DatabaseError):
                raise exc
