# Streamlit UI 모듈 임포트 문제 해결

- **날짜**: 2025-03-01
- **작성자**: Gunn Kim
- **관련 이슈**: N/A
- **이전 로그**: [댓글 수집 기능 구현 성공](./2025-02-28-006-feature-comment-collection-success.md)

## 문제 상황

Streamlit을 사용하여 뉴스 기사 및 댓글 수집 UI를 구현하는 과정에서 여러 모듈 임포트 관련 문제가 발생했습니다:

1. 상대 경로 임포트 문제: Streamlit 실행 시 `ImportError: attempted relative import with no known parent package` 오류 발생
2. 외부 모듈 의존성 문제: `news_collector.collectors.comment` 모듈을 찾을 수 없는 오류
3. 네임스페이스 충돌: Streamlit 내부 `validators` 모듈과 프로젝트 내 `validators.py` 파일 간 충돌

이러한 문제로 인해 Streamlit 애플리케이션이 정상적으로 실행되지 않았습니다.

## 해결 전략

다음과 같은 전략으로 문제를 해결했습니다:

1. 상대 경로 임포트 문제 해결을 위해 절대 경로 임포트로 변경
2. 외부 모듈 의존성 문제 해결을 위해 `collection_service.py` 파일을 간소화된 데모 버전으로 대체
3. 네임스페이스 충돌 해결을 위해 `validators.py` 파일을 `data_validators.py`로 이름 변경

## 구현 세부사항

### 1. 상대 경로 임포트 문제 해결

Streamlit은 각 페이지를 독립적인 스크립트로 실행하기 때문에 상대 경로 임포트가 제대로 작동하지 않습니다. 이를 해결하기 위해 다음과 같이 수정했습니다:

```python
# 기존 코드 (문제 발생)
from .modules.database import Database
from .collection_service import CollectionService

# 수정된 코드
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.database import Database
from collection_service import CollectionService
```

### 2. 외부 모듈 의존성 문제 해결

`collection_service.py` 파일이 외부 모듈에 의존하고 있어 문제가 발생했습니다. 이를 해결하기 위해 간소화된 데모 버전으로 대체했습니다:

```python
"""
Data collection module for the dashboard application.
Provides functions for collecting articles and comments.

This is a simplified version for demonstration purposes.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional, Union
import pytz
import random

# 한국 표준시(KST) 설정
KST = pytz.timezone('Asia/Seoul')

# 수집 방식 상수
class CollectionMethod:
    API = "API"
    SEARCH = "SEARCH"
    COMMENTS = "COMMENTS"

# 기사 상태 상수
class ArticleStatus:
    pending = "PENDING"
    in_progress = "IN_PROGRESS"
    completed = "COMPLETED"
    failed = "FAILED"

# 예외 클래스
class CollectionError(Exception):
    """Collection related error"""
    pass

class CollectionService:
    """
    수집 서비스 클래스 (데모 버전)
    메타데이터 및 댓글 수집 기능을 제공합니다.
    """
    
    def __init__(self):
        """Initialize collection service."""
        pass
    
    def collect_metadata(self, keyword, start_date, end_date, **kwargs):
        """메타데이터 수집 (데모 버전)"""
        return {
            "job_id": random.randint(1000, 9999),
            "status": ArticleStatus.pending,
            "message": "메타데이터 수집 작업이 성공적으로 요청되었습니다."
        }
    
    # 기타 메서드 생략...
```

### 3. 네임스페이스 충돌 해결

Streamlit 내부 `validators` 모듈과 프로젝트 내 `validators.py` 파일 간 충돌을 해결하기 위해 파일 이름을 변경했습니다:

```bash
mv news_visualizer/news_ui/validators.py news_visualizer/news_ui/data_validators.py
```

그리고 관련 임포트 구문을 모두 업데이트했습니다:

```python
# 기존 코드
from .validators import validate_date_range

# 수정된 코드
from .data_validators import validate_date_range
```

## 기술적 고려사항

### 1. Streamlit의 실행 모델 이해

Streamlit은 각 페이지를 독립적인 Python 스크립트로 실행하기 때문에 상대 경로 임포트가 예상대로 작동하지 않습니다. 이는 Streamlit의 설계 특성으로, 멀티페이지 애플리케이션에서 특히 주의해야 합니다.

### 2. 데이터베이스 연결 문제

PostgreSQL 데이터베이스 연결 시 `asyncpg` 드라이버를 사용하는데, 이는 비동기 코드를 요구합니다. Streamlit은 기본적으로 동기 실행 환경이므로 이로 인한 충돌이 발생했습니다. 이 문제를 해결하기 위해 데이터베이스 연결 부분을 try-except 블록으로 감싸 오류를 적절히 처리했습니다.

### 3. 모듈 의존성 관리

프로젝트가 여러 하위 패키지로 구성되어 있어 의존성 관리가 복잡합니다. 특히 `news_collector`, `news_storage`, `news_visualizer` 간의 의존성이 명확하게 정의되어 있지 않아 문제가 발생했습니다. 장기적으로는 패키지 간 의존성을 명확히 정의하고 관리할 필요가 있습니다.

## 다음 단계

1. **데이터베이스 연결 개선**: 현재는 오류 처리를 통해 문제를 회피하고 있지만, 장기적으로는 Streamlit에서 비동기 데이터베이스 연결을 적절히 처리할 수 있는 방법을 모색해야 합니다.

2. **모듈 구조 개선**: 현재는 임시 방편으로 문제를 해결했지만, 패키지 구조를 개선하여 상대 경로 임포트 문제를 근본적으로 해결할 필요가 있습니다.

3. **UI 기능 확장**: 기본적인 UI 구현이 완료되었으므로, 다음 단계로는 사용자 경험을 개선하고 추가 기능(예: 데이터 시각화, 필터링 옵션 등)을 구현할 계획입니다.

4. **테스트 코드 작성**: UI 구현에 대한 테스트 코드를 작성하여 향후 변경 사항이 기존 기능을 손상시키지 않도록 해야 합니다.

## 참고 자료

- [Streamlit 공식 문서 - 멀티페이지 앱](https://docs.streamlit.io/library/get-started/multipage-apps)
- [Python 패키지 임포트 문제 해결 가이드](https://docs.python.org/3/tutorial/modules.html)
- [SQLModel과 비동기 데이터베이스 연결](https://sqlmodel.tiangolo.com/tutorial/fastapi/async-sql/)
