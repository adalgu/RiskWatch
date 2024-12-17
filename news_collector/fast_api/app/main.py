from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Annotated
from prometheus_client import make_asgi_app, Counter, Gauge, Histogram
import psutil
import logging
import json

from app.routers import collector_router
from app.services.collector_service import CollectorService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'request_count',
    'Number of requests received',
    ['method', 'endpoint', 'status_code']
)

ACTIVE_COLLECTIONS = Gauge(
    'active_collections',
    'Number of active collection tasks'
)

COLLECTION_DURATION = Histogram(
    'collection_duration_seconds',
    'Time spent on collection tasks',
    ['collection_type']
)

SYSTEM_CPU_USAGE = Gauge(
    'system_cpu_usage',
    'System CPU usage percentage'
)

SYSTEM_MEMORY_USAGE = Gauge(
    'system_memory_usage',
    'System memory usage percentage'
)

# Create a single instance of CollectorService to be used throughout the application
collector_service = CollectorService()

app = FastAPI(
    title="RiskWatch API",
    description="News Collector API for RiskWatch",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# 서비스 의존성
async def get_collector_service():
    if not collector_service._initialized:
        await collector_service.init()
    return collector_service

# 라우터 등록
app.include_router(
    collector_router.router,
    prefix="/api/v1",
    dependencies=[Depends(get_collector_service)]  # Ensure service is initialized
)

@app.get("/")
def root():
    return {"message": "Welcome to RiskWatch"}

@app.get("/health")
@app.head("/health")
async def health_check():
    """
    헬스 체크 엔드포인트
    """
    return {"status": "healthy", "version": "1.0.0"}

@app.on_event("startup")
async def startup_event():
    """
    애플리케이션 시작 시 실행되는 이벤트 핸들러
    """
    try:
        # Initialize the global CollectorService instance
        await collector_service.init()
        logger.info("Successfully initialized CollectorService")
        
        # 시스템 메트릭 초기화
        SYSTEM_CPU_USAGE.set(psutil.cpu_percent())
        memory = psutil.virtual_memory()
        SYSTEM_MEMORY_USAGE.set(memory.percent)
    except Exception as e:
        logger.error(f"Failed to initialize CollectorService: {str(e)}")
        raise

@app.on_event("startup")
async def print_routes():
    from fastapi.routing import APIRoute
    print("Registered routes:")
    for route in app.routes:
        if isinstance(route, APIRoute):
            print(f"Path: {route.path}, Methods: {route.methods}")
        else:
            print(f"Path: {route.path}, Type: {type(route)}")

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """
    요청 메트릭을 수집하고 로깅하는 미들웨어
    """
    # 요청 본문 로깅
    if request.method == "POST":
        try:
            body = await request.body()
            if body:
                body_str = body.decode()
                logger.info(f"[Middleware] Request body: {body_str}")
                # 요청 본문을 다시 설정
                await request.body()
        except Exception as e:
            logger.error(f"[Middleware] Error reading request body: {str(e)}")

    try:
        logger.info(f"[Middleware] Processing request to {request.url.path}")
        response = await call_next(request)
        logger.info(f"[Middleware] Response status code: {response.status_code}")
        
        # 422 에러 발생 시 상세 로깅
        if response.status_code == 422:
            logger.error(f"[Middleware] Validation error occurred for request to {request.url.path}")
            # 응답 본문 로깅
            try:
                response_body = [chunk async for chunk in response.body_iterator]
                response_body = b"".join(response_body)
                logger.error(f"[Middleware] Validation error details: {response_body.decode()}")
                # 응답 본문 재설정
                response.body_iterator = iter([response_body])
            except Exception as e:
                logger.error(f"[Middleware] Error reading response body: {str(e)}")

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()
        
        return response
    except Exception as e:
        logger.error(f"[Middleware] Error in middleware: {str(e)}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """
    애플리케이션 종료 시 실행되는 이벤트 핸들러
    """
    try:
        # Use the global collector_service instance
        await collector_service.cleanup()
        logger.info("Successfully cleaned up CollectorService")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        # Log the error but don't raise it to ensure other cleanup tasks can proceed
        # and to prevent the shutdown process from being interrupted

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
