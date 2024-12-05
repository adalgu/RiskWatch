# FastAPI 도입 진행 문서

## 1. 현재 상태 (As-Is)

### 1.1 시스템 구조
- news_collector: 뉴스 수집 모듈
  - collectors/: 각종 수집기 구현
  - core/: 핵심 유틸리티
  - parallel/: 병렬 처리 관련
  - ui/: Streamlit 기반 UI
- news_storage: 데이터 저장 모듈
  - database.py: DB 연결 및 조작
  - models.py: DB 모델
  - consumer.py: RabbitMQ 소비자

### 1.2 현재 작업 흐름
1. Streamlit UI를 통한 수집 요청
2. RabbitMQ를 통한 작업 분배
3. Selenium Grid를 통한 병렬 수집
4. PostgreSQL에 데이터 저장

## 2. 구현 계획 (To-Be)

### 2.1 FastAPI 도입 단계

#### Phase 1: 기본 API 구조 설정 (1주차) ✅
- [x] FastAPI 프로젝트 구조 생성
  - news_collector/api/
    - main.py: FastAPI 앱
    - routers/: 엔드포인트 라우터
    - models/: Pydantic 모델
    - services/: 비즈니스 로직
- [x] 기본 의존성 설정
  - FastAPI
  - Uvicorn
  - Pydantic
- [x] 헬스체크 엔드포인트 구현

#### Phase 2: 핵심 API 구현 (2주차) ✅
- [x] 수집기 제어 API 구현
  - POST /collectors/metadata/start
  - POST /collectors/metadata/stop
  - POST /collectors/comments/start
  - POST /collectors/comments/stop
- [x] 상태 조회 API 구현
  - GET /collectors/status
  - GET /collectors/metadata/status
  - GET /collectors/comments/status
- [x] API 테스트 및 문서화
- [x] RabbitMQ 연동 완료 및 테스트

#### Phase 3: 우선순위 및 리소스 관리 (3주차) 🔄
- [x] 우선순위 큐 구현
  - 부서별 우선순위 설정
  - 동시 요청 처리 로직
- [x] RabbitMQ 우선순위 큐 연동
  - 메시지 우선순위 설정 (1-9)
  - 우선순위 기반 처리 구현
- [x] 리소스 모니터링 구현
  - Selenium Grid 노드 상태 모니터링
  - RabbitMQ 큐 상태 모니터링
  - 시스템 리소스 모니터링
  - Prometheus/Grafana 통합

#### Phase 4: 로깅 및 데이터 접근 (4주차) ⏳
- [ ] 로그 관리 API
  - GET /logs
  - 로그 레벨별 필터링
- [ ] 데이터 조회 API
  - GET /data/metadata
  - GET /data/comments
  - 데이터 다운로드 기능

### 2.2 통합 테스트 계획

#### 기능 테스트
- [x] 각 엔드포인트 단위 테스트
- [x] 우선순위 큐 테스트
- [ ] 통합 테스트 시나리오 작성
- [ ] 부하 테스트 계획

#### 성능 테스트
- [x] 리소스 모니터링 테스트
- [ ] 동시 요청 처리 테스트
- [ ] 응답 시간 측정

## 3. 현재 진행 상황

### 3.1 완료된 작업
- [x] Phase 1, 2 완료
- [x] 우선순위 큐 구현 및 RabbitMQ 연동
- [x] 부서별 우선순위 처리 로직 구현
- [x] 동시 요청 처리 기본 구조 구현
- [x] 리소스 모니터링 시스템 구축
  - Prometheus/Grafana 설정
  - 메트릭 수집 구현
  - 모니터링 대시보드 구성

### 3.2 진행 중인 작업
- [ ] 리소스 모니터링 시스템 안정화
- [ ] 통합 테스트 시나리오 작성
- [ ] Phase 4 준비

### 3.3 다음 단계
1. 리소스 모니터링 시스템 안정화
2. 통합 테스트 실행
3. Phase 4 시작

## 4. 이슈 및 해결 방안

### 4.1 해결된 이슈
1. RabbitMQ 연동
   - 문제: 환경 변수 기반 설정 필요
   - 해결: Docker Compose 환경변수 설정 구현

2. 우선순위 큐 구현
   - 문제: 부서별 우선순위 충돌
   - 해결: RabbitMQ 메시지 우선순위(1-9) 및 큐 설정

3. 리소스 모니터링
   - 문제: 다중 서버 환경 통합 모니터링
   - 해결: Prometheus/Grafana 도입

### 4.2 현재 이슈
1. 시스템 안정성
   - 상태: 모니터링 중
   - 계획: 스트레스 테스트 및 장애 복구 시나리오 작성

2. 성능 최적화
   - 상태: 분석 중
   - 계획: 부하 테스트 후 병목 지점 식별 및 개선

## 5. 다음 업데이트 예정 사항
1. 통합 테스트 결과 보고
2. 성능 테스트 결과 분석
3. Phase 4 상세 계획 수립

---
마지막 업데이트: 2024-12-02
작성자: 삼돌
상태: 진행 중 (Phase 3)
