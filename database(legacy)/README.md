# CommentWatch Database Structure

## Overview

CommentWatch의 데이터베이스는 뉴스 기사와 댓글을 수집하고 분석하기 위한 구조로 설계되어 있습니다.
데이터베이스는 크게 핵심 모델(Core Models)과 분석 모델(Analysis Models)로 구분됩니다.

## Directory Structure

```
database/
├── __init__.py          # Package initialization and exports
├── config.py            # Database configuration and setup
├── enums.py            # Shared enumerations
├── operations.py       # Database operations class
└── models/             # Database models
    ├── article.py      # Article and related models
    ├── comment.py      # Comment model
    ├── sentiment/      # Sentiment analysis models
    │   ├── article_sentiment.py
    │   └── comment_sentiment.py
    ├── keyword/        # Keyword analysis models
    │   ├── article_keywords.py
    │   └── comment_keywords.py
    └── stats/          # Statistical analysis models
        ├── article_stats.py
        └── comment_stats.py
```

## Core Models

### Article 관련 모델

#### Article 테이블 스키마와 수집기 매핑

```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY,
    title STRING,              -- NewsSearchCollector: title
    naver_link STRING,         -- NewsSearchCollector: naver_link
    original_link STRING,      -- NewsSearchCollector: original_link
    description TEXT,          -- NewsSearchCollector: description
    publisher STRING,          -- NewsSearchCollector: publisher
    publisher_domain STRING,   -- APICollector: publisher_domain
    pub_date DATE,            -- NewsSearchCollector: pub_date (YYYY-MM-DD)
    published_at TIMESTAMP,    -- ContentCollector: published_at
    main_keyword STRING,       -- NewsSearchCollector: main_keyword
    collection_method ENUM,    -- 수집 방법 (API/SEARCH)
    content_status ENUM,       -- 본문 수집 상태
    comment_status ENUM,       -- 댓글 수집 상태
    created_at TIMESTAMP,      -- 메타데이터 수집 시간
    collected_at TIMESTAMP,    -- 본문 수집 시간
    comment_collected_at TIMESTAMP,  -- 댓글 수집 시간
    last_updated_at TIMESTAMP       -- 마지막 업데이트 시간
);
```

- **Article**: 뉴스 기사의 기본 정보

  - 수집기별 필드 매핑:
    - NewsSearchCollector: 기본 메타데이터 (title, naver_link, original_link, description, publisher, pub_date)
    - NewsContentCollector: 상세 정보 (content, reporter, category, published_at)
    - APICollector: API 관련 정보 (publisher_domain, api_id)

- **ArticleCollectionLog**: 기사 수집 이력

  ```sql
  CREATE TABLE article_collection_logs (
      id INTEGER PRIMARY KEY,
      keyword STRING,          -- 검색 키워드
      start_date DATE,         -- 검색 시작일
      end_date DATE,           -- 검색 종료일
      total_articles INTEGER,  -- 총 수집 기사 수
      success_count INTEGER,   -- 성공 건수
      error_count INTEGER,     -- 실패 건수
      error_message TEXT,      -- 오류 메시지
      collected_at TIMESTAMP   -- 수집 시간
  );
  ```

- **ArticleMapping**: 기사-키워드 매핑
  ```sql
  CREATE TABLE article_mappings (
      id INTEGER PRIMARY KEY,
      article_id INTEGER,      -- 기사 ID
      main_keyword STRING,     -- 메인 키워드
      sub_keyword STRING,      -- 서브 키워드
      collection_method ENUM,  -- 수집 방법
      subset_size INTEGER,     -- 서브셋 크기
      overlap_count INTEGER,   -- 중복 수
      created_at TIMESTAMP     -- 생성 시간
  );
  ```

### Comment 모델

