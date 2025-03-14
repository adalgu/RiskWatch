# 댓글 수집 및 데이터베이스 저장 기능 구현

- **날짜**: 2025-02-28
- **작성자**: Gunn Kim
- **관련 이슈**: N/A
- **이전 로그**: 
  - [메타데이터 수집 및 저장 스크립트 구현](./2025-02-28-003-feature-metadata-collection-script.md)
  - [Full Stack FastAPI Template 데이터베이스 컴포넌트 통합](./2025-02-28-002-refactor-database-template-integration.md)

## 문제 상황

메타데이터 수집 및 저장 기능을 성공적으로 구현한 후, 네이버 뉴스 댓글을 수집하고 데이터베이스에 저장하는 기능이 필요했습니다. 기존의 댓글 수집 로직은 있었지만, 새로운 데이터베이스 컴포넌트와 통합되지 않아 다음과 같은 문제가 있었습니다:

1. **데이터베이스 저장 로직 부재**: 댓글 수집 후 데이터베이스에 저장하는 로직이 없음
2. **새로운 CRUD 패턴 미적용**: 새로 구현한 CRUD 패턴을 활용하지 않음
3. **기사 연결 로직 부재**: 수집된 댓글을 해당 기사와 연결하는 로직이 없음
4. **실행 자동화 부재**: 댓글 수집 및 저장 과정을 자동화하는 스크립트 부재

## 해결 전략

다음과 같은 전략으로 문제를 해결했습니다:

1. **댓글 수집 및 저장 스크립트 개발**: 기존 `CommentCollector`를 활용하여 댓글을 수집하고, 새로운 CRUD 패턴을 사용하여 데이터베이스에 저장하는 스크립트 개발
2. **기사 및 댓글 통합 수집 스크립트 개발**: 기사가 데이터베이스에 없는 경우 기사 메타데이터를 먼저 생성한 후 댓글을 수집하는 스크립트 개발
3. **실행 스크립트 개발**: 댓글 수집 및 저장 과정을 자동화하는 셸 스크립트 개발
4. **오류 처리 강화**: 수집 및 저장 과정에서 발생할 수 있는 오류를 처리하는 로직 추가
5. **데이터베이스 스키마 호환성 확보**: 모델 및 스키마를 데이터베이스 구조에 맞게 조정

## 구현 세부사항

### 1. 댓글 수집 및 저장 스크립트

`scripts/collect_and_store_comments.py` 파일을 생성하여 댓글 수집 및 저장 로직을 구현했습니다:

```python
async def collect_and_store_comments(article_url: str, include_stats: bool = True, max_retries: int = 3) -> Dict[str, Any]:
    """
    Collect comments from an article and store them in the database.
    
    Args:
        article_url: URL of the article
        include_stats: Whether to collect statistics
        max_retries: Maximum number of retries for collection
        
    Returns:
        Dictionary with collection results
    """
    logger.info(f"Starting comment collection for article: {article_url}")
    
    # Initialize collector
    collector = CommentCollector()
    
    result = {
        'success': False,
        'article_url': article_url,
        'article_id': None,
        'total_comments': 0,
        'stored_comments': 0,
        'error': None
    }
    
    try:
        # Collect comments with retries
        retry_count = 0
        collection_result = None
        
        while retry_count < max_retries:
            try:
                logger.info(f"Collecting comments (attempt {retry_count + 1}/{max_retries})...")
                collection_result = await collector.collect(
                    article_url=article_url,
                    include_stats=include_stats
                )
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                logger.warning(f"Collection attempt failed: {e}. Retrying...")
                await asyncio.sleep(2)
        
        if not collection_result:
            raise Exception("Failed to collect comments after multiple attempts")
        
        logger.info(f"Collected {len(collection_result['comments'])} comments")
        result['total_comments'] = len(collection_result['comments'])
        
        # Get article from database
        article_found = False
        async for db in get_db():
            db_article = await get_article_by_url(db, article_url)
            if db_article:
                article_found = True
                result['article_id'] = db_article.id
                
                # Store comments in database
                stored_count = await store_comments_in_db(
                    db, 
                    db_article.id, 
                    collection_result['comments']
                )
                result['stored_comments'] = stored_count
                break
        
        if not article_found:
            result['error'] = f"Article not found in database: {article_url}"
            logger.error(result['error'])
        else:
            result['success'] = True
            logger.info(f"Comment collection and storage completed successfully")
        
    except Exception as e:
        error_msg = f"Error collecting or storing comments: {str(e)}"
        logger.error(error_msg)
        result['error'] = error_msg
    finally:
        # Cleanup collector resources
        await collector.cleanup()
    
    return result
```

### 2. 기사 및 댓글 통합 수집 스크립트

`scripts/collect_article_with_comments.py` 파일을 생성하여 기사 메타데이터 생성 및 댓글 수집을 통합하는 로직을 구현했습니다:

