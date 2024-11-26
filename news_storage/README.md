# News Storage Module

뉴스 데이터를 저장하고 관리하는 모듈입니다. RabbitMQ를 통해 `news_collector` 모듈로부터 데이터를 수신하여 PostgreSQL 데이터베이스에 저장합니다.

## 주요 기능

- RabbitMQ를 통한 이벤트 기반 데이터 수신
- PostgreSQL을 사용한 데이터 영구 저장
- 비동기 데이터베이스 작업 지원
- 메시지 타입별 처리 (메타데이터, 본문, 댓글)
- 자동 재연결 및 오류 복구

## 아키텍처

```
[news_collector] ---> [RabbitMQ] ---> [news_storage] ---> [PostgreSQL]
     발행자          메시지 브로커       소비자           데이터베이스
```

### 메시지 큐

- `metadata_queue`: 기사 메타데이터
- `content_queue`: 기사 본문
- `comments_queue`: 댓글 데이터

## 설치 및 실행

1. 환경 변수 설정

```bash
# .env 파일
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
NEWS_STORAGE_URL=postgresql+asyncpg://user:password@postgres:5432/news_db
```

2. Docker Compose로 실행

```bash
docker-compose up -d
```

## 데이터베이스 스키마

### articles

- 기사 메타데이터 저장
- 제목, 링크, 발행일 등 기본 정보

### contents

- 기사 본문 및 관련 정보
- 서브헤딩, 이미지, 기자 정보 등

### comments

- 기사 댓글
- 작성자, 내용, 작성일 등

### comment_stats

- 댓글 통계 정보
- 성별/연령대 분포, 삭제된 댓글 수 등

## 메시지 형식

### 메타데이터

```json
{
  "type": "metadata",
  "articles": [
    {
      "title": "기사 제목",
      "naver_link": "네이버 링크",
      "original_link": "원본 링크",
      "description": "설명",
      "publisher": "언론사",
      "published_at": "2024-03-20T14:30:00+09:00",
      "collected_at": "2024-03-20T14:35:00+09:00"
    }
  ]
}
```

### 본문

```json
{
  "type": "content",
  "article_id": 123,
  "content": {
    "subheadings": ["소제목1", "소제목2"],
    "content": "기사 본문",
    "reporter": "기자 이름",
    "images": [
      {
        "url": "이미지 URL",
        "caption": "이미지 설명"
      }
    ]
  }
}
```

### 댓글

```json
{
  "type": "comments",
  "article_id": 123,
  "comments": [
    {
      "comment_no": "댓글 ID",
      "content": "댓글 내용",
      "author": "작성자",
      "timestamp": "2024-03-20T15:00:00+09:00"
    }
  ]
}
```

## 오류 처리

1. **RabbitMQ 연결 오류**

   - 최대 5회 재시도
   - 5초 간격으로 재연결 시도

2. **데이터베이스 오류**

   - 트랜잭션 롤백
   - 메시지 재처리를 위한 requeue

3. **메시지 처리 오류**
   - 잘못된 형식: 메시지 폐기
   - 처리 실패: 재시도를 위한 requeue

## 모니터링

- 로그 레벨: INFO
- 주요 모니터링 포인트:
  - RabbitMQ 연결 상태
  - 메시지 처리 성공/실패
  - 데이터베이스 작업 상태

## 개발 환경

- Python >= 3.8
- PostgreSQL 15
- RabbitMQ 3-management
- SQLAlchemy 2.0 (async)
- aio-pika for RabbitMQ

## 테스트

```bash
# 단위 테스트 실행
pytest tests/

# 통합 테스트 실행
pytest tests/integration/
```

## 라이센스

MIT License
