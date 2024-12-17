"""
Base collector module providing common functionality for all collectors.
Extends the original BaseCollector with async support and enhanced features.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    Enhanced base collector with async support and improved error handling.
    Maintains compatibility with the original interface while adding new features.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize collector with configuration.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging for the collector."""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.setLevel(logging.INFO)

    async def init_session(self) -> None:
        """
        Initialize session and connections.
        Override in subclasses if needed.
        """
        pass

    @abstractmethod
    async def collect(self, **kwargs) -> Dict[str, Any]:
        """
        Abstract collection method that must be implemented by all collectors.
        Enhanced with async support.

        Args:
            **kwargs: Collection parameters

        Returns:
            Dict[str, Any]: Collected data

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Collectors must implement collect method")

    def validate(self, data: Any) -> bool:
        """
        Validate collected data. Maintains compatibility with original interface.

        Args:
            data: Data to validate

        Returns:
            bool: True if valid, False otherwise
        """
        return True

    async def validate_async(self, data: Any) -> bool:
        """
        Async version of validate method for complex validation logic.

        Args:
            data: Data to validate

        Returns:
            bool: True if valid, False otherwise
        """
        return self.validate(data)

    async def preprocess_data(self, data: Any) -> Any:
        """
        Preprocess collected data before returning.

        Args:
            data: Raw collected data

        Returns:
            Preprocessed data
        """
        return data

    async def handle_error(self, error: Exception) -> None:
        """
        Handle collection errors with improved logging.

        Args:
            error: The exception that occurred
        """
        self.logger.error(
            f"Collection error in {self.__class__.__name__}: {str(error)}",
            exc_info=True
        )

    async def collect_with_retry(self,
                                 retry_count: int = 3,
                                 delay: float = 1.0,
                                 **kwargs) -> Any:
        """
        Attempt collection with retry logic.

        Args:
            retry_count: Number of retry attempts
            delay: Delay between retries in seconds
            **kwargs: Collection parameters

        Returns:
            Collected data

        Raises:
            Exception: If all retry attempts fail
        """
        for attempt in range(retry_count):
            try:
                self.logger.info(
                    f"Collection attempt {attempt + 1}/{retry_count}")
                return await self.collect(**kwargs)
            except Exception as e:
                await self.handle_error(e)
                if attempt < retry_count - 1:
                    await asyncio.sleep(delay * (attempt + 1))
                else:
                    raise

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Safely get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def log_collection_start(self, details: Dict = None) -> None:
        """
        Log collection start with details.

        Args:
            details: Additional details to log
        """
        msg = f"Starting collection at {datetime.now()}"
        if details:
            msg += f" with details: {details}"
        self.logger.info(msg)

    def log_collection_end(self,
                           success: bool = True,
                           details: Dict = None) -> None:
        """
        Log collection completion with status.

        Args:
            success: Whether collection was successful
            details: Additional details to log
        """
        status = "successfully" if success else "with failures"
        msg = f"Completed collection {status} at {datetime.now()}"
        if details:
            msg += f" with details: {details}"
        self.logger.info(msg)

    async def cleanup(self) -> None:
        """
        Cleanup resources after collection.
        Override in subclasses if needed.
        """
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup()
