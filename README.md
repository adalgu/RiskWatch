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

4. **Selenium Grid**
   - 분산 웹 브라우저 자동화
   - Hub/Node 구조로 확장성 제공
   - 크롤링 작업 병렬 처리

### 데이터 흐름

```mermaid
graph LR
    A[News Collector] -->|Publish| B[RabbitMQ]
    A -->|Web Scraping| E[Selenium Grid]
    B -->|Consume| C[News Storage]
    C -->|Store| D[PostgreSQL]
```

1. Collector가 뉴스 데이터 수집 (API 또는 Selenium)
2. RabbitMQ로 메시지 발행
3. Storage가 메시지 소비
4. PostgreSQL에 데이터 저장

### 도커 기반 아키텍처

```mermaid
graph TB
    subgraph Docker Network
        A[News Collector Container]
        B[RabbitMQ Container]
        C[News Storage Container]
        D[PostgreSQL Container]
        E[Selenium Hub Container]
        F[Chrome Node Container]
    end
    A -->|http://selenium-hub:4444| E
    E --> F
    A -->|amqp://rabbitmq:5672| B
    C -->|amqp://rabbitmq:5672| B
    C -->|postgresql://postgres:5432| D
```

1. **서비스 디스커버리**

   - 각 서비스는 도커 네트워크 내에서 서비스 이름으로 통신
   - 예: `http://selenium-hub:4444/wd/hub`, `amqp://rabbitmq:5672/`
   - 개발과 프로덕션 환경에서 동일한 구조 유지

2. **컨테이너 간 통신**

   - 내부 네트워크를 통한 안전한 통신
   - 필요한 포트만 선택적으로 외부 노출
   - 서비스 간 독립성 보장

3. **확장성**
   - 각 컨테이너는 독립적으로 스케일 가능
   - 로드 밸런싱 지원
   - 무중단 배포 가능

## 데이터 수집

### 수집 방식

1. **API 방식**

   - Naver News API 사용
   - 최신 기사 우선 수집
   - 정확한 타임스탬프 제공

2. **검색 방식**
   - Selenium Grid 기반 웹 크롤링
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
   SELENIUM_HUB_URL=http://selenium-hub:4444/wd/hub
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
   - Selenium Grid 준비 상태 확인
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

## 개발 및 배포 가이드

### 개발 환경

1. **로컬 개발**

   - Docker Compose로 모든 서비스 실행
   - 서비스 간 통신은 서비스 이름 사용
   - 환경 변수로 설정 관리

2. **디버깅**
   - 각 서비스의 로그 확인
   ```bash
   docker compose logs -f [service_name]
   ```
   - 컨테이너 내부 접속
   ```bash
   docker exec -it [container_name] bash
   ```

### 배포 환경

1. **클라우드 배포**

   - 동일한 도커 기반 아키텍처 유지
   - 서비스 디스커버리 메커니즘 활용
   - 필요한 서비스만 외부 노출

2. **스케일링**

   - 수평적 확장 가능
   - 로드 밸런서 사용
   - 컨테이너 오케스트레이션

3. **모니터링**
   - 각 서비스의 상태 모니터링
   - 로그 집중화
   - 성능 메트릭 수집

### 보안 고려사항

1. **네트워크 보안**

   - 내부 서비스는 외부에서 직접 접근 불가
   - 필요한 포트만 선택적 노출
   - TLS/SSL 적용

2. **인증/인가**

   - API 키 관리
   - 서비스 간 인증
   - 접근 권한 제어

3. **데이터 보안**
   - 민감 정보 암호화
   - 백업 및 복구 전략
   - 감사 로그 유지
