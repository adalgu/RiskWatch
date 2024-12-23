"""
Usage examples for SimpleCollector with different storage backends.
"""
import asyncio
from bs4 import BeautifulSoup
from typing import Dict, Any
from .collector import SimpleCollector

async def example_parser(content: str, **kwargs) -> Dict[str, Any]:
    """
    Example parser that extracts title and content from HTML.
    
    Args:
        content: HTML content
        **kwargs: Additional parsing parameters
        
    Returns:
        Dict containing parsed data
    """
    soup = BeautifulSoup(content, 'html.parser')
    return {
        'title': soup.title.text if soup.title else '',
        'content': soup.get_text()[:200]  # First 200 chars as sample
    }

async def pandas_example():
    """Example using pandas storage."""
    # Create collector with pandas storage
    collector = SimpleCollector.with_pandas(return_df=True)
    
    # Collect data from sample URLs
    urls = [
        'https://example.com/page1',
        'https://example.com/page2'
    ]
    
    results = await collector.collect(urls, example_parser)
    print("Pandas DataFrame:", collector.storage.df)
    
async def csv_example():
    """Example using CSV storage."""
    # Create collector with CSV storage
    collector = SimpleCollector.with_csv('output/data.csv')
    
    # Collect and save to CSV
    await collector.collect(
        'https://example.com',
        example_parser
    )
    print("Data saved to output/data.csv")
    
async def sqlite_example():
    """Example using SQLite storage."""
    # Create collector with SQLite storage
    collector = SimpleCollector.with_sqlite(
        'output/data.db',
        'collected_data'
    )
    
    # Collect and save to SQLite
    await collector.collect(
        'https://example.com',
        example_parser
    )
    print("Data saved to SQLite database")
    
async def postgres_example():
    """Example using PostgreSQL storage."""
    # Create collector with PostgreSQL storage
    collector = SimpleCollector.with_postgres(
        'postgresql://user:pass@localhost:5432/db',
        'collected_data'
    )
    
    # Collect and save to PostgreSQL
    await collector.collect(
        'https://example.com',
        example_parser
    )
    print("Data saved to PostgreSQL database")

async def main():
    """Run all examples."""
    print("Running examples...")
    
    try:
        print("\n1. Pandas Example:")
        await pandas_example()
    except Exception as e:
        print(f"Pandas example error: {e}")
        
    try:
        print("\n2. CSV Example:")
        await csv_example()
    except Exception as e:
        print(f"CSV example error: {e}")
        
    try:
        print("\n3. SQLite Example:")
        await sqlite_example()
    except Exception as e:
        print(f"SQLite example error: {e}")
        
    try:
        print("\n4. PostgreSQL Example:")
        await postgres_example()
    except Exception as e:
        print(f"PostgreSQL example error: {e}")

if __name__ == '__main__':
    asyncio.run(main())
