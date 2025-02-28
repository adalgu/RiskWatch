# News Storage Module

This module provides database storage functionality for the RiskWatch project, following patterns from the Full Stack FastAPI Template.

## Overview

The news_storage module is responsible for:

1. Database connection management
2. ORM models for news articles, content, comments, and statistics
3. CRUD operations for database entities
4. Database migrations using Alembic

## Architecture

The module follows a clean architecture pattern with the following components:

- **Models**: SQLModel-based ORM models representing database tables
- **Schemas**: Pydantic models for data validation and serialization
- **CRUD**: Classes for database operations
- **Database**: Connection management and session handling

## Usage

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

# Get an article by ID
db_article = await article.get(db, id=1)

# Update an article
updated_article = await article.update(db, db_obj=db_article, obj_in={"title": "New Title"})

# Delete an article
await article.remove(db, id=1)
```

### Migrations

To create a new migration:

```bash
alembic revision --autogenerate -m "Description of changes"
```

To apply migrations:

```bash
alembic upgrade head
```

To revert migrations:

```bash
alembic downgrade -1  # Revert one migration
alembic downgrade base  # Revert all migrations
```

## Components

### Models

- `Article`: News article metadata
- `Content`: Full content of articles
- `Comment`: User comments on articles
- `CommentStats`: Statistics about comments

### CRUD Operations

- `CRUDBase`: Generic CRUD operations
- `CRUDArticle`: Article-specific operations
- `CRUDComment`: Comment-specific operations

### Schemas

- `ArticleBase`, `ArticleCreate`, `ArticleUpdate`, `Article`: Article schemas
- `CommentBase`, `CommentCreate`, `CommentUpdate`, `Comment`: Comment schemas

## Configuration

Database configuration is managed through environment variables:

- `DATABASE_URL`: Database connection string
- `DB_ECHO`: Enable SQL query logging (True/False)
- `DB_POOL_SIZE`: Connection pool size
- `DB_MAX_OVERFLOW`: Maximum number of connections to overflow
- `DB_POOL_TIMEOUT`: Connection timeout in seconds
- `DB_POOL_RECYCLE`: Connection recycle time in seconds
- `ENVIRONMENT`: Environment name (development, staging, production)
