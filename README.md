# Risk Watch

뉴스 수집 및 저장 시스템은 이벤트 기반 아키텍처를 사용하여 네이버 뉴스 데이터를 수집하고 저장하는 시스템입니다.

## 시스템 아키텍처

### 주요 컴포넌트

1. **News Collector**

   - 네이버 뉴스 데이터 수집
   - API 및 웹 검색 방식 지원
   - RabbitMQ로 메시지 발행

2. **News Storage**

   - PostgreSQL 데이터베이스 관리
   - RabbitMQ 메시지 소비
   - 비동기 데이터 처리

3. **Message Broker (RabbitMQ)**
   - 컴포넌트 간 메시지 전달
   - 비동기 통신 지원
   - 메시지 영속성 보장

### 데이터 흐름

```mermaid
graph LR
    A[News Collector] -->|Publish| B[RabbitMQ]
    B -->|Consume| C[News Storage]
    C -->|Store| D[PostgreSQL]
```

1. Collector가 뉴스 데이터 수집
2. RabbitMQ로 메시지 발행
3. Storage가 메시지 소비
4. PostgreSQL에 데이터 저장

## 데이터 수집

### 수집 방식

1. **API 방식**

   - Naver News API 사용
   - 최신 기사 우선 수집
   - 정확한 타임스탬프 제공

2. **검색 방식**
   - 웹 크롤링 기반
   - 날짜 범위 지정 가능
   - 상세 검색 옵션 지원

### 수집 데이터

1. **메타데이터**

   ```json
   {
     "title": "기사 제목",
     "naver_link": "네이버 뉴스 링크",
     "original_link": "언론사 원본 링크",
     "description": "기사 설명",
     "publisher": "언론사명",
     "publisher_domain": "언론사 도메인",
     "published_at": "2024-11-27T06:32:00+09:00",
     "published_date": "2024.11.27",
     "collected_at": "2024-11-27T06:34:35.153563+09:00",
     "is_naver_news": true,
     "main_keyword": "검색 키워드"
   }
   ```

2. **날짜 처리**
   - API: RFC822 형식 → ISO 형식 변환
   - 검색: 상대/절대 날짜 처리
   - 타임존: KST(Asia/Seoul) 사용

## 데이터베이스 구조

### 테이블 구조

1. **articles**

   - id (PK)
   - main_keyword (검색 키워드)
   - naver_link (네이버 뉴스 링크)
   - title (기사 제목)
   - original_link (원본 링크)
   - description (기사 설명)
   - publisher (언론사)
   - publisher_domain (언론사 도메인)
   - published_at (발행 시각)
   - published_date (발행 날짜)
   - collected_at (수집 시각)
   - is_naver_news (네이버 뉴스 여부)

2. **contents**

   - id (PK)
   - article_id (FK)
   - content (기사 본문)
   - published_at (발행 시각)
   - modified_at (수정 시각)
   - collected_at (수집 시각)

3. **comments**

   - id (PK)
   - article_id (FK)
   - comment_no (댓글 번호)
   - username (작성자)
   - content (댓글 내용)
   - timestamp (작성 시각)
   - collected_at (수집 시각)
   - parent_comment_no (부모 댓글 번호)
   - is_reply (답글 여부)

4. **comment_stats**
   - id (PK)
   - comment_id (FK)
   - likes (좋아요 수)
   - dislikes (싫어요 수)
   - collected_at (수집 시각)

### 제약 조건

1. **Unique Constraints**

   - articles: (main_keyword, naver_link)
   - contents: article_id
   - comment_stats: comment_id

2. **Foreign Keys**
   - contents → articles
   - comments → articles
   - comment_stats → comments

## 설치 및 실행

### 필수 요구사항

1. **Docker & Docker Compose**

   - Docker 설치
   - Docker Compose 설치

2. **환경 변수 설정**
   ```bash
   # .env 파일 생성
   DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/news_db
   RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
   NAVER_CLIENT_ID=your_client_id
   NAVER_CLIENT_SECRET=your_client_secret
   ```

### 실행 방법

1. **자동 실행 스크립트 사용**

   ```bash
   # 실행 권한 부여
   chmod +x run_test.sh

   # 테스트 실행
   ./run_test.sh
   ```

   스크립트는 다음 작업을 자동으로 수행합니다:

   - Docker 컨테이너 시작
   - PostgreSQL 준비 상태 확인
   - RabbitMQ 준비 상태 확인
   - 통합 테스트 실행

2. **수동 실행**

   ```bash
   # Docker 컨테이너 시작
   docker compose up -d

   # 테스트 실행
   docker exec -it riskwatch-news_storage-1 python -m scripts.test_event
   ```

### 테스트 실행

```bash
# 메타데이터 수집 테스트
python -m news_collector.collectors.metadata \
  --method search \
  --keyword "삼성전자" \
  --max_articles 5
```

## 주요 기능

1. **실시간 수집**

   - 최신 뉴스 자동 수집
   - 중복 데이터 처리
   - 오류 복구 메커니즘

2. **데이터 정규화**

   - 날짜/시간 표준화
   - 언론사 정보 정규화
   - 텍스트 정제

3. **확장성**
   - 비동기 처리
   - 모듈식 구조
   - 마이크로서비스 아키텍처

## 개발 가이드

### 새로운 수집기 추가

1. BaseCollector 상속
2. collect 메서드 구현
3. RabbitMQ 메시지 발행

```python
class NewCollector(BaseCollector):
    async def collect(self, **kwargs):
        # 데이터 수집 로직
        result = {
            'articles': articles,
            'metadata': {'keyword': kwargs.get('keyword')}
        }
        await self.publish_message(result)
        return result
```

### 데이터베이스 마이그레이션

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "migration_name"

# 마이그레이션 적용
alembic upgrade head

# 마이그레이션 롤백
alembic downgrade -1
```
