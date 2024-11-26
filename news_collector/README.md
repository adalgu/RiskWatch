# News Collector

뉴스 기사의 메타데이터, 본문, 댓글을 수집하는 비동기 수집기 모듈입니다.

## 주요 기능

- 메타데이터 수집 (API/검색 방식)
- 본문 수집 (서브헤딩, 이미지 포함)
- 댓글 수집 (통계 포함)
- 병렬 수집 지원

## 설치

```bash
pip install -e .
```

## 수집기 스펙

### 1. MetadataCollector

메타데이터 수집기는 두 가지 방식을 지원합니다:

#### API 방식

```python
collector = MetadataCollector()
result = await collector.collect(
    method='api',
    keyword='검색어',
    max_articles=10
)
```

**결과 형식:**

```python
{
    'articles': [{
        'title': str,
        'naver_link': str,
        'original_link': str,
        'description': str,
        'publisher': str,
        'publisher_domain': str,
        'published_at': str,      # ISO format with timezone (e.g., "2024-03-20T14:30:00+09:00")
        'published_date': str,    # YYYY.MM.DD format (e.g., "2024.03.20")
        'collected_at': str,      # ISO format with timezone
        'is_naver_news': bool
    }],
    'collected_at': str,          # ISO format with timezone
    'metadata': {
        'method': str,
        'total_collected': int,
        'keyword': str
    }
}
```

#### 검색 방식

```python
collector = MetadataCollector()
result = await collector.collect(
    method='search',
    keyword='검색어',
    start_date='2024-01-01',  # Optional
    end_date='2024-01-31',    # Optional
    max_articles=10
)
```

**날짜 처리:**

- 5주 이내 기사: 일별 역순 수집
- 5주 이전 기사: 절대 날짜 추출

### 2. ContentCollector

기사 본문과 관련 정보를 수집합니다.

```python
collector = ContentCollector()
result = await collector.collect(
    article_url='https://n.news.naver.com/article/001/0012345678'
)
```

**결과 형식:**

```python
{
    'content': {
        'title': str,
        'subheadings': List[str],     # strong 태그 내용
        'content': str,               # 본문 텍스트
        'reporter': str,
        'media': str,
        'published_at': str,          # ISO format with timezone
        'modified_at': str,           # ISO format with timezone
        'category': str,              # 언론사 분류 (e.g., "경제")
        'images': [{
            'url': str,
            'caption': str,           # 이미지 설명
            'alt': str                # 대체 텍스트
        }],
        'collected_at': str           # ISO format with timezone
    },
    'metadata': {
        'url': str,
        'success': bool
    }
}
```

### 3. CommentCollector

댓글과 통계 정보를 수집합니다.

```python
collector = CommentCollector()
result = await collector.collect(
    article_url='https://n.news.naver.com/article/001/0012345678',
    include_stats=True
)
```

**결과 형식:**

```python
{
    'total_count': int,           # 전체 댓글 수 (u_cbox_count 태그 기준)
    'published_at': str,          # 기사 발행 시간 (ISO format with timezone)
    'stats': {
        'current_count': int,
        'user_deleted_count': int,
        'admin_deleted_count': int,
        'gender_ratio': {
            'male': int,          # 백분율
            'female': int         # 백분율
        },
        'age_distribution': {     # 각 연령대별 백분율
            '10s': int,
            '20s': int,
            '30s': int,
            '40s': int,
            '50s': int,
            '60s_above': int
        }
    },
    'collected_at': str,          # ISO format with timezone
    'comments': [{
        'comment_no': str,
        'parent_comment_no': str, # 답글인 경우 부모 댓글 번호
        'content': str,
        'author': str,
        'profile_url': str,
        'timestamp': str,         # ISO format with timezone
        'likes': int,
        'dislikes': int,
        'reply_count': int,
        'is_reply': bool,
        'is_deleted': bool,
        'delete_type': str,       # 'user' or 'admin' or None
        'collected_at': str       # ISO format with timezone
    }]
}
```

### 4. 병렬 수집

대량의 기사를 효율적으로 수집하기 위한 병렬 처리를 지원합니다.

```python
collector = ParallelMetadataCollector(num_processes=4)
results = await collector.collect_metadata_bulk(
    method='api',
    keywords=['키워드1', '키워드2', '키워드3'],
    max_articles=100
)
```

## 명령줄 실행

각 수집기는 명령줄에서 직접 실행할 수 있습니다:

### 메타데이터 수집

```bash
# API 방식
python -m news_system.news_collector.collectors.metadata --method api --keyword "검색어" --max_articles 10

# 검색 방식
python -m news_system.news_collector.collectors.metadata --method search --keyword "검색어" --start_date 2024-01-01 --end_date 2024-01-31 --max_articles 50
```

### 본문 수집

```bash
python -m news_system.news_collector.collectors.content --article_url "https://n.news.naver.com/article/001/0012345678"
```

### 댓글 수집

```bash
python -m news_system.news_collector.collectors.comments --article_url "https://n.news.naver.com/article/001/0012345678"
python -m news_system.news_collector.collectors.comments --article_url "https://n.news.naver.com/article/001/0012345678" --no-stats
```

## 타임스탬프 처리

모든 시간 정보는 다음과 같이 표준화되어 있습니다:

1. **published_at**: ISO format with timezone

   - 예: "2024-03-20T14:30:00+09:00"
   - API 수집: API 응답의 pubDate 파싱
   - 검색 수집: 댓글 수집 시 업데이트 가능

2. **published_date**: YYYY.MM.DD format

   - 예: "2024.03.20"
   - 검색 수집 시 사용
   - 정확한 시간 정보가 없는 경우 사용

3. **collected_at**: ISO format with timezone
   - 수집 시점을 나타냄
   - 모든 수집 결과에 포함

## 다른 모듈과의 연동

### 1. News Analyzer (예정)

- 수집된 데이터의 키워드 분석
- 감성 분석
- 토픽 모델링

### 2. News Storage (예정)

- 수집 데이터의 영구 저장
- 메타데이터 업데이트 지원
- 캐싱 시스템

### 3. News Visualizer (예정)

- 수집 데이터 시각화
- 트렌드 분석
- 대시보드 지원

## 개발 환경

- Python >= 3.8
- 비동기 지원 (asyncio)
- Type hints 사용
- 테스트 커버리지 관리

## 테스트

```bash
pytest tests/
```

## 라이센스

MIT License
