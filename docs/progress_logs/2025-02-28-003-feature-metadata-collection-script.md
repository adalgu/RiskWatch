# 메타데이터 수집 및 저장 스크립트 구현

- **날짜**: 2025-02-28
- **작성자**: Gunn Kim
- **관련 이슈**: N/A
- **이전 로그**: 
  - [Full Stack FastAPI Template 데이터베이스 컴포넌트 통합](./2025-02-28-002-refactor-database-template-integration.md)
  - [메타데이터 수집 스크립트 오류 해결](./2025-02-28-001-bug-fix-metadata-collection.md)

## 문제 상황

Full Stack FastAPI Template 데이터베이스 컴포넌트를 성공적으로 통합한 후, 이를 활용하여 메타데이터를 수집하고 데이터베이스에 저장하는 기능이 필요했습니다. 기존의 메타데이터 수집 로직은 있었지만, 새로운 데이터베이스 컴포넌트와 통합되지 않아 다음과 같은 문제가 있었습니다:

1. **데이터베이스 저장 로직 부재**: 메타데이터 수집 후 데이터베이스에 저장하는 로직이 없음
2. **새로운 CRUD 패턴 미적용**: 새로 구현한 CRUD 패턴을 활용하지 않음
3. **스키마 검증 미적용**: Pydantic 스키마를 통한 데이터 검증이 이루어지지 않음
4. **실행 자동화 부재**: 메타데이터 수집 및 저장 과정을 자동화하는 스크립트 부재

## 해결 전략

다음과 같은 전략으로 문제를 해결했습니다:

1. **메타데이터 수집 및 저장 스크립트 개발**: 기존 `SearchMetadataCollector`를 활용하여 메타데이터를 수집하고, 새로운 CRUD 패턴을 사용하여 데이터베이스에 저장하는 스크립트 개발
2. **실행 스크립트 개발**: 메타데이터 수집 및 저장 과정을 자동화하는 셸 스크립트 개발
3. **오류 처리 강화**: 수집 및 저장 과정에서 발생할 수 있는 오류를 처리하는 로직 추가
4. **로깅 개선**: 수집 및 저장 과정을 모니터링할 수 있는 로깅 기능 강화

## 구현 세부사항

### 1. 메타데이터 수집 및 저장 스크립트

`scripts/collect_and_store_metadata.py` 파일을 생성하여 메타데이터 수집 및 저장 로직을 구현했습니다:

```python
"""
Script to collect metadata and store it in the database using the new database components.
"""

import asyncio
import logging
from datetime import datetime
import pytz

from sqlalchemy.ext.asyncio import AsyncSession

from news_collector.collectors.search_metadata_collector import SearchMetadataCollector
from news_storage.src.deps import get_db
from news_storage.src.crud.article import article
from news_storage.src.schemas.article import ArticleCreate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')


async def collect_and_store_metadata(keyword: str, max_articles: int = 10):
    """
    Collect metadata using SearchMetadataCollector and store it in the database.
    
    Args:
        keyword: Search keyword
        max_articles: Maximum number of articles to collect
    """
    logger.info(f"Starting metadata collection for keyword: {keyword}")
    
    # Initialize collector
    collector = SearchMetadataCollector()
    
    try:
        # Collect metadata
        logger.info("Collecting metadata...")
        metadata_results = await collector.collect(
            keyword=keyword,
            max_articles=max_articles
        )
        
        logger.info(f"Collected {len(metadata_results)} articles")
        
        # Get database session
        async for db in get_db():
            # Store metadata in database
            await store_metadata_in_db(db, metadata_results, keyword)
            break
            
        logger.info("Metadata collection and storage completed successfully")
        
    except Exception as e:
        logger.error(f"Error collecting or storing metadata: {e}")
        raise
    finally:
        # Cleanup collector resources
        await collector.cleanup()


async def store_metadata_in_db(db: AsyncSession, metadata_results: list, keyword: str):
    """
    Store metadata in the database using the new CRUD operations.
    
    Args:
        db: Database session
        metadata_results: List of metadata results
        keyword: Search keyword
    """
    logger.info(f"Storing {len(metadata_results)} articles in database")
    
    stored_count = 0
    
    for item in metadata_results:
        try:
            # Convert metadata to ArticleCreate schema
            article_data = {
                'main_keyword': keyword,
                'naver_link': item.get('link', ''),
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'publisher': item.get('press', ''),
                'published_at': None,  # Will be parsed from published_at string
                'published_date': item.get('published_at', ''),
                'collected_at': datetime.now(KST),
                'is_naver_news': True,
                'is_test': False,
                'is_api_collection': False
            }
            
            # Create article schema
            article_in = ArticleCreate(**article_data)
            
            # Store in database using upsert
            db_article = await article.create_with_upsert(db, obj_in=article_in)
            
            stored_count += 1
            
        except Exception as e:
            logger.error(f"Error storing article: {e}")
            logger.error(f"Article data: {item}")
            continue
    
    logger.info(f"Successfully stored {stored_count} articles in database")


async def main():
    """Main function."""
    # Example usage
    keyword = "인공지능"
    max_articles = 20
    
    await collect_and_store_metadata(keyword, max_articles)


if __name__ == "__main__":
    asyncio.run(main())
```

