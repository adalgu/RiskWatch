"""
Abstract base class and implementations for different storage backends.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List
import pandas as pd
import sqlite3
import csv
import os

class DataStorage(ABC):
    """Abstract base class for data storage implementations."""
    
    @abstractmethod
    def save(self, data: List[Dict[str, Any]]) -> None:
        """Save data to storage."""
        pass

class PandasStorage(DataStorage):
    """Store data using pandas DataFrame."""
    
    def __init__(self, return_df: bool = True):
        self.return_df = return_df
        self.df = None
    
    def save(self, data: List[Dict[str, Any]]) -> Any:
        """Save data to pandas DataFrame."""
        self.df = pd.DataFrame(data)
        return self.df if self.return_df else None

class CSVStorage(DataStorage):
    """Store data in CSV file."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    def save(self, data: List[Dict[str, Any]]) -> None:
        """Save data to CSV file."""
        if not data:
            return
            
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        
        with open(self.filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

class SQLiteStorage(DataStorage):
    """Store data in SQLite database."""
    
    def __init__(self, db_path: str, table_name: str):
        self.db_path = db_path
        self.table_name = table_name
    
    def save(self, data: List[Dict[str, Any]]) -> None:
        """Save data to SQLite database."""
        if not data:
            return
            
        df = pd.DataFrame(data)
        
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            df.to_sql(self.table_name, conn, if_exists='append', index=False)

class PostgresStorage(DataStorage):
    """Store data in PostgreSQL database."""
    
    def __init__(self, connection_string: str, table_name: str):
        self.connection_string = connection_string
        self.table_name = table_name
    
    def save(self, data: List[Dict[str, Any]]) -> None:
        """Save data to PostgreSQL database."""
        if not data:
            return
            
        df = pd.DataFrame(data)
        
        # Using pandas to_sql with PostgreSQL
        df.to_sql(
            self.table_name,
            self.connection_string,
            if_exists='append',
            index=False
        )
