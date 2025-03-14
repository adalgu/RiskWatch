import requests
import json
import logging
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

def send_collection_request(keyword, start_date, end_date, method, min_delay, max_delay, collection_type, batch_size=None, auto_collect_comments=False):
    """FastAPI 서버로 수집 요청 전송"""
    try:
        # FastAPI 서버 URL
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
            "max_delay": max_delay
        }
        
        # 메타데이터 수집인 경우 추가 파라미터
        if collection_type == "metadata":
            request_data["batch_size"] = batch_size
            request_data["auto_collect_comments"] = auto_collect_comments
        
        # 요청 데이터 로깅
        logger.info(f"Sending request to FastAPI: {json.dumps(request_data, ensure_ascii=False)}")
        
        # FastAPI 서버로 요청 전송
        response = requests.post(api_url, json=request_data)
        
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"FastAPI 응답: {response_data}")
            return True, datetime.now()
        else:
            logger.error(f"FastAPI 요청 실패: {response.status_code} - {response.text}")
            return False, None
    except Exception as e:
        logger.error(f"수집 요청 발행 실패: {str(e)}", exc_info=True)
        return False, None
