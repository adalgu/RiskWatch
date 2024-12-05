from setuptools import setup, find_packages

setup(
    name="news_collector",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0,<0.69.0",
        "uvicorn>=0.15.0,<0.16.0",
        "pydantic>=1.8.0,<2.0.0",
        "python-multipart>=0.0.5,<0.1.0",
        "aiofiles>=0.7.0,<0.8.0",
        "python-jose[cryptography]>=3.3.0,<3.4.0",
        "passlib[bcrypt]>=1.7.4,<1.8.0",
        "sqlalchemy>=1.4.23,<1.5.0",
        "psycopg2-binary>=2.9.1,<2.10.0",
        "pika>=1.2.0,<1.3.0",
        "selenium>=4.0.0",
        "beautifulsoup4>=4.9.3",
        "requests>=2.26.0",
        "streamlit>=1.0.0",
        "pandas>=1.3.0",
        "numpy>=1.21.0",
        "pytz>=2024.1",
    ],
    python_requires=">=3.9",
)
