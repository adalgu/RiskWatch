#!/bin/bash
set -e

echo "Waiting for postgres..."

# Wait for postgres server to be ready (connect to 'postgres' default db)
until PGPASSWORD=password psql -h "postgres" -U "postgres" -d "postgres" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up - checking database"

# Check if database exists, if not create it
PGPASSWORD=password psql -h "postgres" -U "postgres" -d "postgres" -tc "SELECT 1 FROM pg_database WHERE datname = 'news_db'" | grep -q 1 || \
    PGPASSWORD=password psql -h "postgres" -U "postgres" -d "postgres" -c "CREATE DATABASE news_db"

>&2 echo "Database is ready - executing migrations"

# Run migrations with proper path to alembic
cd /app && alembic upgrade head

# Execute the main command passed to the container
exec "$@"
