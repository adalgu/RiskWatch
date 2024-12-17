from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import pytz
from enum import Enum

KST = pytz.timezone('Asia/Seoul')

def format_datetime(dt: datetime) -> str:
    """Format datetime to ISO format with timezone"""
    if dt.tzinfo is None:
        dt = KST.localize(dt)
    return dt.isoformat()

class CollectionMethod(str, Enum):
    API = "API"
    SEARCH = "SEARCH"

class CollectionStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class MetadataCollectionRequest(BaseModel):
    """메타데이터 수집 요청 모델"""
    keyword: str = Field(..., description="검색 키워드")
    method: CollectionMethod = Field(default=CollectionMethod.API, description="수집 방식 (API 또는 SEARCH)")
    start_date: Optional[datetime] = Field(None, description="검색 시작 날짜")
    end_date: Optional[datetime] = Field(None, description="검색 종료 날짜")
    max_articles: Optional[int] = Field(100, description="수집할 최대 기사 수")
    min_delay: Optional[float] = Field(0.1, description="요청 간 최소 지연 시간(초)")
    max_delay: Optional[float] = Field(0.5, description="요청 간 최대 지연 시간(초)")
    batch_size: Optional[int] = Field(100, description="한 번에 처리할 기사 수")
    is_test: Optional[bool] = Field(False, description="테스트 모드 여부")

class CommentCollectionRequest(BaseModel):
    """댓글 수집 요청 모델"""
    article_urls: List[str] = Field(..., description="댓글을 수집할 기사 URL 목록")
    min_delay: Optional[float] = Field(0.1, description="요청 간 최소 지연 시간(초)")
    max_delay: Optional[float] = Field(0.5, description="요청 간 최대 지연 시간(초)")
    batch_size: Optional[int] = Field(10, description="한 번에 처리할 기사 수")
    is_test: Optional[bool] = Field(False, description="테스트 모드 여부")

class CollectionResponse(BaseModel):
    """수집 요청 응답 모델"""
    request_id: str = Field(..., description="수집 요청 ID")
    success: bool = Field(..., description="요청 성공 여부")
    message: str = Field(..., description="응답 메시지")
    status: CollectionStatus = Field(..., description="수집 상태")
    total_collected: Optional[int] = Field(None, description="수집된 총 항목 수")
    queued_at: datetime = Field(default_factory=lambda: datetime.now(KST), description="큐에 추가된 시간")

class CollectionStatusResponse(BaseModel):
    """수집 상태 응답 모델"""
    request_id: str = Field(..., description="수집 요청 ID")
    status: CollectionStatus = Field(..., description="수집 상태")
    total_collected: Optional[int] = Field(None, description="수집된 총 항목 수")
    error_message: Optional[str] = Field(None, description="에러 메시지")
    started_at: Optional[datetime] = Field(None, description="수집 시작 시간")
    completed_at: Optional[datetime] = Field(None, description="수집 완료 시간")
    metadata: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")

class CollectionResult(BaseModel):
    """수집 결과 모델"""
    request_id: str = Field(..., description="수집 요청 ID")
    articles: List[Dict[str, Any]] = Field(..., description="수집된 기사 목록")
    collected_at: datetime = Field(default_factory=lambda: datetime.now(KST), description="수집 완료 시간")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="수집 메타데이터")
