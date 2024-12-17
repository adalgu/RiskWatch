FROM python:3.12-slim

WORKDIR /app

# System packages (minimal required)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# FastAPI app dependencies
COPY pyproject.toml ./
COPY poetry.lock* ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-dev --no-root

# Application code
COPY . .

# Environment variables
ENV PYTHONPATH=/app:/app/news_collector

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
