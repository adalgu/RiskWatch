"""
Parallel execution manager for collectors.
"""
import asyncio
import logging
from typing import List, Any, Dict, Optional, Callable, TypeVar, Generic
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import pytz

from ..collectors.base import BaseCollector

logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')

T = TypeVar('T')
R = TypeVar('R')


class ParallelExecutor(Generic[T, R]):
    """
    병렬 실행 관리자.
    수집기의 병렬 실행을 관리합니다.
    """

    def __init__(self,
                 max_workers: int = 5,
                 chunk_size: int = 10,
                 retry_count: int = 3,
                 retry_delay: float = 1.0):
        """
        Initialize parallel executor.

        Args:
            max_workers: Maximum number of parallel workers
            chunk_size: Size of chunks for batch processing
            retry_count: Maximum retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._started = False

    async def start(self):
        """Start the executor."""
        if not self._started:
            self._started = True
            logger.info(
                f"Started parallel executor with {self.max_workers} workers")

    async def stop(self):
        """Stop the executor."""
        if self._started:
            self._executor.shutdown(wait=True)
            self._started = False
            logger.info("Stopped parallel executor")

    async def execute_parallel(self,
                               collector: BaseCollector,
                               items: List[T],
                               process_func: Callable[[T], R],
                               **kwargs) -> List[R]:
        """
        Execute collection in parallel.

        Args:
            collector: Collector instance
            items: List of items to process
            process_func: Function to process each item
            **kwargs: Additional parameters for process_func

        Returns:
            List of processed results
        """
        if not items:
            return []

        if not self._started:
            await self.start()

        logger.info(f"Starting parallel execution with {len(items)} items")
        start_time = datetime.now(KST)

        # 청크로 분할
        chunks = [items[i:i + self.chunk_size]
                  for i in range(0, len(items), self.chunk_size)]

        results = []
        total_processed = 0
        errors = 0

        try:
            for chunk in chunks:
                chunk_results = await self._process_chunk(
                    collector, chunk, process_func, **kwargs
                )
                results.extend(chunk_results)

                # 진행 상황 업데이트
                total_processed += len(chunk)
                success = len([r for r in chunk_results if r is not None])
                errors += len(chunk) - success

                progress = (total_processed / len(items)) * 100
                logger.info(
                    f"Progress: {progress:.1f}% "
                    f"({total_processed}/{len(items)}, "
                    f"Errors: {errors})"
                )

        except Exception as e:
            logger.error(f"Parallel execution error: {str(e)}")
            raise

        finally:
            duration = (datetime.now(KST) - start_time).total_seconds()
            logger.info(
                f"Parallel execution completed in {duration:.1f}s. "
                f"Total: {len(items)}, "
                f"Processed: {total_processed}, "
                f"Errors: {errors}"
            )

        return results

    async def _process_chunk(self,
                             collector: BaseCollector,
                             chunk: List[T],
                             process_func: Callable[[T], R],
                             **kwargs) -> List[Optional[R]]:
        """Process a chunk of items."""
        tasks = []
        for item in chunk:
            task = asyncio.create_task(
                self._process_with_retry(
                    collector, item, process_func, **kwargs
                )
            )
            tasks.append(task)

        return await asyncio.gather(*tasks)

    async def _process_with_retry(self,
                                  collector: BaseCollector,
                                  item: T,
                                  process_func: Callable[[T], R],
                                  **kwargs) -> Optional[R]:
        """Process an item with retry logic."""
        for attempt in range(self.retry_count):
            try:
                return await process_func(item, **kwargs)
            except Exception as e:
                if attempt < self.retry_count - 1:
                    logger.warning(
                        f"Retry {attempt + 1}/{self.retry_count} "
                        f"for item {item}: {str(e)}"
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(
                        f"Failed to process item {item} "
                        f"after {self.retry_count} attempts: {str(e)}"
                    )
                    return None

    async def execute_batch(self,
                            collector: BaseCollector,
                            items: List[T],
                            batch_size: int = 100,
                            **kwargs) -> Dict[str, Any]:
        """
        Execute batch collection.

        Args:
            collector: Collector instance
            items: List of items to process
            batch_size: Size of each batch
            **kwargs: Additional parameters

        Returns:
            Collection results and statistics
        """
        if not items:
            return {
                'results': [],
                'stats': {
                    'total': 0,
                    'success': 0,
                    'error': 0,
                    'duration': 0
                }
            }

        if not self._started:
            await self.start()

        start_time = datetime.now(KST)
        logger.info(f"Starting batch execution with {len(items)} items")

        # 배치로 분할
        batches = [items[i:i + batch_size]
                   for i in range(0, len(items), batch_size)]

        all_results = []
        total_success = 0
        total_error = 0

        try:
            for i, batch in enumerate(batches, 1):
                logger.info(
                    f"Processing batch {i}/{len(batches)} "
                    f"({len(batch)} items)"
                )

                results = await self.execute_parallel(
                    collector, batch, collector.collect, **kwargs
                )

                success = len([r for r in results if r is not None])
                errors = len(batch) - success

                all_results.extend(results)
                total_success += success
                total_error += errors

                logger.info(
                    f"Batch {i} completed: "
                    f"Success: {success}, "
                    f"Errors: {errors}"
                )

        except Exception as e:
            logger.error(f"Batch execution error: {str(e)}")
            raise

        finally:
            duration = (datetime.now(KST) - start_time).total_seconds()
            logger.info(
                f"Batch execution completed in {duration:.1f}s. "
                f"Total: {len(items)}, "
                f"Success: {total_success}, "
                f"Errors: {total_error}"
            )

        return {
            'results': all_results,
            'stats': {
                'total': len(items),
                'success': total_success,
                'error': total_error,
                'duration': duration
            }
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
