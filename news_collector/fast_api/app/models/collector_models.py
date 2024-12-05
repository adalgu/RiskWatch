from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class CollectionMethod(str, Enum):
    API = "API"
    SEARCH = "SEARCH"
    COMMENTS = "COMMENTS"

class CollectionRequest(BaseModel):
    method: CollectionMethod
    keyword: str
    start_date: datetime
    end_date: datetime

class CollectionStatus(BaseModel):
    id: str
    status: str
    keyword: str
    progress: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None

class ResourceUsage(BaseModel):
    selenium_nodes: int
    active_collections: int
    queued_collections: int
    rabbitmq_queue_size: int
    cpu_usage: float
    memory_usage: float

class CollectorResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None
