"""
Proxy management for collectors.
"""
import asyncio
import logging
import random
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import aiohttp
import pytz

logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')


class ProxyManager:
    """
    프록시 관리자.
    수집기의 프록시 사용을 관리합니다.
    """

    def __init__(self,
                 proxies: Optional[List[str]] = None,
                 check_interval: int = 300,
                 timeout: int = 10,
                 max_fails: int = 3):
        """
        Initialize proxy manager.

        Args:
            proxies: List of proxy URLs
            check_interval: Interval for proxy health checks in seconds
            timeout: Proxy request timeout in seconds
            max_fails: Maximum consecutive failures before proxy removal
        """
        self.proxies = set(proxies) if proxies else set()
        self.check_interval = check_interval
        self.timeout = timeout
        self.max_fails = max_fails

        self._active_proxies: Set[str] = set()
        self._failed_proxies: Dict[str, int] = {}  # proxy -> fail count
        self._proxy_stats: Dict[str, Dict] = {}    # proxy -> stats
        self._last_check: Dict[str, datetime] = {}  # proxy -> last check time

        self._check_task = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Start proxy manager and health checks."""
        self._active_proxies = self.proxies.copy()
        for proxy in self._active_proxies:
            self._proxy_stats[proxy] = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'last_success': None,
                'last_failure': None,
                'average_response_time': 0
            }
            self._last_check[proxy] = datetime.now(KST)

        # 주기적 상태 체크 시작
        self._check_task = asyncio.create_task(
            self._check_proxies_periodically())
        logger.info(f"Started proxy manager with {len(self.proxies)} proxies")

    async def stop(self):
        """Stop proxy manager and cleanup."""
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped proxy manager")

    async def get_proxy(self) -> Optional[str]:
        """
        Get available proxy.

        Returns:
            Proxy URL or None if no proxies available
        """
        async with self._lock:
            if not self._active_proxies:
                return None
            return random.choice(list(self._active_proxies))

    async def report_success(self, proxy: str, response_time: float):
        """
        Report successful proxy use.

        Args:
            proxy: Proxy URL
            response_time: Request response time in seconds
        """
        async with self._lock:
            if proxy in self._proxy_stats:
                stats = self._proxy_stats[proxy]
                stats['total_requests'] += 1
                stats['successful_requests'] += 1
                stats['last_success'] = datetime.now(KST)

                # 평균 응답 시간 업데이트
                n = stats['successful_requests']
                avg = stats['average_response_time']
                stats['average_response_time'] = (
                    avg * (n - 1) + response_time) / n

                # 실패 카운트 리셋
                self._failed_proxies.pop(proxy, None)

    async def report_failure(self, proxy: str, error: Exception):
        """
        Report proxy failure.

        Args:
            proxy: Proxy URL
            error: Error that occurred
        """
        async with self._lock:
            if proxy in self._proxy_stats:
                stats = self._proxy_stats[proxy]
                stats['total_requests'] += 1
                stats['failed_requests'] += 1
                stats['last_failure'] = datetime.now(KST)

                # 실패 카운트 증가
                self._failed_proxies[proxy] = self._failed_proxies.get(
                    proxy, 0) + 1

                # 최대 실패 횟수 초과 시 비활성화
                if self._failed_proxies[proxy] >= self.max_fails:
                    self._deactivate_proxy(proxy)
                    logger.warning(
                        f"Deactivated proxy {proxy} after {self.max_fails} failures"
                    )

    async def _check_proxies_periodically(self):
        """Periodically check proxy health."""
        while True:
            try:
                await self._check_all_proxies()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in proxy health check: {str(e)}")
                await asyncio.sleep(self.check_interval)

    async def _check_all_proxies(self):
        """Check health of all proxies."""
        async with self._lock:
            all_proxies = self.proxies.copy()

        tasks = []
        for proxy in all_proxies:
            if (datetime.now(KST) - self._last_check.get(proxy, datetime.min.replace(tzinfo=KST))).total_seconds() >= self.check_interval:
                tasks.append(self._check_proxy(proxy))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            async with self._lock:
                for proxy, result in zip(all_proxies, results):
                    self._last_check[proxy] = datetime.now(KST)
                    if isinstance(result, Exception):
                        logger.warning(
                            f"Proxy check failed for {proxy}: {str(result)}")
                    elif result:
                        self._active_proxies.add(proxy)
                        self._failed_proxies.pop(proxy, None)
                    else:
                        self._deactivate_proxy(proxy)

    async def _check_proxy(self, proxy: str) -> bool:
        """
        Check single proxy health.

        Args:
            proxy: Proxy URL to check

        Returns:
            bool: True if proxy is healthy
        """
        try:
            start_time = datetime.now(KST)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://www.google.com',
                    proxy=proxy,
                    timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        response_time = (datetime.now(KST) -
                                         start_time).total_seconds()
                        await self.report_success(proxy, response_time)
                        return True
            return False
        except Exception as e:
            await self.report_failure(proxy, e)
            return False

    def _deactivate_proxy(self, proxy: str):
        """
        Deactivate proxy.

        Args:
            proxy: Proxy URL to deactivate
        """
        self._active_proxies.discard(proxy)
        self._failed_proxies.pop(proxy, None)

    def get_stats(self) -> Dict:
        """
        Get proxy statistics.

        Returns:
            Dict containing proxy statistics
        """
        return {
            'total_proxies': len(self.proxies),
            'active_proxies': len(self._active_proxies),
            'failed_proxies': len(self._failed_proxies),
            'proxy_stats': self._proxy_stats.copy()
        }

    async def add_proxy(self, proxy: str):
        """
        Add new proxy.

        Args:
            proxy: Proxy URL to add
        """
        async with self._lock:
            self.proxies.add(proxy)
            if await self._check_proxy(proxy):
                self._active_proxies.add(proxy)
                self._proxy_stats[proxy] = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'last_success': None,
                    'last_failure': None,
                    'average_response_time': 0
                }
                self._last_check[proxy] = datetime.now(KST)
                logger.info(f"Added new proxy: {proxy}")

    async def remove_proxy(self, proxy: str):
        """
        Remove proxy.

        Args:
            proxy: Proxy URL to remove
        """
        async with self._lock:
            self.proxies.discard(proxy)
            self._active_proxies.discard(proxy)
            self._failed_proxies.pop(proxy, None)
            self._proxy_stats.pop(proxy, None)
            self._last_check.pop(proxy, None)
            logger.info(f"Removed proxy: {proxy}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


# Usage example:
"""
async def collect_with_proxy():
    proxies = [
        "http://proxy1:8080",
        "http://proxy2:8080",
        "http://proxy3:8080"
    ]
    
    async with ProxyManager(proxies=proxies) as proxy_manager:
        while True:
            proxy = await proxy_manager.get_proxy()
            if not proxy:
                logger.error("No proxies available")
                break
                
            try:
                # Use proxy for collection
                result = await collect_data(proxy=proxy)
                await proxy_manager.report_success(proxy, response_time=1.0)
                
            except Exception as e:
                await proxy_manager.report_failure(proxy, e)
                continue
"""
