"""
HTTP client utility with retry and error handling capabilities.
"""
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)


class HTTPClient:
    """
    비동기 HTTP 클라이언트.
    재시도 및 에러 처리 기능을 포함합니다.
    """

    def __init__(self,
                 timeout: int = 30,
                 max_retries: int = 3,
                 backoff_factor: float = 1.0):
        """
        Initialize HTTP client.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            backoff_factor: Exponential backoff factor
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._session = None

    async def __aenter__(self):
        """Context manager entry."""
        await self.create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close_session()

    async def create_session(self) -> None:
        """Create aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self.timeout)

    async def close_session(self) -> None:
        """Close aiohttp session."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(
            (aiohttp.ClientError, asyncio.TimeoutError)
        )
    )
    async def request(self,
                      method: str,
                      url: str,
                      **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request with automatic retry and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response data as dictionary

        Raises:
            HTTPError: On request failure after retries
        """
        if self._session is None:
            await self.create_session()

        try:
            async with self._session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {str(e)}")
            raise

    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make GET request.

        Args:
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response data
        """
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make POST request.

        Args:
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response data
        """
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make PUT request.

        Args:
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response data
        """
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make DELETE request.

        Args:
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response data
        """
        return await self.request("DELETE", url, **kwargs)

    def add_headers(self, headers: Dict[str, str]) -> None:
        """
        Add default headers to session.

        Args:
            headers: Headers to add
        """
        if self._session:
            self._session.headers.update(headers)

    def set_proxy(self, proxy: str) -> None:
        """
        Set proxy for session.

        Args:
            proxy: Proxy URL
        """
        if self._session:
            self._session._connector_owner = False
            self._session._connector = aiohttp.TCPConnector(proxy=proxy)

    async def download_file(self, url: str, path: str) -> None:
        """
        Download file from URL.

        Args:
            url: File URL
            path: Save path
        """
        if self._session is None:
            await self.create_session()

        try:
            async with self._session.get(url) as response:
                response.raise_for_status()
                with open(path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)

        except Exception as e:
            logger.error(f"File download failed: {str(e)}")
            raise
