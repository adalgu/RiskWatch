# Naver News Collector Example

## Setup

1. Install required packages:
```bash
pip install selenium pandas beautifulsoup4 aiohttp pytz
```

2. Install Chrome WebDriver:
   - Download ChromeDriver from: https://sites.google.com/chromium.org/driver/
   - Make sure the version matches your Chrome browser version
   - Add the ChromeDriver to your system PATH

## Running the Example

```bash
python scripts/test_simple_collector.py
```

This will:
1. Initialize the collector with Pandas storage
2. Collect today's news articles for the keyword "파이썬"
3. Display the results both as formatted text and a pandas DataFrame

## Troubleshooting

### WebDriver Issues
- Make sure Chrome and ChromeDriver versions match
- Verify ChromeDriver is in your system PATH
- Try running Chrome in non-headless mode for debugging (set `headless=False`)

### Import Issues
- Make sure you're running the script from the project root directory
- The script automatically adds the project root to Python path

## Customizing

You can modify the script to:
- Change the search keyword
- Collect from different dates
- Use different storage options (CSV, SQLite)
- Adjust the maximum number of articles
- Configure WebDriver options

For more examples and storage options, see:
`news_collector/collectors/simple/examples/naver_example.py`
