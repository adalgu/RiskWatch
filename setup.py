from setuptools import setup, find_packages

setup(
    name="news_system",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'sqlalchemy==2.0.15',
        'asyncpg==0.27.0',
        'alembic==1.10.4',
        'psycopg2-binary==2.9.6',
        'pydantic==1.10.7',
        'python-dotenv==1.0.0',
        'pytz==2023.3',
        'ujson==5.7.0',
        'aio-pika==9.5.0',
    ],
)
