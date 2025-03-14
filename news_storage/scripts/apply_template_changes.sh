#!/bin/bash
# Script to apply the Full Stack FastAPI Template database changes

set -e  # Exit on error

echo "Applying Full Stack FastAPI Template database changes..."

# 1. Create backup of current files
echo "Creating backups..."
cp -v news_storage/src/database.py news_storage/src/database.py.bak
cp -v alembic/env.py alembic/env.py.bak
cp -v alembic.ini alembic.ini.bak

# 2. Apply new files
echo "Applying new files..."
cp -v news_storage/src/database.py.new news_storage/src/database.py
cp -v alembic/env.py.new alembic/env.py
cp -v alembic.ini.new alembic.ini

# 3. Create directories if they don't exist
echo "Creating directories..."
mkdir -p news_storage/src/crud
mkdir -p news_storage/src/schemas

# 4. Copy new files
echo "Copying new files..."

# Copy CRUD files
echo "Copying CRUD files..."
cp -v news_storage/src/crud/base.py news_storage/src/crud/
cp -v news_storage/src/crud/__init__.py news_storage/src/crud/
cp -v news_storage/src/crud/article.py news_storage/src/crud/
cp -v news_storage/src/crud/comment.py news_storage/src/crud/

# Copy schema files
echo "Copying schema files..."
mkdir -p news_storage/src/schemas
cp -v news_storage/src/schemas/__init__.py news_storage/src/schemas/
cp -v news_storage/src/schemas/article.py news_storage/src/schemas/
cp -v news_storage/src/schemas/comment.py news_storage/src/schemas/

# Copy deps file
echo "Copying deps file..."
cp -v news_storage/src/deps.py news_storage/src/

# 5. Generate a new migration
echo "Generating a new migration..."
alembic revision --autogenerate -m "Apply Full Stack FastAPI Template patterns"

echo "Changes applied successfully!"
echo "To apply the migration, run: alembic upgrade head"
