"""
Factory for creating and managing collectors.
"""
from typing import Dict, Optional, Type

from ..collectors.base import BaseCollector
from ..collectors.metadata import MetadataCollector
from ..collectors.content import ContentCollector
from ..collectors.comments import CommentCollector
from ..collectors.stats import StatsCollector


class CollectorFactory:
    """
    Factory class for creating collector instances.
    Manages collector creation and configuration.
    """

    _collectors: Dict[str, Type[BaseCollector]] = {
        'metadata': MetadataCollector,
        'content': ContentCollector,
        'comments': CommentCollector,
        'stats': StatsCollector
    }

    @classmethod
    def create_collector(cls, collector_type: str, config: Optional[Dict] = None) -> BaseCollector:
        """
        Create a collector instance of the specified type.

        Args:
            collector_type: Type of collector to create
                ('metadata', 'content', 'comments', 'stats')
            config: Optional configuration for the collector

        Returns:
            Instance of the requested collector

        Raises:
            ValueError: If collector_type is not recognized
        """
        collector_class = cls._collectors.get(collector_type)
        if not collector_class:
            raise ValueError(
                f"Unknown collector type: {collector_type}. "
                f"Available types: {', '.join(cls._collectors.keys())}"
            )

        return collector_class(config)

    @classmethod
    def register_collector(cls, name: str, collector_class: Type[BaseCollector]) -> None:
        """
        Register a new collector type.

        Args:
            name: Name to register the collector under
            collector_class: Collector class to register

        Raises:
            ValueError: If name is already registered
        """
        if name in cls._collectors:
            raise ValueError(f"Collector type '{name}' is already registered")

        if not issubclass(collector_class, BaseCollector):
            raise ValueError(
                f"Collector class must inherit from BaseCollector"
            )

        cls._collectors[name] = collector_class

    @classmethod
    def get_available_collectors(cls) -> Dict[str, Type[BaseCollector]]:
        """
        Get dictionary of available collector types.

        Returns:
            Dict mapping collector names to their classes
        """
        return cls._collectors.copy()

    @classmethod
    def create_all_collectors(cls, config: Optional[Dict] = None) -> Dict[str, BaseCollector]:
        """
        Create instances of all registered collectors.

        Args:
            config: Optional configuration to apply to all collectors

        Returns:
            Dict mapping collector names to their instances
        """
        return {
            name: collector_class(config)
            for name, collector_class in cls._collectors.items()
        }


# Usage example:
"""
# Create specific collector
metadata_collector = CollectorFactory.create_collector('metadata', {
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret'
})

# Create all collectors
collectors = CollectorFactory.create_all_collectors({
    'browser_timeout': 20,
    'max_retries': 5
})

# Register custom collector
class CustomCollector(BaseCollector):
    async def collect(self, **kwargs):
        # Implementation
        pass

CollectorFactory.register_collector('custom', CustomCollector)
"""
