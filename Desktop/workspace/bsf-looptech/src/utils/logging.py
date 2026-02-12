"""
Enhanced logging utilities for BSF-LoopTech system.
Provides structured logging with context and error tracking.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

from src.config import settings

if TYPE_CHECKING:
    class LogRecordWithContext(logging.LogRecord):
        """LogRecord with additional context attributes."""
        user_id: Optional[str]
        farm_id: Optional[str]
        device_id: Optional[str]
        trace_id: Optional[str]
        duration: Optional[float]


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = getattr(record, 'user_id')
        if hasattr(record, 'farm_id'):
            log_data['farm_id'] = getattr(record, 'farm_id')
        if hasattr(record, 'device_id'):
            log_data['device_id'] = getattr(record, 'device_id')
        if hasattr(record, 'trace_id'):
            log_data['trace_id'] = getattr(record, 'trace_id')
        if hasattr(record, 'duration'):
            log_data['duration'] = getattr(record, 'duration')
        
        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else 'Unknown',
                'message': str(record.exc_info[1]) if record.exc_info[1] else '',
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data)


def setup_logging():
    """Setup application logging configuration."""
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Set formatter
    if settings.LOG_LEVEL.upper() == "DEBUG":
        # Use simple formatter for debugging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        # Use structured formatter for production
        formatter = StructuredFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


def log_execution_time(func_name: Optional[str] = None):
    """Decorator to log function execution time."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = datetime.utcnow()
            
            try:
                result = await func(*args, **kwargs)
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                logger.info(
                    f"Function {func_name or func.__name__} completed successfully",
                    extra={'duration': duration}
                )
                return result
                
            except Exception as e:
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                logger.error(
                    f"Function {func_name or func.__name__} failed: {str(e)}",
                    extra={'duration': duration},
                    exc_info=True
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = datetime.utcnow()
            
            try:
                result = func(*args, **kwargs)
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                logger.info(
                    f"Function {func_name or func.__name__} completed successfully",
                    extra={'duration': duration}
                )
                return result
                
            except Exception as e:
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                logger.error(
                    f"Function {func_name or func.__name__} failed: {str(e)}",
                    extra={'duration': duration},
                    exc_info=True
                )
                raise
        
        return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
    
    return decorator


@contextmanager
def log_context(logger: logging.Logger, operation: str, **context):
    """Context manager for logging operations with additional context."""
    start_time = datetime.utcnow()
    
    # Add context to all log records in this block
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        for key, value in context.items():
            setattr(record, key, value)
        return record
    
    logging.setLogRecordFactory(record_factory)
    
    try:
        logger.info(f"Starting {operation}", extra=context)
        yield
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        logger.info(
            f"Completed {operation}",
            extra={**context, 'duration': duration}
        )
        
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.error(
            f"Failed {operation}: {str(e)}",
            extra={**context, 'duration': duration},
            exc_info=True
        )
        raise
        
    finally:
        logging.setLogRecordFactory(old_factory)


def log_database_error(logger: logging.Logger, operation: str, error: Exception, **context):
    """Log database errors with specific handling for SQLAlchemy errors."""
    error_data = {
        'operation': operation,
        'error_type': type(error).__name__,
        'error_message': str(error),
        **context
    }
    
    if isinstance(error, SQLAlchemyError):
        # Extract additional SQLAlchemy error details
        orig_error = getattr(error, 'orig', None)
        if orig_error is not None:
            error_data['original_error'] = str(orig_error)
        
        statement = getattr(error, 'statement', None)
        if statement is not None:
            error_data['sql_statement'] = statement
            
        params = getattr(error, 'params', None)
        if params is not None:
            error_data['sql_params'] = "[REDACTED]"
    
    logger.error(
        f"Database operation failed: {operation}",
        extra=error_data,
        exc_info=True
    )


def log_api_request(logger: logging.Logger, method: str, path: str, **context):
    """Log API request with context."""
    logger.info(
        f"API Request: {method} {path}",
        extra={
            'method': method,
            'path': path,
            **context
        }
    )


def log_api_response(logger: logging.Logger, method: str, path: str, status_code: int, **context):
    """Log API response with context."""
    logger.info(
        f"API Response: {method} {path} - {status_code}",
        extra={
            'method': method,
            'path': path,
            'status_code': status_code,
            **context
        }
    )


logger = logging.getLogger(__name__)