# Simple Collector

A flexible and modular data collection system with support for multiple storage backends.

## Features

- Asynchronous data collection
- Multiple storage options:
  - Pandas DataFrame
  - CSV files
  - SQLite database
  - PostgreSQL database
- Easy to extend with new storage backends
- Simple parser-based architecture

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Example with Pandas

```python
import asyncio
from simple import SimpleCollector

async def my_parser(content, **kwargs):
    return {
        'data': content[:100]  # First 100 chars as sample
    }

async def main():
    # Create collector with pandas storage
    collector = SimpleCollector.with_pandas()
    
    # Collect data
    results = await collector.collect(
        'https://example.com',
        my_parser
    )
    
    # Access pandas DataFrame
    print(collector.storage.df)

if __name__ == '__main__':
    asyncio.run(main())
```

### CSV Storage Example

```python
# Save to CSV file
collector = SimpleCollector.with_csv('output.csv')
await collector.collect(urls, my_parser)
```

### SQLite Example

```python
# Save to SQLite database
collector = SimpleCollector.with_sqlite('data.db', 'my_table')
await collector.collect(urls, my_parser)
```

### PostgreSQL Example

```python
# Save to PostgreSQL database
collector = SimpleCollector.with_postgres(
    'postgresql://user:pass@localhost:5432/db',
    'my_table'
)
await collector.collect(urls, my_parser)
```

## Creating Custom Storage Backends

Implement the `DataStorage` abstract base class:

```python
from simple import DataStorage

class MyStorage(DataStorage):
    def save(self, data):
        # Implement your storage logic here
        pass

# Use with collector
collector = SimpleCollector(storage=MyStorage())
```

## Error Handling

The collector includes built-in error handling and logging. Failed requests are logged but don't stop the collection process.

## Async Support

All collection operations are asynchronous for better performance. Use `asyncio.run()` to execute collection tasks.

## Future Extensions

The collector is designed to be easily extended with:
- Message broker support (e.g., RabbitMQ)
- Additional storage backends
- Custom middleware
- Rate limiting and retry strategies

## Contributing

Feel free to submit issues and enhancement requests!
