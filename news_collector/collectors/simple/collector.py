"""
Simple collector implementation with flexible storage options.
"""
from typing import Any, Dict, List, Optional, Union
import logging
from datetime import datetime
import aiohttp
import asyncio
from .storage import DataStorage, PandasStorage, CSVStorage, SQLiteStorage, PostgresStorage

class SimpleCollector:
    """
    A simplified collector implementation that supports various storage backends
    and can work independently or with message brokers.
    """
    
    def __init__(
        self,
        storage: Optional[DataStorage] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the collector.
        
        Args:
            storage: Optional storage backend instance
            config: Optional configuration dictionary
        """
        self.storage = storage or PandasStorage()
        self.config = config or {}
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Configure logging for the collector."""
        logger = logging.getLogger(f"{self.__class__.__name__}")
        logger.setLevel(logging.INFO)
        return logger
        
    async def collect(
        self,
        urls: Union[str, List[str]],
        parser: callable,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Collect data from specified URLs.
        
        Args:
            urls: Single URL or list of URLs to collect from
            parser: Function to parse the response
            **kwargs: Additional arguments for collection
            
        Returns:
            List of collected data items
        """
        if isinstance(urls, str):
            urls = [urls]
            
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._collect_single(session, url, parser, **kwargs)
                for url in urls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        # Filter out exceptions and flatten results
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Collection error: {str(result)}")
            elif isinstance(result, list):
                valid_results.extend(result)
            else:
                valid_results.append(result)
                
        if self.storage:
            self.storage.save(valid_results)
            
        return valid_results
        
    async def _collect_single(
        self,
        session: aiohttp.ClientSession,
        url: str,
        parser: callable,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect data from a single URL.
        
        Args:
            session: aiohttp ClientSession instance
            url: URL to collect from
            parser: Function to parse the response
            **kwargs: Additional arguments for collection
            
        Returns:
            Collected data
        """
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                content = await response.text()
                return await parser(content, **kwargs)
        except Exception as e:
            self.logger.error(f"Error collecting from {url}: {str(e)}")
            raise
            
    @classmethod
    def with_pandas(cls, return_df: bool = True, **kwargs) -> 'SimpleCollector':
        """Create collector with pandas storage."""
        return cls(storage=PandasStorage(return_df=return_df), config=kwargs)
        
    @classmethod
    def with_csv(cls, filepath: str, **kwargs) -> 'SimpleCollector':
        """Create collector with CSV storage."""
        return cls(storage=CSVStorage(filepath=filepath), config=kwargs)
        
    @classmethod
    def with_sqlite(
        cls,
        db_path: str,
        table_name: str,
        **kwargs
    ) -> 'SimpleCollector':
        """Create collector with SQLite storage."""
        return cls(
            storage=SQLiteStorage(db_path=db_path, table_name=table_name),
            config=kwargs
        )
        
    @classmethod
    def with_postgres(
        cls,
        connection_string: str,
        table_name: str,
        **kwargs
    ) -> 'SimpleCollector':
        """Create collector with PostgreSQL storage."""
        return cls(
            storage=PostgresStorage(
                connection_string=connection_string,
                table_name=table_name
            ),
            config=kwargs
        )