```python
async def collect_article_with_comments(article_url: str, include_stats: bool = True, max_retries: int = 3) -> Dict[str, Any]:
    """
    Collect metadata for a specific article URL and then collect comments for it.
    
    Args:
        article_url: URL of the article
        include_stats: Whether to collect comment statistics
        max_retries: Maximum number of retries for collection
        
    Returns:
        Dictionary with collection results
    """
    result = {
        'success': False,
        'article_url': article_url,
        'article_id': None,
        'metadata_collected': False,
        'comments_collected': False,
        'total_comments': 0,
        'stored_comments': 0,
        'error': None
    }
    
    try:
        # Step 1: Collect and store article metadata
        article_id = await collect_and_store_article_metadata(article_url)
        
        if not article_id:
            result['error'] = "Failed to collect and store article metadata"
            return result
        
        result['article_id'] = article_id
        result['metadata_collected'] = True
        
        # Step 2: Collect and store comments
        comments_result = await collect_and_store_comments(
            article_url=article_url,
            include_stats=include_stats,
            max_retries=max_retries
        )
        
        result['comments_collected'] = comments_result['success']
        result['total_comments'] = comments_result['total_comments']
        result['stored_comments'] = comments_result['stored_comments']
        
        if not comments_result['success']:
            result['error'] = comments_result['error']
            return result
        
        result['success'] = True
        
    except Exception as e:
        error_msg = f"Error in collect_article_with_comments: {str(e)}"
        logger.error(error_msg)
        result['error'] = error_msg
    
    return result
```

### 3. 실행 스크립트

댓글 수집 및 저장 과정을 자동화하는 셸 스크립트를 구현했습니다:

1. `scripts/run_comment_collection.sh`: 기사가 이미 데이터베이스에 있는 경우 사용
2. `scripts/run_article_with_comments.sh`: 기사가 데이터베이스에 없는 경우 사용

```bash
#!/bin/bash
# Script to run comment collection for a given article URL

# Default values
ARTICLE_URL=""
NO_STATS=false
RETRIES=3

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --article_url)
      ARTICLE_URL="$2"
      shift 2
      ;;
    --no-stats)
      NO_STATS=true
      shift
      ;;
    --retries)
      RETRIES="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check if article URL is provided
if [ -z "$ARTICLE_URL" ]; then
  echo "Error: Article URL is required"
  echo "Usage: $0 --article_url <URL> [--no-stats] [--retries <number>]"
  exit 1
fi

# Build command
CMD="python scripts/collect_and_store_comments.py --article_url \"$ARTICLE_URL\""

if [ "$NO_STATS" = true ]; then
  CMD="$CMD --no-stats"
fi

CMD="$CMD --retries $RETRIES"

# Run the command
echo "Running: $CMD"
eval $CMD
```

### 4. 데이터베이스 스키마 호환성 확보

데이터베이스 스키마와 모델 및 스키마 간의 호환성을 확보하기 위해 다음과 같은 수정을 진행했습니다:

1. **Pydantic 호환성 문제 해결**: `model_dump()` 대신 `dict()`를 사용하여 Pydantic v1.x와의 호환성 유지
2. **데이터베이스 스키마 불일치 해결**: 데이터베이스 테이블에 존재하지 않는 필드 제거
   - `profile_url` 필드 제거
   - `likes`, `dislikes`, `reply_count` 필드 제거

```python
# 모델 수정 예시
class Comment(SQLModel, table=True):
    __tablename__ = "comments"
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id")
    comment_no: Optional[str] = None
    parent_comment_no: Optional[str] = None
    content: Optional[str] = None
    username: Optional[str] = None
    # Removed profile_url as it's not in the database schema
    timestamp: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Timestamp of the comment"
    )
    collected_at: datetime = Field(
        default_factory=get_kst_now,
        sa_column=Column(DateTime(timezone=True))
    )
    # Removed likes, dislikes, and reply_count as they're not in the database schema
    is_reply: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    delete_type: Optional[str] = None
```

## 기술적 고려사항

### 1. 비동기 프로그래밍

댓글 수집 및 저장 과정에서 비동기 프로그래밍을 활용했습니다:

- `async/await` 구문을 사용하여 I/O 바운드 작업의 효율성 향상
- 비동기 세션 관리를 통한 데이터베이스 연결 최적화
- 비동기 컨텍스트 관리자를 활용한 리소스 관리

### 2. 데이터 매핑

수집된 댓글을 데이터베이스 모델에 매핑하는 과정에서 다음 사항을 고려했습니다:

- 필드명 차이 해결
- 날짜/시간 형식 변환
- 누락된 필드에 대한 기본값 설정
- 데이터베이스 스키마와의 호환성 확보

### 3. 오류 처리 및 재시도 메커니즘

댓글 수집 과정에서 발생할 수 있는 오류를 처리하고, 재시도 메커니즘을 구현했습니다:

- 네트워크 오류, 타임아웃 등에 대한 재시도 로직
- 최대 재시도 횟수 설정
- 재시도 간 지연 시간 설정

### 4. 확장성

향후 확장을 고려한 설계를 적용했습니다:

- 모듈화된 함수 구조로 재사용성 향상
- 로깅 및 오류 처리 패턴 표준화
- 다양한 사용 시나리오 지원 (기사가 이미 DB에 있는 경우, 없는 경우)

## 다음 단계

1. **정기적인 댓글 수집 자동화**: 최근 기사에 대한 댓글을 정기적으로 수집하는 스케줄링 기능 구현
2. **다중 기사 처리**: 여러 기사의 댓글을 한 번에 수집하는 기능 구현
3. **댓글 분석 기능**: 수집된 댓글에 대한 분석 기능 구현 (감정 분석, 키워드 추출 등)
4. **모니터링 개선**: 댓글 수집 및 저장 과정을 모니터링할 수 있는 대시보드 구현

## 참고 자료

- [asyncio 공식 문서](https://docs.python.org/3/library/asyncio.html)
- [SQLAlchemy 비동기 지원](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
- [Pydantic 데이터 검증](https://docs.pydantic.dev/latest/usage/models/)
- [Python 로깅 가이드](https://docs.python.org/3/howto/logging.html)
