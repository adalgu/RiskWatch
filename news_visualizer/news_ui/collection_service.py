import requests
import json
import logging
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

def send_collection_request(keyword, start_date, end_date, method, min_delay, max_delay, collection_type, batch_size=None, auto_collect_comments=False):
    """수집 요청 전송 (직접 API 호출 방식)"""
    try:
        # API 서버 URL 정의
        if collection_type == "metadata":
            # 메타데이터 수집 요청은 fast_api 서버로 전송
            api_url = f"http://fast_api:8000/api/v1/collectors/{collection_type}/start"
            
            # 날짜를 YYYY-MM-DD 형식으로 변환
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # 요청 데이터 준비
            request_data = {
                "keyword": keyword,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "method": method,
                "min_delay": min_delay,
                "max_delay": max_delay,
                "batch_size": batch_size,
                "auto_collect_comments": auto_collect_comments
            }
            
            # 요청 데이터 로깅
            logger.info(f"Sending metadata collection request: {json.dumps(request_data, ensure_ascii=False)}")
            
            # FastAPI 서버로 요청 전송
            response = requests.post(api_url, json=request_data)
            
        elif collection_type == "comments":
            # 이 부분에서는 fast_api 서버를 거치지 않고 직접 news_storage API를 호출할 수도 있지만
            # 일관성을 위해 메타데이터와 동일한 형태로 요청
            api_url = f"http://fast_api:8000/api/v1/collectors/{collection_type}/start"
            
            # 날짜를 YYYY-MM-DD 형식으로 변환
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # 요청 데이터 준비 - 댓글 수집은 날짜 범위로 메타데이터를 조회한 후 댓글 수집
            request_data = {
                "keyword": keyword,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "method": method,
                "min_delay": min_delay,
                "max_delay": max_delay
            }
            
            # 요청 데이터 로깅
            logger.info(f"Sending comment collection request: {json.dumps(request_data, ensure_ascii=False)}")
            
            # FastAPI 서버로 요청 전송
            response = requests.post(api_url, json=request_data)
        else:
            logger.error(f"Unknown collection type: {collection_type}")
            return False, None, None
            
        # 응답 처리
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"API 응답: {response_data}")
            
            # 요청 ID 추출
            request_id = response_data.get('request_id')
            if not request_id:
                logger.warning("응답에 request_id가 없습니다.")
            
            return True, datetime.now(), request_id
        else:
            logger.error(f"API 요청 실패: {response.status_code} - {response.text}")
            return False, None, None
            
    except Exception as e:
        logger.error(f"수집 요청 발행 실패: {str(e)}", exc_info=True)
        return False, None, None
        
def check_collection_status(request_id):
    """수집 상태 확인"""
    try:
        # 상태 확인 API URL
        api_url = f"http://fast_api:8000/api/v1/collectors/status/{request_id}"
        
        # API 요청
        response = requests.get(api_url)
        
        if response.status_code == 200:
            status_data = response.json()
            logger.info(f"상태 확인 응답: {status_data}")
            return status_data
        else:
            logger.error(f"상태 확인 실패: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"상태 확인 오류: {str(e)}", exc_info=True)
        return None

def check_collection_detailed_status(request_id):
    """수집 상세 상태 확인 - 실시간 수집 항목 정보 포함"""
    try:
        # 상세 상태 확인 API URL
        api_url = f"http://fast_api:8000/api/v1/collectors/detailed-status/{request_id}"
        
        # API 요청
        response = requests.get(api_url)
        
        if response.status_code == 200:
            status_data = response.json()
            logger.info(f"상세 상태 확인 응답: {status_data.get('current_count')}개 항목 수집됨")
            return status_data
        else:
            logger.error(f"상세 상태 확인 실패: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"상세 상태 확인 오류: {str(e)}", exc_info=True)
        return None
        
def get_article_stats(keyword=None, days=7):
    """기사 통계 조회"""
    try:
        # 통계 API URL
        api_url = "http://news_storage:8000/api/storage/stats"
        
        # 쿼리 파라미터
        params = {}
        if keyword:
            params["keyword"] = keyword
        params["days"] = days
        
        # API 요청
        response = requests.get(api_url, params=params)
        
        if response.status_code == 200:
            stats_data = response.json()
            logger.info(f"통계 조회 응답: {stats_data}")
            return stats_data
        else:
            logger.error(f"통계 조회 실패: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"통계 조회 오류: {str(e)}", exc_info=True)
        return None
