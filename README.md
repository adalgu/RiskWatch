# Risk Watch

뉴스 데이터 수집, 저장, 분석 및 시각화를 위한 통합 시스템입니다. 이벤트 기반 아키텍처를 사용하여 네이버 뉴스 데이터를 수집하고, FastAPI 기반 API를 통해 데이터를 제공하며, 대시보드를 통해 데이터를 시각화합니다.

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

3. **News Visualizer**
   - 수집된 뉴스 데이터 시각화
   - 웹 기반 대시보드 제공
   - 데이터 분석 및 인사이트 제공

4. **FastAPI Backend**
   - RESTful API 제공
   - 데이터 CRUD 작업 처리
   - 비동기 작업 지원

5. **Message Broker (RabbitMQ)**
   - 컴포넌트 간 메시지 전달
   - 비동기 통신 지원
   - 메시지 영속성 보장

6. **Selenium Grid**
   - 분산 웹 브라우저 자동화
   - Hub/Node 구조로 확장성 제공
   - 크롤링 작업 병렬 처리

7. **Monitoring (Prometheus)**
   - 시스템 메트릭 수집
   - 성능 모니터링
   - 알림 설정 지원

### 데이터 흐름

```mermaid
graph LR
    A[News Collector] -->|Publish| B[RabbitMQ]
    A -->|Web Scraping| E[Selenium Grid]
    B -->|Consume| C[News Storage]
    C -->|Store| D[PostgreSQL]
    F[FastAPI] -->|Query| D
    G[News Visualizer] -->|API Calls| F
    H[Prometheus] -->|Monitor| A & B & C & D & F
```

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
        G[FastAPI Container]
        H[News Visualizer Container]
        I[Prometheus Container]
    end
    A -->|http://selenium-hub:4444| E
    E --> F
    A -->|amqp://rabbitmq:5672| B
    C -->|amqp://rabbitmq:5672| B
    C -->|postgresql://postgres:5432| D
    G -->|postgresql://postgres:5432| D
    H -->|http://fastapi:8000| G
    I -->|metrics| A & B & C & D & G
```

## 설치 및 실행

### 필수 요구사항

1. **Docker & Docker Compose**
   - Docker 설치
   - Docker Compose 설치

2. **Python 패키지 설치**
   ```bash
   # 각 컴포넌트의 Python 패키지 설치
   pip install -e news_collector/
   pip install -e news_storage/
   pip install -e common/
   ```

3. **환경 변수 설정**
   ```bash
   # .env 파일 생성
   DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/news_db
   RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
   NAVER_CLIENT_ID=your_client_id
   NAVER_CLIENT_SECRET=your_client_secret
   SELENIUM_HUB_URL=http://selenium-hub:4444/wd/hub
   ```

### 실행 방법

1. **Docker Compose로 실행**
   ```bash
   # 모든 서비스 시작
   docker compose up -d

   # 특정 서비스만 시작
   docker compose up -d news-collector news-storage fastapi
   ```

2. **개별 서비스 실행**
   ```bash
   # News Collector
   cd news_collector
   python -m news_collector.producer

   # News Storage
   cd news_storage
   python -m src.consumer

   # News Visualizer
   cd news_visualizer/news_ui
   streamlit run app.py
   ```

3. **데이터베이스 마이그레이션**
   ```bash
   # 마이그레이션 실행
   alembic upgrade head
   ```

### 컴포넌트별 설정

1. **News Collector**
   ```bash
   cd news_collector
   pip install -e .
   ```

2. **News Storage**
   ```bash
   cd news_storage
   pip install -e .
   ```

3. **News Visualizer**
   ```bash
   cd news_visualizer/news_ui
   pip install -e .
   
   # PYTHONPATH 설정 (news_storage 모듈 접근용)
   export PYTHONPATH=$PYTHONPATH:/path/to/project/root
   ```

## API 엔드포인트

### News Collector API

```
GET /api/v1/collector/status - 수집기 상태 확인
POST /api/v1/collector/start - 수집 작업 시작
POST /api/v1/collector/stop - 수집 작업 중지
GET /api/v1/collector/stats - 수집 통계 조회
```

### News Storage API

```
GET /api/v1/articles - 기사 목록 조회
GET /api/v1/articles/{id} - 특정 기사 조회
GET /api/v1/articles/{id}/comments - 기사 댓글 조회
GET /api/v1/articles/{id}/stats - 기사 통계 조회
```

[이전 내용 계속...]

## 모니터링

### Prometheus 설정

1. **메트릭 수집**
   - 시스템 리소스 사용량
   - API 엔드포인트 응답 시간
   - 수집기 성능 지표
   - 데이터베이스 연결 상태

2. **알림 설정**
   - 리소스 사용량 임계치 초과
   - API 응답 시간 지연
   - 수집기 오류 발생
   - 데이터베이스 연결 실패

3. **대시보드 구성**
   ```yaml
   # prometheus.yml
   global:
     scrape_interval: 15s
   
   scrape_configs:
     - job_name: 'news_collector'
       static_configs:
         - targets: ['collector:8000']
     
     - job_name: 'news_storage'
       static_configs:
         - targets: ['storage:8000']
     
     - job_name: 'fastapi'
       static_configs:
         - targets: ['api:8000']
   ```

## 문제 해결

### 일반적인 문제

1. **모듈 Import 오류**
   ```bash
   # PYTHONPATH 설정으로 해결
   export PYTHONPATH=$PYTHONPATH:/path/to/project/root
   
   # Docker 환경에서는 볼륨 마운트로 해결
   volumes:
     - .:/app
   ```

2. **데이터베이스 연결 오류**
   - 환경 변수 확인
   - PostgreSQL 서비스 실행 상태 확인
   - 네트워크 연결 확인

3. **RabbitMQ 연결 오류**
   - 서비스 실행 상태 확인
   - 크레덴셜 확인
   - 큐 상태 확인

[이전 내용 계속...]
