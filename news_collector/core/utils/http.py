"""
HTTP utility functions.
"""
import aiohttp
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class HttpUtils:
    """HTTP utility functions."""

    @staticmethod
    async def get(url: str, headers: Optional[Dict[str, str]] = None, proxy: Optional[str] = None) -> Dict[str, Any]:
        """Make HTTP GET request."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, proxy=proxy) as response:
                    if response.status == 200:
                        return {
                            'success': True,
                            'status': response.status,
                            'data': await response.text()
                        }
                    else:
                        return {
                            'success': False,
                            'status': response.status,
                            'error': f"HTTP {response.status}"
                        }
        except Exception as e:
            logger.error(f"HTTP request failed: {str(e)}")
            return {
                'success': False,
                'status': 500,
                'error': str(e)
            }

    @staticmethod
    async def post(url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None, proxy: Optional[str] = None) -> Dict[str, Any]:
        """Make HTTP POST request."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, proxy=proxy) as response:
                    if response.status == 200:
                        return {
                            'success': True,
                            'status': response.status,
                            'data': await response.text()
                        }
                    else:
                        return {
                            'success': False,
                            'status': response.status,
                            'error': f"HTTP {response.status}"
                        }
        except Exception as e:
            logger.error(f"HTTP request failed: {str(e)}")
            return {
                'success': False,
                'status': 500,
                'error': str(e)
            }
