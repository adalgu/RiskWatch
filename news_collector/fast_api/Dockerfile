FROM python:3.12-slim

WORKDIR /app

# System packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencies
COPY pyproject.toml ./
COPY poetry.lock* ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-dev --no-root

# Application code
COPY . .

# Environment variables
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
