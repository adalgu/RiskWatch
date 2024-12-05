#!/bin/bash
set -e

echo "Waiting for postgres..."

# Wait for postgres to be ready
until PGPASSWORD=password psql -h "postgres" -U "postgres" -d "news_db" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up - executing migrations"

# Run migrations with proper path to alembic
cd /app && alembic upgrade head

# Execute the main command passed to the container
exec "$@"
