# 메타데이터 수집 스크립트 오류 해결

- **날짜**: 2025-02-28
- **작성자**: Gunn Kim
- **관련 이슈**: N/A
- **이전 로그**: N/A (첫 번째 로그)

## 문제 상황

메타데이터 수집 스크립트 실행 시 다음과 같은 오류가 발생했습니다:

```
(rm) gunn.kim@gunn RiskWatch % ./scripts/run_metadata_collection.sh               
Running metadata collection and storage...
Database template changes already applied
Collecting and storing metadata...
Traceback (most recent call last):
  File "/Users/gunn.kim/study/RiskWatch/scripts/collect_and_store_metadata.py", line 12, in <module>
    from news_collector.collectors.search_metadata_collector import SearchMetadataCollector
ModuleNotFoundError: No module named 'new
```

이 오류는 `news_collector` 패키지를 찾지 못해 발생했으며, 이후 해결 과정에서 다음과 같은 추가 문제들이 발견되었습니다:

1. Pydantic 버전 호환성 문제 (`model_dump()` vs `dict()` 메서드)
2. Selenium Hub 연결 문제 (Docker 컨테이너 내 `selenium-hub` 호스트명 해석 실패)
3. PostgreSQL 데이터베이스 연결 문제 (호스트명 설정 오류)

## 해결 전략

문제를 단계적으로 해결하기 위해 다음과 같은 전략을 채택했습니다:

1. **패키지 경로 문제 해결**: 로컬 `news_collector` 패키지를 개발 모드로 설치
2. **Pydantic 호환성 문제 해결**: 현재 FastAPI 버전과 호환되는 Pydantic v1 사용 유지
3. **인프라 구성 요소 실행**: Docker Compose로 필요한 서비스 실행 및 연결 설정 수정

## 구현 세부사항

### 1. 패키지 경로 문제 해결

`pip list` 명령어로 확인한 결과, `news_collector` 패키지가 다른 위치에 설치되어 있었습니다:

```
news_collector 0.1.0 /Users/gunn.kim/study/CommentWatch/news_system/news_collector
```

로컬 패키지를 개발 모드로 설치하여 해결했습니다:

```bash
pip install -e .
```

### 2. Pydantic 호환성 문제 해결

`article.py` 파일에서 `model_dump()` 메서드를 사용하고 있었으나, 이는 Pydantic v2의 메서드입니다. 현재 프로젝트는 FastAPI 0.68.2를 사용하고 있어 Pydantic v1과만 호환됩니다.

```python
# 변경 전 (Pydantic v2)
obj_in_data = obj_in.model_dump()

# 변경 후 (Pydantic v1)
obj_in_data = obj_in.dict()
```

Pydantic v2로 업그레이드를 시도했으나 FastAPI와의 호환성 문제로 다시 v1으로 되돌렸습니다.

### 3. Selenium Hub 연결 설정

Docker Compose로 Selenium Hub와 Chrome 노드를 실행했습니다:

```bash
docker-compose up -d selenium-hub chrome
```

`WebDriverUtils` 클래스에서 호스트명 해석 문제를 해결하기 위해 다음과 같이 수정했습니다:

```python
# 추가된 코드
if 'selenium-hub' in self.remote_url and not os.path.exists('/.dockerenv'):
    self.remote_url = self.remote_url.replace('selenium-hub', 'localhost')
```

### 4. 데이터베이스 연결 설정

환경 변수를 통해 올바른 데이터베이스 URL을 설정했습니다:

```bash
export DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/news_db
```

## 기술적 고려사항

### Pydantic 버전 선택

Pydantic v2는 다음과 같은 장점이 있지만, 현재 FastAPI 버전과 호환되지 않습니다:
- 향상된 성능
- 더 풍부한 API (`model_dump()` 등)
- 더 나은 타입 힌팅 지원

향후 FastAPI를 업그레이드할 때 함께 Pydantic v2로 마이그레이션하는 것이 좋을 것입니다.

### 로컬 개발 환경과 Docker 환경의 차이

로컬 개발 환경과 Docker 환경 간의 호스트명 차이로 인한 문제가 발생했습니다:
- Docker 내부: `selenium-hub`, `postgres` 등의 서비스명을 호스트명으로 사용
- 로컬 환경: `localhost`를 사용해야 함

이를 해결하기 위해 환경 감지 로직을 추가했습니다.

### 환경 변수를 통한 설정 관리

환경 변수를 통해 설정을 관리하는 것이 중요합니다:
- 개발/테스트/운영 환경 간 설정 차이 관리
- 민감한 정보(비밀번호 등) 코드에서 분리
- 배포 환경에 따른 유연한 설정 변경

## 다음 단계

1. **환경 설정 개선**: `.env` 파일을 통한 환경 변수 관리 강화
2. **의존성 관리 개선**: 패키지 버전 충돌 방지를 위한 의존성 관리 개선
3. **FastAPI 및 관련 라이브러리 업그레이드 계획**: 최신 버전으로 업그레이드하여 새로운 기능 및 개선사항 활용

## 참고 자료

- [Pydantic v1 vs v2 비교](https://docs.pydantic.dev/latest/migration/)
- [FastAPI 호환성 가이드](https://fastapi.tiangolo.com/advanced/settings/)
- [Docker Compose 네트워킹](https://docs.docker.com/compose/networking/)
- [SQLAlchemy 비동기 지원](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
