# News Data Dashboard

PostgreSQL 데이터베이스에 저장된 뉴스 데이터를 시각화하는 웹 대시보드입니다.

## 기능

- 최근 수집된 뉴스 기사 목록 확인
- 기사 내용 및 원문 링크 제공
- 댓글 목록 확인
- 댓글 통계 시각화 (성별/연령대 분포)

## 실행 방법

### Docker Compose 사용 (권장)

1. 프로젝트 루트 디렉토리에서 Docker Compose로 실행:

```bash
docker-compose up -d news_data_dashboard
```

2. 웹 브라우저에서 접속:

```
http://localhost:5050
```

### 수동 실행 (개발용)

1. 의존성 설치:

```bash
pip install -r requirements.txt
```

2. 환경 변수 설정:

```bash
export DATABASE_URL=postgresql://postgres:password@localhost:5432/news_db
```

3. Flask 앱 실행:

```bash
python app.py
```

## 사용 방법

1. 왼쪽 패널에서 기사 목록을 확인할 수 있습니다.
2. 기사를 클릭하면 오른쪽 패널에서 상세 내용을 볼 수 있습니다.
3. 기사 상세 페이지에서는:
   - 기사 전문
   - 원문 링크
   - 댓글 통계 (성별/연령대 분포)
   - 댓글 목록
     을 확인할 수 있습니다.
4. "더 보기" 버튼을 클릭하여 추가 기사를 로드할 수 있습니다.

## Docker 구성

- 이미지: Python 3.9 slim
- 포트: 5000 (컨테이너 내부) -> 5050 (호스트)
- 환경 변수:
  - DATABASE_URL: PostgreSQL 데이터베이스 연결 문자열
- 볼륨: news_storage 디렉토리가 컨테이너의 /app/news_storage에 마운트됨

## 주의사항

- PostgreSQL 서비스가 실행 중이어야 합니다
- Docker Compose로 실행 시 자동으로 필요한 서비스들이 함께 실행됩니다
- 데이터베이스 마이그레이션이 완료된 상태여야 합니다
