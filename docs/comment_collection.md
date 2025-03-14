# 댓글 수집 및 저장 기능

이 문서는 네이버 뉴스 댓글 수집 및 데이터베이스 저장 기능에 대한 설명입니다.

## 개요

댓글 수집기는 네이버 뉴스 기사의 댓글을 수집하고 데이터베이스에 저장하는 기능을 제공합니다. 이 기능은 기존의 메타데이터 수집 및 저장 로직과 유사한 방식으로 동작합니다.

## 주요 기능

1. 네이버 뉴스 기사 URL에서 댓글 수집
2. 수집된 댓글을 데이터베이스에 저장
3. 댓글 통계 정보 수집 (선택적)
4. 에러 처리 및 재시도 메커니즘

## 사용 방법

### 1. 기사가 이미 DB에 있는 경우 (run_comment_collection.sh)

```bash
# 기본 사용법
./scripts/run_comment_collection.sh --article_url "https://n.news.naver.com/mnews/article/001/0014189012"

# 통계 정보 수집 제외
./scripts/run_comment_collection.sh --article_url "https://n.news.naver.com/mnews/article/001/0014189012" --no-stats

# 재시도 횟수 설정
./scripts/run_comment_collection.sh --article_url "https://n.news.naver.com/mnews/article/001/0014189012" --retries 5
```

### 2. 기사가 DB에 없는 경우 (run_article_with_comments.sh)

이 스크립트는 기사 메타데이터를 먼저 DB에 저장한 후 댓글을 수집합니다.

```bash
# 기본 사용법
./scripts/run_article_with_comments.sh --article_url "https://n.news.naver.com/article/056/0011902190"

# 통계 정보 수집 제외
./scripts/run_article_with_comments.sh --article_url "https://n.news.naver.com/article/056/0011902190" --no-stats

# 재시도 횟수 설정
./scripts/run_article_with_comments.sh --article_url "https://n.news.naver.com/article/056/0011902190" --retries 5
```

### 3. Python 코드에서 사용

#### 기사가 이미 DB에 있는 경우

```python
import asyncio
from scripts.collect_and_store_comments import collect_and_store_comments

async def main():
    article_url = "https://n.news.naver.com/mnews/article/001/0014189012"
    result = await collect_and_store_comments(
        article_url=article_url,
        include_stats=True,
        max_retries=3
    )
    
    if result['success']:
        print(f"Successfully collected and stored {result['stored_comments']} comments")
    else:
        print(f"Failed: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
```

#### 기사가 DB에 없는 경우

```python
import asyncio
from scripts.collect_article_with_comments import collect_article_with_comments

async def main():
    article_url = "https://n.news.naver.com/article/056/0011902190"
    result = await collect_article_with_comments(
        article_url=article_url,
        include_stats=True,
        max_retries=3
    )
    
    if result['success']:
        print(f"Successfully collected article and {result['stored_comments']} comments")
        print(f"Article ID: {result['article_id']}")
    else:
        print(f"Failed: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 주의사항

1. `run_comment_collection.sh`를 사용할 경우, 댓글을 수집하기 전에 해당 기사가 데이터베이스에 존재해야 합니다. 기사가 데이터베이스에 없는 경우 댓글 저장이 실패합니다.
2. 기사가 데이터베이스에 없는 경우, `run_article_with_comments.sh`를 사용하여 기사 메타데이터와 댓글을 함께 수집하는 것이 좋습니다.
3. 또는 먼저 메타데이터 수집 스크립트를 실행하여 기사를 데이터베이스에 추가한 후 댓글을 수집할 수도 있습니다.

```bash
# 메타데이터 수집 예시
./scripts/run_metadata_collection.sh --keyword "인공지능" --max_articles 10
```

## 테스트

테스트 스크립트를 사용하여 댓글 수집 및 저장 기능을 테스트할 수 있습니다.

```bash
python scripts/test_comment_collection.py
```

이 스크립트는 두 가지 테스트 옵션을 제공합니다:
1. 기존 기사에서 댓글 수집 및 저장
2. 새 기사에서 댓글 수집 및 저장 (기사가 데이터베이스에 없는 경우 실패 예상)

## 구현 세부사항

### 주요 구성 요소

1. `CommentCollector` 클래스: 네이버 뉴스 기사에서 댓글을 수집하는 클래스
2. `collect_and_store_comments.py`: 댓글 수집 및 저장 로직을 구현한 스크립트
3. `run_comment_collection.sh`: 명령줄에서 댓글 수집 스크립트를 실행하는 셸 스크립트
4. `collect_article_with_comments.py`: 기사 메타데이터와 댓글을 함께 수집하는 스크립트
5. `run_article_with_comments.sh`: 기사 메타데이터와 댓글 수집 스크립트를 실행하는 셸 스크립트

### 데이터베이스 통합

댓글 수집기는 다음과 같은 방식으로 데이터베이스와 통합됩니다:

1. 기사 URL을 사용하여 데이터베이스에서 기사 ID를 조회
2. 수집된 댓글을 `CommentCreate` 스키마로 변환
3. `comment.batch_create` 함수를 사용하여 댓글을 데이터베이스에 일괄 저장

### 에러 처리

댓글 수집 과정에서 발생할 수 있는 다양한 에러를 처리합니다:

1. 네트워크 오류: 재시도 메커니즘을 통해 처리
2. 기사 없음: 적절한 에러 메시지 반환 또는 자동으로 기사 메타데이터 생성
3. 데이터베이스 오류: 로깅 및 예외 처리

## 향후 개선 사항

1. 여러 기사의 댓글을 한 번에 수집하는 기능 추가
2. 정기적인 댓글 수집을 위한 스케줄링 기능 구현
3. 수집된 댓글에 대한 분석 기능 추가
