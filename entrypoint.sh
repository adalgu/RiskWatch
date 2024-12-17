#!/bin/sh
set -e

echo "Running Alembic migrations..."
# alembic.ini 파일이 alembic/ 디렉토리 안에 있는 경우 경로를 지정
alembic -c alembic/alembic.ini upgrade head

echo "Starting the application..."
exec "$@"
