from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import json
import pytz
from uuid import UUID

from ..models.collector_models import (
    MetadataCollectionRequest,
    CommentCollectionRequest,
    CollectionResponse,
    CollectionStatusResponse,
    CollectionStatus,
    format_datetime
)
from ..services.collector_service import CollectorService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')

def serialize_datetime(obj: Any) -> Any:
    """Helper function to serialize datetime objects"""
    if isinstance(obj, datetime):
        return format_datetime(obj)
    return obj

router = APIRouter(
    prefix="/collectors",
    tags=["collectors"],
    responses={404: {"description": "Not found"}},
)

@router.post("/metadata/start")
async def start_metadata_collection(
    request: Request,
    collection_request: MetadataCollectionRequest,
    background_tasks: BackgroundTasks,
    collector_service: CollectorService = Depends()
) -> CollectionResponse:
    """
    메타데이터 수집 시작 엔드포인트
    - 수집 요청을 큐에 발행하고 요청 ID를 반환
    """
    try:
        # Log raw request for debugging
        raw_body = await request.body()
        logger.info(f"[Router] Raw request body: {raw_body.decode()}")
        
        # Log the request parameters
        request_dict = collection_request.model_dump()
        logger.info(f"[Router] Parsed request: {json.dumps(request_dict, default=serialize_datetime, ensure_ascii=False)}")
        
        # Start collection through service with background tasks
        status = await collector_service.collect_metadata(
            keyword=collection_request.keyword,
            method=collection_request.method,
            start_date=collection_request.start_date,
            end_date=collection_request.end_date,
            max_articles=collection_request.max_articles,
            min_delay=collection_request.min_delay,
            max_delay=collection_request.max_delay,
            batch_size=collection_request.batch_size,
            is_test=collection_request.is_test,
            background_tasks=background_tasks
        )
        
        # Return response with request ID
        return CollectionResponse(
            request_id=status.request_id,
            success=True,
            message="Metadata collection request queued successfully",
            status=status.status,
            total_collected=status.total_collected,
            queued_at=datetime.now(KST)
        )
        
    except ValueError as e:
        logger.error(f"[Router] Validation error in metadata collection: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request parameters: {str(e)}"
        )
    except Exception as e:
        logger.error(f"[Router] Error starting metadata collection: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start metadata collection: {str(e)}"
        )

@router.post("/comments/start")
async def start_comment_collection(
    request: Request,
    collection_request: CommentCollectionRequest,
    background_tasks: BackgroundTasks,
    collector_service: CollectorService = Depends()
) -> CollectionResponse:
    """
    댓글 수집 시작 엔드포인트
    - 수집 요청을 큐에 발행하고 요청 ID를 반환
    """
    try:
        # Log raw request for debugging
        raw_body = await request.body()
        logger.info(f"[Router] Raw request body: {raw_body.decode()}")
        
        # Log the request parameters
        request_dict = collection_request.model_dump()
        logger.info(f"[Router] Starting comment collection with params: {json.dumps(request_dict, default=serialize_datetime, ensure_ascii=False)}")
        
        # Start collection through service with background tasks
        status = await collector_service.collect_comments(
            article_urls=collection_request.article_urls,
            min_delay=collection_request.min_delay,
            max_delay=collection_request.max_delay,
            batch_size=collection_request.batch_size,
            is_test=collection_request.is_test,
            background_tasks=background_tasks
        )
        
        # Return response with request ID
        return CollectionResponse(
            request_id=status.request_id,
            success=True,
            message="Comment collection request queued successfully",
            status=status.status,
            total_collected=status.total_collected,
            queued_at=datetime.now(KST)
        )
        
    except ValueError as e:
        logger.error(f"[Router] Validation error in comment collection: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request parameters: {str(e)}"
        )
    except Exception as e:
        logger.error(f"[Router] Error starting comment collection: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start comment collection: {str(e)}"
        )

@router.get("/status/{request_id}")
async def get_collection_status(
    request_id: str,
    collector_service: CollectorService = Depends()
) -> CollectionStatusResponse:
    """
    수집 상태 확인 엔드포인트
    - 요청 ID로 수집 상태를 조회
    """
    try:
        # Validate request_id format
        try:
            UUID(request_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid request ID format"
            )
        
        status = await collector_service.get_status(request_id)
        if status is None:
            raise HTTPException(
                status_code=404,
                detail=f"No collection status found for request ID: {request_id}"
            )
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Router] Error getting collection status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get collection status: {str(e)}"
        )

@router.get("/detailed-status/{request_id}")
async def get_detailed_collection_status(
    request_id: str,
    collector_service: CollectorService = Depends()
):
    """
    상세 수집 상태 확인 엔드포인트
    - 요청 ID로 수집 상태와 최신 수집 항목 정보를 조회
    """
    try:
        # Validate request_id format
        try:
            UUID(request_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid request ID format"
            )
        
        # 기본 상태 조회
        status = await collector_service.get_status(request_id)
        if status is None:
            raise HTTPException(
                status_code=404,
                detail=f"No collection status found for request ID: {request_id}"
            )
        
        # 작업 정보 가져오기
        task = collector_service.tasks.get(request_id)
        if task is None:
            raise HTTPException(
                status_code=404,
                detail=f"Task not found for request ID: {request_id}"
            )
        
        # 상세 상태 정보 구성
        detailed_status = {
            **status.dict(),
            "latest_collected_item": task.latest_collected_item,
            "current_count": task.current_count
        }
        
        return detailed_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Router] Error getting detailed collection status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get detailed collection status: {str(e)}"
        )
