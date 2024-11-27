"""
Decorators for the dashboard application
"""

import time
import functools
import logging
from typing import Any, Callable, TypeVar, cast
from sqlalchemy.exc import SQLAlchemyError
from .exceptions import CollectionError, DatabaseError

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def handle_exceptions(error_message: str) -> Callable[[F], F]:
    """
    Exception handling decorator for dashboard functions.
    Catches exceptions and raises CollectionError with custom message.

    Args:
        error_message: Custom error message for the exception

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except CollectionError as e:
                # CollectionError는 그대로 전파
                logger.error(f"Dashboard error in {func.__name__}: {str(e)}")
                raise
            except Exception as e:
                # 다른 예외는 CollectionError로 변환
                logger.error(
                    f"Dashboard error in {func.__name__}: {error_message}")
                raise CollectionError(f"{error_message}: {str(e)}")
        return cast(F, wrapper)
    return decorator


def log_execution_time(func: F) -> F:
    """
    Decorator to log function execution time.

    Args:
        func: Function to be decorated

    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(
                f"Function {func.__name__} executed in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Function {func.__name__} failed after {execution_time:.2f} seconds: {str(e)}")
            raise
    return cast(F, wrapper)


def safe_db_operation(func: F) -> F:
    """
    Decorator for safely handling database operations.
    Catches SQLAlchemy errors and provides proper error handling.

    Args:
        func: Database operation function to be decorated

    Returns:
        Decorated function that safely handles database operations
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            raise DatabaseError(f"데이터베이스 작업 중 오류가 발생했습니다: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise DatabaseError(f"예상치 못한 오류가 발생했습니다: {str(e)}")
    return cast(F, wrapper)
