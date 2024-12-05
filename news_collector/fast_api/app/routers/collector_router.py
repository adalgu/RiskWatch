from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List
from app.models.collector_models import (
    CollectionRequest,
    CollectionStatus,
    ResourceUsage,
    CollectorResponse
)
from app.services.collector_service import CollectorService
from datetime import datetime

router = APIRouter(
    prefix="/collectors",
    tags=["collectors"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def api_root():
    return {"message": "API Root"}

@router.get("/metadata/start")
def metadata_start_endpoint():
    return {"status": "Metadata collection started"}

def get_collector_service():
    return CollectorService()

@router.post("/metadata/start", response_model=CollectorResponse)
async def start_metadata_collection(
    request: CollectionRequest,
    collector_service: CollectorService = Depends(get_collector_service)
):
    """메타데이터 수집 시작"""
    try:
        collection_id = await collector_service.start_collection(request, "metadata")
        return CollectorResponse(
            status="success",
            message="Metadata collection started",
            data={"request_id": collection_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/metadata/stop", response_model=CollectorResponse)
async def stop_metadata_collection(
    collection_id: str,
    collector_service: CollectorService = Depends(get_collector_service)
):
    """메타데이터 수집 중지"""
    try:
        success = await collector_service.stop_collection(collection_id)
        if success:
            return CollectorResponse(
                status="success",
                message=f"Metadata collection {collection_id} stopped"
            )
        raise HTTPException(status_code=400, detail="Failed to stop collection")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comments/start", response_model=CollectorResponse)
async def start_comments_collection(
    request: CollectionRequest,
    collector_service: CollectorService = Depends(get_collector_service)
):
    """댓글 수집 시작"""
    try:
        collection_id = await collector_service.start_collection(request, "comments")
        return CollectorResponse(
            status="success",
            message="Comments collection started",
            data={"request_id": collection_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comments/stop", response_model=CollectorResponse)
async def stop_comments_collection(
    collection_id: str,
    collector_service: CollectorService = Depends(get_collector_service)
):
    """댓글 수집 중지"""
    try:
        success = await collector_service.stop_collection(collection_id)
        if success:
            return CollectorResponse(
                status="success",
                message=f"Comments collection {collection_id} stopped"
            )
        raise HTTPException(status_code=400, detail="Failed to stop collection")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=List[CollectionStatus])
async def get_collectors_status(
    collection_id: str = None,
    collector_service: CollectorService = Depends(get_collector_service)
):
    """모든 수집기 상태 조회"""
    try:
        return await collector_service.get_collection_status(collection_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resources/usage", response_model=ResourceUsage)
async def get_resource_usage(
    collector_service: CollectorService = Depends(get_collector_service)
):
    """리소스 사용량 조회"""
    try:
        return await collector_service.get_resource_usage()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pause", response_model=CollectorResponse)
async def pause_all_collections(
    collector_service: CollectorService = Depends(get_collector_service)
):
    """전체 수집 작업 일시 정지"""
    try:
        # 모든 활성 수집 작업에 대해 중지 요청
        active_collections = await collector_service.get_collection_status()
        for collection in active_collections:
            if collection.status == "running":
                await collector_service.stop_collection(collection.id)
        
        return CollectorResponse(
            status="success",
            message="All collections paused"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resume", response_model=CollectorResponse)
async def resume_collections(
    collector_service: CollectorService = Depends(get_collector_service)
):
    """일시 정지된 작업 재개"""
    try:
        # TODO: 일시 정지된 작업 재개 로직 구현
        return CollectorResponse(
            status="success",
            message="Collections resumed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