```sql
CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    article_id INTEGER,        -- NaverCommentCollector: article_id
    content TEXT,              -- NaverCommentCollector: content
    writer STRING,             -- NaverCommentCollector: writer
    timestamp TIMESTAMP,       -- NaverCommentCollector: timestamp
    likes INTEGER,             -- NaverCommentCollector: likes
    dislikes INTEGER,          -- NaverCommentCollector: dislikes
    parent_id INTEGER,         -- 부모 댓글 ID (대댓글용)
    status STRING,             -- 댓글 상태
    created_at TIMESTAMP       -- 수집 시간
);
```

## Analysis Models

### 1. Sentiment Analysis (감성분석)

- **ArticleSentiment**: 기사 감성분석

  - 전체 감성 점수 및 카테고리
  - 제목/본문 별도 분석
  - 신뢰도 점수
  - 분석 메타데이터

- **CommentSentiment**: 댓글 감성분석
  - 감성 점수 및 카테고리
  - 세부 감정 분석 (분노, 기쁨 등)
  - 맥락 관련성
  - 스팸/공격성 탐지

### 2. Keyword Analysis (키워드 분석)

- **ArticleKeywordAnalysis**: 기사 키워드 분석

  - 추출 키워드 및 가중치
  - 토픽 모델링 결과
  - 개체명 인식 (NER)
  - 시간별 키워드 트렌드

- **CommentKeywordAnalysis**: 댓글 키워드 분석
  - 키워드 추출
  - 의견/논쟁점 분석
  - 사용자 입장 분석
  - 맥락 관련성

### 3. Statistical Analysis (통계 분석)

- **ArticleStats**: 기사 통계

  - 조회수/참여도 지표
  - 트래픽 소스
  - 시간대별 성과
  - 소셜 미디어 지표

- **CommentStats**: 댓글 통계
  - 댓글 수 추이
  - 인구통계 분석
  - 시간대별 분포
  - 사용자 행동 패턴

## 주요 관계도

```
Article
├── comments (1:N) → Comment
├── mappings (1:N) → ArticleMapping
├── sentiment_analysis (1:N) → ArticleSentiment
├── keyword_analysis (1:N) → ArticleKeywordAnalysis
├── article_stats (1:N) → ArticleStats
└── comment_stats (1:N) → CommentStats

Comment
├── sentiment_analysis (1:N) → CommentSentiment
└── keyword_analysis (1:N) → CommentKeywordAnalysis
```

## 설계 원칙

1. **모듈성**: 각 분석 유형별로 독립적인 모델을 구성하여 유지보수와 확장이 용이하도록 설계

2. **확장성**:

   - 각 모델에 메타데이터 필드 포함
   - 분석 버전 관리 지원
   - 향후 새로운 분석 지표 추가 가능

3. **추적성**:

   - 모든 모델에 시간 정보 포함
   - 수집/분석 과정의 상태 추적
   - 품질 지표 관리

4. **유연성**:

   - JSON/JSONB 타입을 활용한 동적 데이터 저장
   - Nullable 필드를 통한 선택적 정보 저장
   - 다양한 분석 시나리오 지원

5. **성능**:
   - 적절한 인덱스 설정
   - 배치 처리 지원
   - 효율적인 관계 설정

## 사용 예시

```python
from database import Database, Article, Comment
from database.models.sentiment import ArticleSentiment
from database.models.keyword import ArticleKeywordAnalysis
from database.models.stats import ArticleStats

# Database 인스턴스 생성
db = Database()

# 기사 조회
article = db.get_article_by_url_and_keyword(url, keyword)

# 감성분석 결과 저장
sentiment = ArticleSentiment(
    article_id=article.id,
    sentiment_score=0.8,
    confidence_score=0.9
)
db.session.add(sentiment)

# 키워드 분석 결과 저장
keywords = ArticleKeywordAnalysis(
    article_id=article.id,
    extracted_keywords={"경제": 0.8, "정책": 0.6}
)
db.session.add(keywords)

# 통계 정보 업데이트
stats = ArticleStats(
    article_id=article.id,
    view_count=1000,
    comment_count=50
)
db.session.add(stats)

db.session.commit()
```
