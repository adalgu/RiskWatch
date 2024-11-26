FROM python:3.8-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy only the news_storage directory
COPY news_storage /app/news_storage

# Install Python dependencies
COPY news_storage/requirements.txt /app/
RUN pip install -r requirements.txt

# Install the package
WORKDIR /app/news_storage
RUN pip install -e .

# Set working directory back to /app
WORKDIR /app

# Run consumer
CMD ["python", "-m", "news_storage.consumer"]