### 2. 실행 스크립트

`scripts/run_metadata_collection.sh` 파일을 생성하여 메타데이터 수집 및 저장 과정을 자동화했습니다:

```bash
#!/bin/bash
# Script to run metadata collection and storage

set -e  # Exit on error

echo "Running metadata collection and storage..."

# Check if the database template changes have been applied
if [ ! -f "news_storage/src/database.py.bak" ]; then
    echo "Applying database template changes first..."
    
    # Make sure the script is executable
    chmod +x news_storage/scripts/apply_template_changes.sh
    
    # Run the script
    ./news_storage/scripts/apply_template_changes.sh || {
        echo "Error applying database template changes"
        exit 1
    }
    
    echo "Applying database migrations..."
    alembic upgrade head || {
        echo "Error applying database migrations"
        exit 1
    }
else
    echo "Database template changes already applied"
fi

# Run the metadata collection script
echo "Collecting and storing metadata..."
python scripts/collect_and_store_metadata.py

echo "Metadata collection and storage completed!"
```

### 3. 오류 처리 및 로깅

메타데이터 수집 및 저장 과정에서 발생할 수 있는 오류를 처리하고, 로깅을 강화했습니다:

1. **예외 처리**: 각 단계별로 try-except 블록을 사용하여 예외 처리
2. **로깅 레벨 조정**: 중요한 정보는 INFO 레벨, 오류는 ERROR 레벨로 로깅
3. **컨텍스트 정보 포함**: 로그 메시지에 컨텍스트 정보(키워드, 수집된 기사 수 등) 포함
4. **리소스 정리**: finally 블록을 사용하여 리소스 정리 보장

### 4. 스키마 검증

Pydantic 스키마를 사용하여 데이터 검증을 수행했습니다:

```python
# Create article schema
article_in = ArticleCreate(**article_data)
```

이를 통해 다음과 같은 검증이 자동으로 이루어집니다:
- 필수 필드 존재 여부 확인
- 필드 타입 검증
- 기본값 적용

## 기술적 고려사항

### 1. 비동기 프로그래밍

메타데이터 수집 및 저장 과정에서 비동기 프로그래밍을 활용했습니다:

- `async/await` 구문을 사용하여 I/O 바운드 작업의 효율성 향상
- 비동기 세션 관리를 통한 데이터베이스 연결 최적화
- 비동기 컨텍스트 관리자를 활용한 리소스 관리

### 2. 데이터 매핑

수집된 메타데이터를 데이터베이스 모델에 매핑하는 과정에서 다음 사항을 고려했습니다:

- 필드명 차이 해결 (예: `press` → `publisher`)
- 날짜/시간 형식 변환
- 누락된 필드에 대한 기본값 설정

### 3. 트랜잭션 관리

데이터베이스 작업 중 일관성을 유지하기 위해 트랜잭션 관리를 고려했습니다:

- 세션 컨텍스트 관리자를 통한 자동 커밋/롤백
- 개별 항목 저장 실패 시 다른 항목에 영향을 주지 않도록 설계

### 4. 확장성

향후 확장을 고려한 설계를 적용했습니다:

- 키워드 및 최대 기사 수를 매개변수로 받아 다양한 검색 조건 지원
- 모듈화된 함수 구조로 재사용성 향상
- 로깅 및 오류 처리 패턴 표준화

## 다음 단계

1. **검색 키워드 자동화**: 여러 키워드에 대한 메타데이터 수집을 자동화하는 기능 추가
2. **스케줄링 구현**: 주기적인 메타데이터 수집을 위한 스케줄링 기능 구현
3. **병렬 처리 최적화**: 여러 키워드에 대한 병렬 수집 및 저장 기능 구현
4. **모니터링 개선**: 수집 및 저장 과정을 모니터링할 수 있는 대시보드 구현

## 참고 자료

- [asyncio 공식 문서](https://docs.python.org/3/library/asyncio.html)
- [SQLAlchemy 비동기 지원](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
- [Pydantic 데이터 검증](https://docs.pydantic.dev/latest/usage/models/)
- [Python 로깅 가이드](https://docs.python.org/3/howto/logging.html)
