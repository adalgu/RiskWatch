"""
Simple collector module for flexible data collection and storage.
"""
from .collector import SimpleCollector
from .storage import (
    DataStorage,
    PandasStorage,
    CSVStorage,
    SQLiteStorage,
    PostgresStorage
)

__all__ = [
    'SimpleCollector',
    'DataStorage',
    'PandasStorage',
    'CSVStorage',
    'SQLiteStorage',
    'PostgresStorage'
]
