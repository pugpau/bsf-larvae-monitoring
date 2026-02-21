"""
Custom exceptions for database operations.
Provides specific error types for better error handling and logging.
"""
from typing import Optional


class DatabaseError(Exception):
    """Base exception for database-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class ConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    pass


class ValidationError(DatabaseError):
    """Exception raised when data validation fails."""
    pass


class NotFoundError(DatabaseError):
    """Exception raised when requested resource is not found."""
    pass


class DuplicateError(DatabaseError):
    """Exception raised when trying to create duplicate resources."""
    pass


class ConstraintError(DatabaseError):
    """Exception raised when database constraints are violated."""
    pass


class TransactionError(DatabaseError):
    """Exception raised when database transaction fails."""
    pass


class RepositoryError(DatabaseError):
    """Exception raised for repository-specific errors."""
    pass