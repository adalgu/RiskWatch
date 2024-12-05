FROM python:3.12-slim

# Install system packages including PostgreSQL client
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create scripts directory
RUN mkdir -p /app/scripts

# Copy migration script first and make it executable
COPY scripts/run_migrations.sh /app/scripts/
RUN chmod +x /app/scripts/run_migrations.sh

# Copy project files
COPY pyproject.toml ./
COPY poetry.lock* ./
COPY ./src/ ./src/

# Install poetry and dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install && \
    pip install alembic psycopg2-binary

# Set environment variables
ENV PYTHONPATH=/app:/app/common:/app/news_storage/src

# Ensure script has Unix line endings
# RUN sed -i 's/\r$//' /app/scripts/run_migrations.sh

# Use the migration script as entrypoint
# ENTRYPOINT ["/app/scripts/run_migrations.sh"]

# Default command (will be passed to the entrypoint script)
CMD ["python", "-m", "src.consumer"]
