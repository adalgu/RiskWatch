# FastAPI Integration Plan for News Collectors

## Overview

This document outlines the plan to integrate the existing news collectors with FastAPI, providing a REST API interface for metadata collection. The system is designed to run on a Mac Mini environment with PostgreSQL as the primary database.

## Database Schema

```sql
-- Metadata collection results
CREATE TABLE metadata_collections (
    id SERIAL PRIMARY KEY,
    keyword TEXT NOT NULL,
    date DATE,
    method TEXT NOT NULL,  -- 'API' or 'WEB'
    total_count INT,      -- Total available articles (API only)
    collected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    results JSONB,        -- Collected articles
    UNIQUE(keyword, date, method)
);

-- Collection request tracking
CREATE TABLE collection_requests (
    id SERIAL PRIMARY KEY,
    keyword TEXT NOT NULL,
    date DATE,
    method TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'pending', 'completed', 'failed'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    error_message TEXT     -- Populated if status is 'failed'
);
```

## API Endpoints

### 1. Metadata Collection

```python
from typing import Literal, Optional
from datetime import date
from pydantic import BaseModel

class CollectionRequest(BaseModel):
    method: Literal["API", "WEB"]
    keyword: str
    max_articles: Optional[int] = None
    date: Optional[date] = None

@router.post("/collect")
async def collect(request: CollectionRequest):
    """
    Collect news metadata using specified method.
    
    - API method: Collects up to 1000 recent articles
    - WEB method: Collects up to 100 articles for a specific date
    """
    # Check existing results
    existing = await get_recent_collection(
        request.keyword,
        request.date,
        request.method
    )
    if existing:
        return existing

    # Create request record
    request_id = await create_collection_request(request)
    
    try:
        # Collect data
        if request.method == "API":
            collector = APIMetadataCollector()
            results = await collector.collect(
                keyword=request.keyword,
                max_articles=min(request.max_articles or 1000, 1000)
            )
        else:
            collector = WebMetadataCollector()
            results = await collector.collect(
                keyword=request.keyword,
                date=request.date,
                max_articles=min(request.max_articles or 100, 100)
            )
            
        # Save results
        await save_collection_results(request, results)
        await update_request_status(request_id, "completed")
        
        return results
        
    except Exception as e:
        await update_request_status(request_id, "failed", str(e))
        raise
```

### 2. Batch Processing

```python
class BatchTask(BaseModel):
    metadata: bool = True
    comments: bool = False
    content: bool = False
    analysis: bool = False

class BatchRequest(BaseModel):
    task: BatchTask
    method: Literal["API", "WEB"]
    keyword: str
    date: Optional[date] = None

@router.post("/batch")
async def run_batch(request: BatchRequest):
    """
    Run batch processing pipeline.
    
    1. Collect metadata
    2. Optionally collect comments (Naver news only)
    3. Optionally collect full content
    4. Optionally run analysis
    """
    # Implementation will be added in next phase
    pass
```

## Resource Management

1. WebDriver Instances:
   - Maximum 2 concurrent instances
   - Implement connection pooling
   - Auto-cleanup after 5 minutes of inactivity

2. Database Connections:
   - Use connection pooling
   - Maximum 10 connections
   - Statement timeout: 30 seconds

## Error Handling

1. HTTP Errors:
   ```python
   class CollectionError(HTTPException):
       def __init__(self, detail: str):
           super().__init__(status_code=500, detail=detail)

   class ValidationError(HTTPException):
       def __init__(self, detail: str):
           super().__init__(status_code=400, detail=detail)
   ```

2. Database Errors:
   - Implement retries for transient errors
   - Log detailed error information
   - Return user-friendly error messages

## Implementation Phases

1. Phase 1: Basic Integration
   - Set up FastAPI project structure
   - Implement database schema
   - Create basic /collect endpoint
   - Add error handling

2. Phase 2: Batch Processing
   - Implement /batch endpoint
   - Add comment collection
   - Add content collection
   - Add basic analysis

3. Phase 3: Optimization
   - Add monitoring
   - Optimize WebDriver management
   - Add rate limiting
   - Improve error handling

## Testing Strategy

1. Unit Tests:
   ```python
   async def test_collect_api():
       request = CollectionRequest(
           method="API",
           keyword="테스트",
           max_articles=10
       )
       response = await collect(request)
       assert len(response['items']) <= 10
       
   async def test_collect_web():
       request = CollectionRequest(
           method="WEB",
           keyword="테스트",
           date=date.today(),
           max_articles=10
       )
       response = await collect(request)
       assert len(response['items']) <= 10
   ```

2. Integration Tests:
   - Test database operations
   - Test WebDriver management
   - Test error scenarios

## Monitoring

1. Key Metrics:
   - Collection success rate
   - Average collection time
   - WebDriver instance count
   - Database connection count
   - Error rate

2. Logging:
   ```python
   logger = logging.getLogger("news_collector")
   logger.setLevel(logging.INFO)
   
   @router.post("/collect")
   async def collect(request: CollectionRequest):
       logger.info(f"Starting collection: {request.method} - {request.keyword}")
       # ... collection logic ...
       logger.info(f"Collection completed: {len(results['items'])} articles")
   ```

## Next Steps

1. Create FastAPI project structure
2. Implement database schema
3. Create basic endpoints
4. Add tests
5. Deploy and test on Mac Mini

## Notes for AI Code Interpreter

- All code examples use type hints for better code understanding
- Database schema includes comments explaining field purposes
- API endpoints include detailed docstrings
- Error handling patterns are clearly defined
- Resource limits are explicitly stated
- Testing examples show expected behavior
