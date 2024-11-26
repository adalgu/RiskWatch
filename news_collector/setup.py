"""
Setup configuration for news_collector package.
"""
from setuptools import setup, find_packages

setup(
    name="news_collector",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.9.3",
        "beautifulsoup4>=4.12.3",
        "selenium>=4.17.2",
        "webdriver-manager>=4.0.1",
        "pytz>=2024.1",
        "python-dateutil>=2.8.2",
    ],
    python_requires=">=3.8",
)
