FastAPI 도입 요구조건 문서 (v1.1)

변경 사항 요약 (v1.0 → v1.1)

	1.	RabbitMQ 및 FastAPI 간 역할 분리 명확화:
	•	RabbitMQ는 메시징 및 비동기 작업 전송에 최적화.
	•	FastAPI는 요청 관리, 상태 모니터링, 리소스 최적화를 위한 중앙 인터페이스 제공.
	2.	동시 요청 처리 시나리오 반영:
	•	여러 부서에서 동시 요청 처리 요구사항과 솔루션 반영.
	•	요청 우선순위 설정과 리소스 제어를 위한 API 설계 추가.
	3.	추가 엔드포인트 정의:
	•	부서별 요청 상태 조회 및 우선순위 관리.

1. 요구사항

1.1 주요 기능

	1.	수집기 제어 및 상태 관리
	•	요청 기반 수집 작업 시작/중지.
	•	각 요청의 상태를 실시간으로 확인.
	2.	동시 요청 처리
	•	여러 부서의 요청이 충돌 없이 독립적으로 처리될 수 있는 구조 제공.
	•	부서별 할당량 관리 및 우선순위 큐 설정.
	3.	리소스 모니터링 및 최적화
	•	현재 사용 중인 리소스(Selenium Grid 노드 수, RabbitMQ 큐 상태 등) 모니터링.
	•	API를 통해 리소스 사용량 조정 및 최적화.
	4.	로그 관리 및 데이터 조회
	•	최근 실행 로그와 에러 로그 제공.
	•	수집된 데이터 조회 및 다운로드 기능 지원.

2. RESTful API 설계

2.1 주요 엔드포인트

HTTP Method	Endpoint	Description
POST	/collectors/metadata/start	Metadata 수집 시작
POST	/collectors/metadata/stop	Metadata 수집 중지
GET	/collectors/metadata/status	Metadata 수집 상태 조회
POST	/collectors/comments/start	Comments 수집 시작
POST	/collectors/comments/stop	Comments 수집 중지
GET	/collectors/comments/status	Comments 수집 상태 조회
GET	/collectors/status	모든 수집기 상태 조회
POST	/collectors/pause	전체 수집 작업 일시 정지
POST	/collectors/resume	일시 정지된 작업 재개
GET	/logs	실행 로그 및 에러 로그 반환
GET	/resources/usage	리소스 사용량 반환

2.2 요청 및 응답 예시

2.2.1 동시 요청 예시

	1.	미국 증시 기사 요청

{
  "method": "api",
  "keyword": "미국 증시",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "department": "CR"
}


	2.	여의도 시황 기사 요청

{
  "method": "search",
  "keyword": "여의도 시황",
  "start_date": "2024-02-01",
  "end_date": "2024-02-28",
  "department": "Finance"
}


	3.	댓글 수집 요청

{
  "method": "comments",
  "keyword": "우리 회사",
  "start_date": "2024-03-01",
  "end_date": "2024-03-31",
  "department": "PR"
}

2.3 우선순위 큐 및 상태 관리

우선순위 설정

	•	API 호출 시 priority 필드 추가:

{
  "method": "api",
  "keyword": "주요 이슈",
  "priority": "high"
}



상태 관리 엔드포인트

	•	요청 상태 조회:
	•	GET /collectors/status
	•	응답 예시:

{
  "collectors": [
    {
      "id": "metadata_12345",
      "status": "running",
      "keyword": "미국 증시",
      "department": "CR",
      "priority": "high",
      "progress": "60%"
    },
    {
      "id": "comments_67890",
      "status": "queued",
      "keyword": "우리 회사",
      "department": "PR",
      "priority": "medium",
      "progress": "0%"
    }
  ]
}

3. 구현 계획

3.1 기술 스택

	•	FastAPI: 비동기 API 개발.
	•	RabbitMQ: 메시지 큐를 활용한 작업 관리.
	•	PostgreSQL: 데이터 저장 및 조회.
	•	Selenium Grid: 병렬 작업 처리.

3.2 요청 처리 흐름

	1.	API 호출 → 요청 정보 RabbitMQ로 발행.
	2.	RabbitMQ 소비자가 메시지를 처리하여 수집기 실행.
	3.	진행 상태 및 결과는 API를 통해 조회 가능.

4. 예산 부서 및 총무 부서 문의사항 반영

	•	RabbitMQ의 역할:
	•	메시지 발행 및 비동기 작업 분배 유지.
	•	FastAPI 추가 역할:
	•	요청 관리, 우선순위 설정, 실시간 상태 확인 및 리소스 최적화.
	•	동시 요청 처리:
	•	동시간에 여러 부서의 요청을 수집기가 처리할 수 있는 병렬 구조.
	•	우선순위 큐 및 작업 상태 관리 API로 요청 간 충돌 방지.

이 문서를 FastAPI 도입 프로젝트의 최신 버전(v1.1)으로 공유하세요. 필요 시 피드백을 받아 추가로 업데이트할 수 있습니다!

5. 향후 확장 가능성

	1.	대시보드 통합:
	•	RESTful API와 Streamlit 대시보드 연동.
	2.	추가 수집기 지원:
	•	새로운 수집기를 API로 쉽게 추가 가능.
	3.	로그 시각화:
	•	로그 데이터를 대시보드에서 그래프로 시각화.

