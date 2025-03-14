# 프로젝트 진행 로그 정책

## 로그 실행을 위한 프롬프트(사용자용)
```
RiskWatch 프로젝트에 대한 진행 로그를 작성해 주세요. 

우리는 프로젝트 진행 상황을 체계적으로 기록하기 위해 다음 경로에 로그 정책을 마련했습니다:
/Users/gunn.kim/study/RiskWatch/docs/progress_logs/00-progress-log-policy.md
또는 /docs/progress_logs/00-progress-log-policy.md

이 정책에 따라 [작업 내용에 대한 간략한 설명]에 대한 진행 로그를 작성해 주세요. 
파일명은 YYYY-MM-DD-NNN-category-brief-description.md 형식을 따라야 합니다.

주요 내용은 다음과 같습니다:
1. [문제 상황 또는 작업 내용]
2. [해결 방법 또는 구현 방법]
3. [기술적 고려사항]
4. [다음 단계]

이전 로그 참조가 필요한 경우, 다음 로그를 참조하세요: [이전 로그 파일명]
```

## 목적
이 문서는 RiskWatch 프로젝트의 진행 상황, 문제 해결 과정, 의사결정 사항을 체계적으로 기록하기 위한 정책을 정의합니다.

## 파일 구조 및 네이밍 규칙

### 디렉토리 구조
```
docs/
└── progress_logs/
    ├── 00-progress-log-policy.md (이 문서)
    ├── YYYY-MM-DD-NNN-category-brief-description.md
    └── images/
        └── YYYY-MM-DD-NNN-brief-description.png
```

### 파일 네이밍 규칙
- **형식**: `YYYY-MM-DD-NNN-category-brief-description.md`
  - `YYYY-MM-DD`: 작업 날짜 (예: 2025-02-28)
  - `NNN`: 일련번호 (001부터 시작, 같은 날 여러 로그 작성 시 구분)
  - `category`: 작업 카테고리 (아래 카테고리 참조)
  - `brief-description`: 간략한 설명 (하이픈으로 단어 구분)

### 카테고리 코드
- `bug-fix`: 버그 수정
- `feature`: 새 기능 개발
- `refactor`: 코드 리팩토링
- `infra`: 인프라 설정
- `dependency`: 의존성 관리
- `docs`: 문서화 작업
- `test`: 테스트 관련 작업
- `perf`: 성능 개선
- `security`: 보안 관련 작업

## 로그 내용 구조

### 기본 템플릿
```markdown
# [간략한 제목]

- **날짜**: YYYY-MM-DD
- **작성자**: [작성자 이름]
- **관련 이슈**: [이슈 번호 또는 링크]
- **이전 로그**: [관련된 이전 로그 파일명]

## 문제 상황
[문제에 대한 명확한 설명]

## 해결 전략
[채택한 해결 방법과 그 이유]

## 구현 세부사항
[주요 변경사항 및 구현 방법]

## 기술적 고려사항
[고려한 대안, 제약사항, 향후 영향]

## 다음 단계
[후속 작업 또는 관련 작업]

## 참고 자료
[참고한 문서, 코드, 외부 자료 등]
```

## 연속성 및 참조 규칙

### 로그 간 연결
- 각 로그는 관련된 이전 로그를 명시적으로 참조해야 합니다.
- 여러 로그가 연결된 경우, 최신 로그에서 이전 로그들의 시퀀스를 모두 나열합니다.

### 참조 형식
- 이전 로그 참조: `[이전 로그 제목](./YYYY-MM-DD-NNN-category-brief-description.md)`
- 이슈 참조: `[이슈 #번호](이슈 URL)`
- 코드 참조: 상대 경로 사용 (예: `[파일명](../../path/to/file.py)`)

### 시퀀스 예시
```
2025-02-28-001-bug-fix-metadata-collection.md
2025-03-01-001-feature-add-error-handling.md (이전 로그: 2025-02-28-001)
2025-03-05-002-refactor-metadata-collector.md (이전 로그: 2025-03-01-001, 2025-02-28-001)
```

## 내용 작성 지침

### 길이 및 상세도
- 각 로그는 500-1000단어 내외로 유지
- 코드 예시는 핵심 부분만 포함 (전체 코드는 참조로 대체)
- 문제 해결 과정의 주요 단계와 결정 사항에 집중

### 코드 블록
- 언어 지정하여 구문 강조 사용 (예: ```python)
- 중요한 변경사항만 포함하고 전체 파일은 참조로 대체

### 이미지 및 다이어그램
- 필요시 이미지는 `docs/progress_logs/images/` 폴더에 저장
- 네이밍: `YYYY-MM-DD-NNN-brief-description.png`
- 참조: `![설명](./images/YYYY-MM-DD-NNN-brief-description.png)`

## 검색 및 필터링
로그 파일의 일관된 구조와 네이밍을 통해 다음과 같은 검색이 가능합니다:
- 날짜별 검색: `YYYY-MM-DD-*`
- 카테고리별 검색: `*-category-*`
- 키워드 검색: 파일 내용 기반

## 유지보수
- 분기별로 로그 인덱스 업데이트
- 연간 로그 요약 문서 작성
- 더 이상 관련 없는 로그는 `archived/` 폴더로 이동
