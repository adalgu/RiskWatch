# 뉴스 댓글 분석 대시보드

이 프로젝트는 뉴스 기사와 댓글을 수집하고 분석하는 Streamlit 기반 UI 애플리케이션입니다.

## 주요 기능

1. **데이터 수집 인터페이스**
   - 키워드 기반 뉴스 메타데이터 수집
   - 네이버 뉴스 댓글 수집
   - 수집 상태 및 로그 모니터링

2. **댓글 분석**
   - 댓글이 많은 상위 기사 확인
   - 댓글 감정 분석 결과 시각화
   - 키워드 빈도 분석

3. **데이터베이스 결과 확인**
   - 기사 및 댓글 데이터 요약 통계
   - 일별 데이터 수집 추이
   - 최근 수집된 기사 목록

## 설치 방법

### Docker를 이용한 설치 (권장)

1. Docker와 Docker Compose가 설치되어 있어야 합니다.

2. 다음 명령어로 애플리케이션을 실행합니다:
   ```bash
   cd news_visualizer/news_ui
   docker-compose up -d
   ```

3. 브라우저에서 `http://localhost:8501`로 접속하여 UI를 확인합니다.

### 로컬 설치

1. Python 3.10 이상이 필요합니다.

2. 필요한 패키지를 설치합니다:
   ```bash
   cd news_visualizer/news_ui
   pip install -r requirements.txt
   ```

3. 환경 변수를 설정합니다:
   ```bash
   export DATABASE_URL=postgresql://postgres:password@localhost:5432/news_db
   ```

4. 애플리케이션을 실행합니다:
   ```bash
   streamlit run app.py
   ```

## 사용 방법

### 데이터 수집

1. 왼쪽 사이드바에서 "데이터 수집" 페이지로 이동합니다.
2. "메타데이터 수집" 탭에서 키워드와 날짜 범위를 입력하고 "수집 시작" 버튼을 클릭합니다.
3. "댓글 수집" 탭에서 키워드와 날짜 범위를 입력하고 "수집 시작" 버튼을 클릭합니다.
4. 수집 상태와 로그를 실시간으로 확인할 수 있습니다.

### 댓글 분석

1. 왼쪽 사이드바에서 "댓글 분석" 페이지로 이동합니다.
2. 댓글이 많은 상위 기사, 감정 분석 결과, 키워드 빈도 등 다양한 분석 결과를 확인할 수 있습니다.

### 데이터베이스 결과 확인

1. 왼쪽 사이드바에서 "DB 결과 확인" 페이지로 이동합니다.
2. 기사 및 댓글 데이터 요약, 일별 데이터 수집 추이, 최근 수집된 기사 목록 등을 확인할 수 있습니다.

## 프로젝트 구조

```
news_ui/
├── app.py                  # 메인 애플리케이션 진입점
├── collection_service.py   # 수집 요청 서비스
├── logging_config.py       # 로깅 설정
├── modules/                # 모듈 디렉토리
│   ├── database.py         # 데이터베이스 연결 및 쿼리
│   └── models.py           # 데이터 모델 정의
├── pages/                  # Streamlit 페이지
│   ├── 1_Collection.py     # 데이터 수집 페이지
│   ├── 2_Comments.py       # 댓글 분석 페이지
│   └── 3_Database_Results.py  # DB 결과 확인 페이지
├── Dockerfile              # Docker 이미지 빌드 파일
├── docker-compose.yml      # Docker Compose 설정
└── test_app.py             # 테스트 코드
```

## 백엔드 연동

이 UI 애플리케이션은 FastAPI 백엔드 서버와 통신하여 데이터 수집 요청을 처리합니다. 백엔드 서버는 다음 엔드포인트를 제공해야 합니다:

- `POST /api/v1/collectors/metadata/start`: 메타데이터 수집 시작
- `POST /api/v1/collectors/comments/start`: 댓글 수집 시작

## 테스트

다음 명령어로 단위 테스트를 실행할 수 있습니다:

```bash
python -m unittest test_app.py
```
