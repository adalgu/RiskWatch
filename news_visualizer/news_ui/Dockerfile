FROM python:3.12-slim

WORKDIR /app

# Install system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install news_storage first
COPY news_storage/ /app/news_storage/
RUN pip install -e /app/news_storage

# Copy poetry files
COPY news_visualizer/news_ui/pyproject.toml /app/pyproject.toml
COPY news_visualizer/news_ui/poetry.lock /app/poetry.lock

# Install dependencies
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --only main --no-root

# Copy application code
COPY news_visualizer/news_ui/ /app/

# Expose Streamlit port
EXPOSE 8501

# Set environment variables
ENV PYTHONPATH=/app:/app/news_storage

# Run application
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
