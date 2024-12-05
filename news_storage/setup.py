from setuptools import setup, find_packages

setup(
    name="news_storage",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy[asyncio]",
        "asyncpg",
        "alembic",
        "psycopg2-binary",
        "pydantic",
        "python-dotenv",
        "pytz",
        "ujson",
        "aio-pika",
        "sqlmodel"
    ]
)
