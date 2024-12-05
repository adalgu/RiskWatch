from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Annotated
from prometheus_client import make_asgi_app, Counter, Gauge, Histogram
import psutil

from app.routers import collector_router
from app.services.collector_service import CollectorService

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
def get_collector_service():
    return CollectorService()

# 라우터 등록
app.include_router(
    collector_router.router,
    prefix="/api/v1"
    # dependencies=[Depends(get_collector_service)]
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
    # 시스템 메트릭 초기화
    SYSTEM_CPU_USAGE.set(psutil.cpu_percent())
    memory = psutil.virtual_memory()
    SYSTEM_MEMORY_USAGE.set(memory.percent)

@app.on_event("startup")
async def print_routes():
    from fastapi.routing import APIRoute
    print("Registered routes:")
    for route in app.routes:
        if isinstance(route, APIRoute):  # APIRoute인 경우에만 methods 속성을 접근
            print(f"Path: {route.path}, Methods: {route.methods}")
        else:
            print(f"Path: {route.path}, Type: {type(route)}")

@app.middleware("http")
async def metrics_middleware(request, call_next):
    """
    요청 메트릭을 수집하는 미들웨어
    """
    response = await call_next(request)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    return response

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
