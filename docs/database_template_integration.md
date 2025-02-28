# Database Template Integration Guide

This document explains how to integrate the Full Stack FastAPI Template database components into the RiskWatch project.

## Overview

We've created a set of files that follow the patterns from the Full Stack FastAPI Template to improve our database operations. These changes include:

1. Better database connection management with connection pooling
2. Dependency injection for database sessions
3. Generic CRUD operations for all models
4. Pydantic schemas for data validation and serialization
5. Improved Alembic configuration for migrations

## Files Created

### Database Components

- `news_storage/src/database.py.new`: Updated database connection management
- `news_storage/src/deps.py`: Dependency injection for database sessions

### CRUD Operations

- `news_storage/src/crud/base.py`: Generic CRUD operations
- `news_storage/src/crud/article.py`: Article-specific operations
- `news_storage/src/crud/comment.py`: Comment-specific operations

### Schemas

- `news_storage/src/schemas/article.py`: Article schemas
- `news_storage/src/schemas/comment.py`: Comment schemas

### Alembic Configuration

- `alembic/env.py.new`: Updated Alembic environment configuration
- `alembic.ini.new`: Updated Alembic configuration

### Documentation

- `news_storage/README.md`: Documentation for the news_storage module

## How to Apply the Changes

We've created a script to apply all the changes at once:

```bash
# Make the script executable
chmod +x news_storage/scripts/apply_template_changes.sh

# Run the script
./news_storage/scripts/apply_template_changes.sh
```

The script will:

1. Create backups of the current files
2. Apply the new files
3. Generate a new migration

After running the script, you'll need to apply the migration:

```bash
alembic upgrade head
```

## Manual Application

If you prefer to apply the changes manually:

1. Copy the new database file:
   ```bash
   cp news_storage/src/database.py.new news_storage/src/database.py
   ```

2. Copy the new Alembic files:
   ```bash
   cp alembic/env.py.new alembic/env.py
   cp alembic.ini.new alembic.ini
   ```

3. Create the necessary directories:
   ```bash
   mkdir -p news_storage/src/crud
   mkdir -p news_storage/src/schemas
   ```

4. Copy the CRUD and schema files:
   ```bash
   cp -r news_storage/src/crud/* news_storage/src/crud/
   cp -r news_storage/src/schemas/* news_storage/src/schemas/
   cp news_storage/src/deps.py news_storage/src/deps.py
   ```

5. Generate a new migration:
   ```bash
   alembic revision --autogenerate -m "Apply Full Stack FastAPI Template patterns"
   ```

6. Apply the migration:
   ```bash
   alembic upgrade head
   ```

## Using the New Components

### Database Session

```python
from news_storage.src.deps import SessionDep

@app.get("/articles/")
async def read_articles(db: SessionDep):
    # Use the database session
    articles = await article.get_multi(db, skip=0, limit=100)
    return {"articles": articles}
```

### CRUD Operations

```python
from news_storage.src.crud.article import article
from news_storage.src.schemas.article import ArticleCreate

# Create a new article
article_in = ArticleCreate(
    main_keyword="example",
    naver_link="https://example.com",
    title="Example Article"
)
db_article = await article.create(db, obj_in=article_in)
```

## Benefits

- **Improved Error Handling**: Better transaction management and error handling
- **Type Safety**: Pydantic schemas provide type validation and better IDE support
- **Code Reuse**: Generic CRUD operations reduce code duplication
- **Dependency Injection**: Cleaner API endpoints with dependency injection
- **Connection Pooling**: Better database connection management
- **Migration Management**: Improved Alembic configuration for migrations

## Rollback

If you need to roll back the changes, you can restore the backup files:

```bash
cp news_storage/src/database.py.bak news_storage/src/database.py
cp alembic/env.py.bak alembic/env.py
cp alembic.ini.bak alembic.ini
```

And revert the migration:

```bash
alembic downgrade -1
```
