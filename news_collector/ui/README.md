# CommentWatch Dashboard

## Overview

CommentWatch의 대시보드는 뉴스 기사와 댓글 수집을 관리하고 모니터링하는 웹 인터페이스를 제공합니다.

## Directory Structure

```
dashboard/
├── __init__.py           # Package initialization
├── app.py               # Main application entry point
├── ui.py                # Streamlit UI components
├── collection_service.py # Data collection service
├── decorators.py        # Utility decorators
├── exceptions.py        # Custom exceptions
├── logging_config.py    # Logging configuration
├── validators.py        # Data validation
└── visualization.py     # Data visualization
```

## 데이터 흐름

### 1. 기사 수집 프로세스

```
UI (ui.py)
  ↓
수집 요청 (collection_service.py)
  ↓
수집기 실행 (news_collector)
  ↓
데이터 검증 (validators.py)
  ↓
DB 저장 (database)
```

#### 데이터 매핑

수집된 데이터는 검증 후 다음과 같이 DB에 매핑됩니다:

```python
# 수집기 결과
{
    'title': str,          # → articles.title
    'naver_link': str,     # → articles.naver_link
    'original_link': str,  # → articles.original_link
    'description': str,    # → articles.description
    'publisher': str,      # → articles.publisher
    'pub_date': str,       # → articles.pub_date (YYYY-MM-DD)
    'collected_at': str,   # → articles.collected_at
    'main_keyword': str,   # → articles.main_keyword
    'status': str         # → articles.content_status
}
```

### 2. 댓글 수집 프로세스

```
UI (ui.py)
  ↓
댓글 수집 요청 (collection_service.py)
  ↓
댓글 수집기 실행 (news_collector)
  ↓
데이터 검증 (validators.py)
  ↓
DB 저장 (database)
```

## 주요 컴포넌트

### 1. Collection Service (collection_service.py)

- **collect_articles_parallel**: 병렬 기사 수집

  ```python
  def collect_articles_parallel(
      keyword: str,
      start_date: datetime,
      end_date: datetime,
      num_processes: int = 4,
      collect_content: bool = True
  ) -> Tuple[int, int]
  ```

- **collect_comments_parallel**: 병렬 댓글 수집
  ```python
  def collect_comments_parallel(
      articles: List[Article],
      max_workers: int = 4
  ) -> int
  ```

### 2. Validators (validators.py)

수집된 데이터 검증 규칙:

```python
# 기사 데이터 필수 필드
required_fields = {
    'title': '제목',
    'naver_link': '네이버 링크',
    'main_keyword': '검색 키워드',
    'pub_date': '발행 날짜'
}

# 댓글 데이터 필수 필드
comment_fields = {
    'article_id': '기사 ID',
    'content': '내용',
    'timestamp': '작성 시간'
}
```

### 3. UI Components (ui.py)

- 수집 설정 폼
- 진행 상황 표시
- 결과 시각화
- 에러 처리 및 표시

## 사용 예시

### 1. 기사 수집

```python
import streamlit as st
from dashboard.collection_service import collect_articles_parallel

# 수집 설정
keyword = st.text_input("검색어")
start_date = st.date_input("시작일")
end_date = st.date_input("종료일")

if st.button("수집 시작"):
    with st.spinner("기사 수집 중..."):
        success_count, error_count = collect_articles_parallel(
            keyword=keyword,
            start_date=start_date,
            end_date=end_date
        )
    st.success(f"수집 완료: 성공 {success_count}건, 실패 {error_count}건")
```

### 2. 댓글 수집

```python
from dashboard.collection_service import collect_comments_parallel

# 기사 선택
selected_articles = st.multiselect("기사 선택", articles)

if st.button("댓글 수집"):
    with st.spinner("댓글 수집 중..."):
        comment_count = collect_comments_parallel(selected_articles)
    st.success(f"댓글 {comment_count}개 수집 완료")
```

## 에러 처리

1. **ValidationError**: 데이터 검증 실패

   ```python
   try:
       validate_article_data(article)
   except ValidationError as e:
       st.error(f"데이터 검증 실패: {str(e)}")
   ```

2. **CollectionError**: 수집 과정 오류
   ```python
   try:
       collect_articles_parallel(...)
   except CollectionError as e:
       st.error(f"수집 실패: {str(e)}")
   ```

## 로깅

- 수집 과정 로깅
- 에러 추적
- 성능 모니터링

```python
logger = get_logger('collectors')
logger.info("수집 시작: %s", keyword)
logger.error("수집 실패: %s", error_message)
```

## 성능 최적화

1. **병렬 처리**

   - 멀티프로세스 기사 수집
   - 멀티스레드 댓글 수집

2. **배치 처리**

   - 대량 데이터 일괄 저장
   - 메모리 사용 최적화

3. **캐싱**
   - 중복 요청 방지
   - 응답 시간 개선
