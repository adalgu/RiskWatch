"""
Collector Service - BackgroundTasks 방식 구현

RabbitMQ 대신 FastAPI BackgroundTasks로 비동기 수집 작업 처리
"""

import logging
import uuid
import pytz
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import BackgroundTasks
from pydantic import BaseModel
import httpx

from news_collector.collectors.metadata import MetadataCollector
from news_collector.collectors.comments import CommentCollector
from ..models.collector_models import CollectionStatusResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')

class TaskStatus:
    """작업 상태 정의"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class CollectionTask:
    """수집 작업 정보"""
    def __init__(self, task_id: str, task_type: str):
        """수집 작업 초기화"""
        self.task_id = task_id
        self.task_type = task_type  # "metadata" 또는 "comments"
        self.status = TaskStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.total_collected = 0
        self.error: Optional[str] = None
        self.progress = 0
        self.result: Optional[Dict[str, Any]] = None
        # 실시간 수집 현황 정보
        self.current_count = 0  # 현재까지 수집된 항목 수
        self.latest_collected_item = None  # 최근 수집 항목 정보

class CollectorService:
    """수집 서비스 - RabbitMQ 대신 BackgroundTasks 사용"""
    
    def __init__(self):
        """초기화"""
        self.tasks: Dict[str, CollectionTask] = {}
        self._initialized = False
        self.storage_url = "http://news_storage:8000/api/storage"
        
    async def init(self):
        """서비스 초기화"""
        if not self._initialized:
            logger.info("CollectorService 초기화 중...")
            self._initialized = True
            logger.info("CollectorService 초기화 완료")
    
    async def collect_metadata(
        self,
        keyword: str,
        method: str,
        start_date: datetime,
        end_date: datetime,
        max_articles: int = 100,
        min_delay: int = 1,
        max_delay: int = 3,
        batch_size: int = 30,
        is_test: bool = False,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> CollectionStatusResponse:
        """메타데이터 수집 요청 처리 및 백그라운드 작업 등록"""
        # 요청 ID 생성
        request_id = str(uuid.uuid4())
        
        # 작업 정보 생성
        task = CollectionTask(request_id, "metadata")
        
        # 작업 등록
        self.tasks[request_id] = task
        
        # 파라미터 저장
        task.params = {
            "keyword": keyword,
            "method": method,
            "start_date": start_date,
            "end_date": end_date,
            "max_articles": max_articles,
            "min_delay": min_delay,
            "max_delay": max_delay,
            "batch_size": batch_size,
            "is_test": is_test
        }
        
        # 백그라운드 태스크 등록
        if background_tasks:
            background_tasks.add_task(
                self.run_metadata_collection_task, 
                task=task,
                background_tasks=background_tasks
            )
            logger.info(f"메타데이터 수집 백그라운드 작업 등록 (ID: {request_id})")
        
        # 상태 응답 반환
        return CollectionStatusResponse(
            request_id=request_id,
            status=task.status,
            started_at=task.started_at,
            completed_at=task.completed_at,
            total_collected=task.total_collected,
            error=task.error,
            progress=task.progress,
            task_type="metadata"
        )
    
    async def collect_comments(
        self,
        article_urls: List[str],
        min_delay: int = 1,
        max_delay: int = 3,
        batch_size: int = 10,
        is_test: bool = False,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> CollectionStatusResponse:
        """댓글 수집 요청 처리 및 백그라운드 작업 등록"""
        # 요청 ID 생성
        request_id = str(uuid.uuid4())
        
        # 작업 정보 생성
        task = CollectionTask(request_id, "comments")
        
        # 작업 등록
        self.tasks[request_id] = task
        
        # 파라미터 저장
        task.params = {
            "article_urls": article_urls,
            "min_delay": min_delay,
            "max_delay": max_delay,
            "batch_size": batch_size,
            "is_test": is_test
        }
        
        # 백그라운드 태스크 등록
        if background_tasks:
            background_tasks.add_task(
                self.run_comment_collection_task, 
                task=task,
                background_tasks=background_tasks
            )
            logger.info(f"댓글 수집 백그라운드 작업 등록 (ID: {request_id})")
        
        # 상태 응답 반환
        return CollectionStatusResponse(
            request_id=request_id,
            status=task.status,
            started_at=task.started_at,
            completed_at=task.completed_at,
            total_collected=task.total_collected,
            error=task.error,
            progress=task.progress,
            task_type="comments"
        )
    
    async def get_status(self, request_id: str) -> Optional[CollectionStatusResponse]:
        """수집 상태 조회"""
        task = self.tasks.get(request_id)
        if not task:
            return None
        
        return CollectionStatusResponse(
            request_id=task.task_id,
            status=task.status,
            started_at=task.started_at,
            completed_at=task.completed_at,
            total_collected=task.total_collected,
            error=task.error,
            progress=task.progress,
            task_type=task.task_type
        )
    
    async def run_metadata_collection_task(self, task: CollectionTask, background_tasks: BackgroundTasks):
        """메타데이터 수집 백그라운드 작업 실행"""
        try:
            # 작업 시작
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(KST)
            
            logger.info(f"메타데이터 수집 작업 시작 (ID: {task.task_id})")
            
            # 메타데이터 수집기 초기화
            collector = MetadataCollector()
            
            # 메타데이터 수집 실행
            # 프로그레스 콜백을 추가하여 메타데이터 수집기로 전달
            collection_params = task.params.copy()
            collection_params["progress_callback"] = lambda article, count, total: self._update_metadata_progress(task, article, count, total)
            
            result = await collector.collect(**collection_params)
            
            # 작업 결과 저장
            task.result = result
            task.total_collected = len(result.get("articles", []))
            task.current_count = task.total_collected
            task.progress = 100
            
            # News Storage API로 메타데이터 저장
            storage_success = await self._store_metadata_to_storage(result)
            
            if not storage_success:
                logger.error(f"메타데이터 저장 실패 (ID: {task.task_id})")
                task.status = TaskStatus.FAILED
                task.error = "메타데이터 저장 API 호출 실패"
                task.completed_at = datetime.now(KST)
                return
            
            # 자동 댓글 수집 여부 확인
            if task.params.get("auto_collect_comments", False) and task.total_collected > 0:
                await self._schedule_comment_collection(result, background_tasks)
            
            # 작업 완료
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(KST)
            
            logger.info(f"메타데이터 수집 작업 완료 (ID: {task.task_id}, 수집: {task.total_collected}개)")
            
        except Exception as e:
            # 작업 실패
            logger.error(f"메타데이터 수집 작업 실패 (ID: {task.task_id}): {str(e)}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(KST)
    
    async def run_comment_collection_task(self, task: CollectionTask, background_tasks: BackgroundTasks):
        """댓글 수집 백그라운드 작업 실행"""
        try:
            # 작업 시작
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(KST)
            
            logger.info(f"댓글 수집 작업 시작 (ID: {task.task_id})")
            
            # 댓글 수집기 초기화
            collector = CommentCollector()
            
            # 파라미터 준비
            article_urls = task.params.get("article_urls", [])
            min_delay = task.params.get("min_delay", 1)
            max_delay = task.params.get("max_delay", 3)
            
            # 각 기사별 댓글 수집
            total_comments = 0
            article_count = len(article_urls)
            
            for i, article_url in enumerate(article_urls):
                try:
                    # 진행 상황 업데이트
                    task.progress = int((i / article_count) * 100)
                    task.current_count = total_comments
                    
                    # 댓글 수집
                    logger.info(f"기사 댓글 수집 중: {article_url}")
                    comment_result = await collector.collect(
                        article_url=article_url,
                        min_delay=min_delay,
                        max_delay=max_delay,
                        progress_callback=lambda comment, count, total: self._update_comment_progress(task, comment, article_url, count, total, i+1, article_count)
                    )
                    
                    # 댓글 개수 계산
                    comments_count = len(comment_result.get("comments", []))
                    total_comments += comments_count
                    task.current_count = total_comments
                    
                    # 스토리지에 저장
                    storage_success = await self._store_comments_to_storage(comment_result, article_url)
                    
                    if storage_success:
                        logger.info(f"기사 댓글 {comments_count}개 수집 및 저장 완료: {article_url}")
                    else:
                        logger.warning(f"기사 댓글 {comments_count}개 수집은 성공했으나 저장 실패: {article_url}")
                        # 저장 실패해도 다음 기사는 계속 처리
                    
                except Exception as e:
                    logger.error(f"기사 댓글 수집 실패: {article_url}: {str(e)}")
                    continue
            
            # 작업 완료
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(KST)
            task.total_collected = total_comments
            task.progress = 100
            
            logger.info(f"댓글 수집 작업 완료 (ID: {task.task_id}, 수집: {total_comments}개)")
            
        except Exception as e:
            # 작업 실패
            logger.error(f"댓글 수집 작업 실패 (ID: {task.task_id}): {str(e)}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(KST)
    
    async def _store_metadata_to_storage(self, metadata_result: Dict[str, Any]) -> bool:
        """메타데이터를 Storage API로 저장 - 성공하면 True, 실패하면 False 반환"""
        try:
            # Storage API URL
            api_url = f"{self.storage_url}/metadata"
            
            logger.info(f"메타데이터 저장 요청 전송: {api_url}")
            logger.debug(f"메타데이터 내용: {len(metadata_result.get('articles', []))}개 기사")
            
            # API 요청 - 타임아웃 설정 추가
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.debug("httpx 클라이언트 생성 완료, 요청 전송 중...")
                response = await client.post(api_url, json=metadata_result)
                logger.debug(f"응답 수신: 상태 코드 {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"메타데이터 저장 API 오류: {response.status_code} - {response.text}")
                    return False
                
                response_data = response.json()
                logger.info(f"메타데이터 저장 성공: {response_data}")
                return True
                
        except httpx.TimeoutException:
            logger.error("메타데이터 저장 API 요청 타임아웃", exc_info=True)
            return False
        except httpx.ConnectError:
            logger.error("메타데이터 저장 API 연결 오류: news_storage 서비스에 연결할 수 없음", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"메타데이터 저장 오류: {str(e)}", exc_info=True)
            return False
    
    async def _store_comments_to_storage(self, comment_result: Dict[str, Any], article_url: str) -> bool:
        """댓글을 Storage API로 저장 - 성공하면 True, 실패하면 False 반환"""
        try:
            # 저장 데이터 준비
            storage_data = {
                "article_url": article_url,
                "comments": comment_result.get("comments", []),
                "stats": comment_result.get("stats", {}),
                "total_count": comment_result.get("total_count", 0),
                "collected_at": comment_result.get("collected_at")
            }
            
            # Storage API URL
            api_url = f"{self.storage_url}/comments"
            
            logger.info(f"댓글 저장 요청 전송: {api_url}")
            logger.debug(f"댓글 데이터: {len(storage_data.get('comments', []))}개 댓글")
            
            # API 요청 - 타임아웃 설정 추가
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.debug("httpx 클라이언트 생성 완료, 요청 전송 중...")
                response = await client.post(api_url, json=storage_data)
                logger.debug(f"응답 수신: 상태 코드 {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"댓글 저장 API 오류: {response.status_code} - {response.text}")
                    return False
                
                response_data = response.json()
                logger.info(f"댓글 저장 성공: {response_data}")
                return True
                
        except httpx.TimeoutException:
            logger.error("댓글 저장 API 요청 타임아웃", exc_info=True)
            return False
        except httpx.ConnectError:
            logger.error("댓글 저장 API 연결 오류: news_storage 서비스에 연결할 수 없음", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"댓글 저장 오류: {str(e)}", exc_info=True)
            return False
    
    async def _schedule_comment_collection(self, metadata_result: Dict[str, Any], background_tasks: BackgroundTasks) -> None:
        """메타데이터 수집 후 자동으로 댓글 수집 스케줄링"""
        try:
            # 기사 URL 추출
            articles = metadata_result.get("articles", [])
            article_urls = [article["naver_link"] for article in articles if article.get("naver_link")]
            
            if not article_urls:
                logger.warning("자동 댓글 수집을 위한 기사 URL이 없음")
                return
            
            # 댓글 수집 요청
            logger.info(f"자동 댓글 수집 시작 ({len(article_urls)}개 기사)")
            
            status = await self.collect_comments(
                article_urls=article_urls,
                min_delay=1,
                max_delay=3,
                background_tasks=background_tasks
            )
            
            logger.info(f"자동 댓글 수집 요청 완료 (ID: {status.request_id})")
            
        except Exception as e:
            logger.error(f"자동 댓글 수집 스케줄링 오류: {str(e)}", exc_info=True)
    
    def _update_metadata_progress(self, task: CollectionTask, article: Dict[str, Any], count: int, total: int) -> None:
        """메타데이터 수집 진행 상황 업데이트"""
        if not article:
            return
            
        task.current_count = count
        task.progress = int((count / max(total, 1)) * 100) if total > 0 else 0
        
        # 최근 수집 항목 정보 저장
        task.latest_collected_item = {
            "title": article.get("title", "제목 없음"),
            "url": article.get("original_url", "URL 없음"),
            "publisher": article.get("publisher", "출처 없음"),
            "collected_at": datetime.now(KST).isoformat()
        }
        
        logger.info(f"메타데이터 수집 진행: {count}/{total} ({task.progress}%) - {article.get('title', '제목 없음')}")
    
    def _update_comment_progress(self, task: CollectionTask, comment: Dict[str, Any], article_url: str, count: int, total: int, article_index: int, article_count: int) -> None:
        """댓글 수집 진행 상황 업데이트"""
        if not comment:
            return
            
        # 전체 진행도 계산 (기사 진행도 + 현재 기사 내 댓글 진행도)
        article_progress = (article_index - 1) / article_count
        comment_progress = (count / max(total, 1)) / article_count if total > 0 else 0
        task.progress = int((article_progress + comment_progress) * 100)
        
        # 최근 수집 항목 정보 저장
        task.latest_collected_item = {
            "comment": comment.get("content", "내용 없음")[:100],
            "article_url": article_url,
            "user_id": comment.get("user_id", "익명"),
            "collected_at": datetime.now(KST).isoformat(),
            "article_index": article_index,
            "article_count": article_count,
            "comment_index": count,
            "comment_total": total
        }
        
        logger.info(f"댓글 수집 진행: 기사 {article_index}/{article_count}, 댓글 {count}/{total} - {comment.get('content', '내용 없음')[:50]}")
    
    async def cleanup(self) -> None:
        """리소스 정리"""
        logger.info("CollectorService 리소스 정리")
        # 오래된 작업 정리
        old_tasks = [
            task_id for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
            and task.completed_at and (datetime.now(KST) - task.completed_at).days > 1
        ]
        
        for task_id in old_tasks:
            del self.tasks[task_id]
            
        logger.info(f"{len(old_tasks)}개 오래된 작업 정리 완료")
