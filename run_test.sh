#!/bin/bash

echo "Starting Docker containers..."
docker compose up -d

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker exec riskwatch-postgres-1 pg_isready -U postgres > /dev/null 2>&1; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 1
done

# Wait for RabbitMQ to be ready with improved check
echo "Waiting for RabbitMQ to be ready..."
until docker exec riskwatch-rabbitmq-1 rabbitmqctl await_startup > /dev/null 2>&1 && \
      docker exec riskwatch-rabbitmq-1 rabbitmqctl await_online_nodes 1 > /dev/null 2>&1; do
    echo "RabbitMQ is unavailable - sleeping"
    sleep 2
done

# Additional wait to ensure RabbitMQ is fully operational
sleep 1
echo "All services are ready. Running tests..."

docker exec -it riskwatch-news_storage-1 python -m scripts.init_and_test

# Check if test was successful
if [ $? -eq 0 ]; then
    echo "Test completed successfully!"
else
    echo "Test failed!"
fi
