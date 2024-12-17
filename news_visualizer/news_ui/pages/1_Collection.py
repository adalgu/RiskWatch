import os
import streamlit as st
import time
from datetime import datetime
import json
import logging
from pathlib import Path
import requests
import pytz

# Configure logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "collector.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('collection')

# KST 타임존 설정
KST = pytz.timezone('Asia/Seoul')

def render_metadata_collection_form():
    """메타데이터 수집 요청 폼 렌더링"""
    st.header("메타데이터 수집 요청")
    
    with st.form("metadata_collection_form"):
        keyword = st.text_input("검색 키워드", value="카카오모빌리티", placeholder="예: 카카오")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("시작일", value=datetime.today())
        with col2:
            end_date = st.date_input("종료일", value=datetime.today())
        
        # 추가 파라미터
        method = st.selectbox("수집 방법", options=["SEARCH", "API"], help="SEARCH: 네이버 검색, API: 네이버 뉴스 API")
        
        col3, col4 = st.columns(2)
        with col3:
            min_delay = st.number_input("최소 딜레이 (초)", min_value=0, max_value=10, value=0, help="요청 사이의 최소 대기 시간")
        with col4:
            max_delay = st.number_input("최대 딜레이 (초)", min_value=1, max_value=10, value=2, help="요청 사이의 최대 대기 시간")
        
        batch_size = st.number_input("배치 크기", min_value=10, max_value=20000, value=10000, help="한 번에 수집할 기사 수")
        
        # 자동 댓글 수집 옵션 추가
        auto_collect_comments = st.checkbox("메타데이터 수집 후 자동으로 댓글 수집", value=False)
        
        submitted = st.form_submit_button("수집 시작")
        
        if submitted:
            if keyword and start_date and end_date and min_delay <= max_delay:
                # FastAPI 서버로 수집 요청
                success, request_time = send_collection_request(
                    keyword=keyword,
                    start_date=start_date,
                    end_date=end_date,
                    method=method,
                    min_delay=min_delay,
                    max_delay=max_delay,
                    batch_size=batch_size,
                    auto_collect_comments=auto_collect_comments,
                    collection_type="metadata"
                )
                if success:
                    st.success("수집 요청이 성공적으로 전송되었습니다.")
                    logger.info(f"수집 요청 성공 - 키워드: {keyword}, 시작일: {start_date}, 종료일: {end_date}")
                    # 세션 상태에 요청 시간 저장
                    if 'last_request_time' not in st.session_state:
                        st.session_state['last_request_time'] = {}
                    st.session_state['last_request_time'] = request_time
                else:
                    st.error("수집 요청 전송 중 오류가 발생했습니다.")
            else:
                if min_delay > max_delay:
                    st.warning("최소 딜레이는 최대 딜레이보다 작거나 같아야 합니다.")
                else:
                    st.warning("모든 필드를 입력해주세요.")

def render_comment_collection_form():
    """댓글 수집 요청 폼 렌더링"""
    st.header("댓글 수집 요청")
    
    with st.form("comment_collection_form"):
        keyword = st.text_input("검색 키워드", value="카카오모빌리티", placeholder="예: 카카오",
                                help="이 키워드로 수집된 메타데이터의 네이버 뉴스 URL에서 댓글을 수집합니다")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("시작일", value=datetime.today(), help="이 기간 내에 발행된 기사의 댓글만 수집합니다")
        with col2:
            end_date = st.date_input("종료일", value=datetime.today())
        
        col3, col4 = st.columns(2)
        with col3:
            min_delay = st.number_input("최소 딜레이 (초)", min_value=0, max_value=10, value=0, help="요청 사이의 최소 대기 시간")
        with col4:
            max_delay = st.number_input("최대 딜레이 (초)", min_value=1, max_value=10, value=3, help="요청 사이의 최대 대기 시간")
        
        submitted = st.form_submit_button("댓글 수집 시작")
        
        if submitted:
            if keyword and start_date and end_date and min_delay <= max_delay:
                # FastAPI 서버로 수집 요청
                success, request_time = send_collection_request(
                    keyword=keyword,
                    start_date=start_date,
                    end_date=end_date,
                    method="COMMENTS",
                    min_delay=min_delay,
                    max_delay=max_delay,
                    collection_type="comments"
                )
                if success:
                    st.success("댓글 수집 요청이 성공적으로 전송되었습니다.")
                    logger.info(f"댓글 수집 요청 성공 - 키워드: {keyword}, 시작일: {start_date}, 종료일: {end_date}")
                    # 세션 상태에 요청 시간 저장
                    if 'last_request_time' not in st.session_state:
                        st.session_state['last_request_time'] = {}
                    st.session_state['last_request_time'] = request_time
                else:
                    st.error("댓글 수집 요청 전송 중 오류가 발생했습니다.")
            else:
                if min_delay > max_delay:
                    st.warning("최소 딜레이는 최대 딜레이보다 작거나 같아야 합니다.")
                else:
                    st.warning("모든 필드를 입력해주세요.")

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
        st.error(f"수집 요청 발행 실패: {str(e)}")
        return False, None

def render_collection_logs():
    """수집 로그 렌더링"""
    st.header("수집 로그")
    
    # 로그 파일 경로 설정
    log_file_path = log_file
    
    # 자동 새로고침 토글
    auto_refresh = st.checkbox("자동 새로고침", value=False, help="5초마다 로그를 자동으로 새로고침합니다")
    
    if st.button("로그 새로고침"):
        st.rerun()
    
    # 최근 로그 가져오기
    if 'last_request_time' in st.session_state:
        logs = get_recent_logs(log_file_path, st.session_state['last_request_time'])
        if logs:
            log_text = ''.join(logs)
            st.text_area("실시간 수집 로그", log_text, height=400)
        else:
            st.info("아직 수집 로그가 없습니다. 수집을 시작하면 여기에 로그가 표시됩니다.")
    else:
        st.info("수집 요청을 시작하면 여기에 로그가 표시됩니다.")
    
    # 자동 새로고침
    if auto_refresh:
        time.sleep(5)
        st.rerun()

def get_recent_logs(log_path, start_time=None):
    """로그 파일에서 최근 로그 가져오기"""
    try:
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                logs = f.readlines()
            
            # 시작 시간 이후의 로그 필터링
            if start_time and isinstance(start_time, datetime):
                filtered_logs = []
                for log in logs:
                    # JSON 메시지 내용은 건너뛰기
                    if log.strip().startswith('{') or log.strip().startswith('"'):
                        continue
                    
                    try:
                        # 로그 형식이 "2024-12-12 09:01:58,184 - collection - INFO - 메시지" 형태인지 확인
                        parts = log.split(' - ')
                        if len(parts) >= 4:  # 최소 4개의 부분이 있어야 함
                            log_time_str = parts[0].strip()
                            log_time = datetime.strptime(log_time_str, '%Y-%m-%d %H:%M:%S,%f')
                            if log_time >= start_time:
                                filtered_logs.append(log)
                    except (ValueError, IndexError):
                        continue
                return filtered_logs
            
            # 시작 시간이 없으면 마지막 100줄 반환
            return logs[-100:]
        else:
            logger.warning(f"로그 파일이 존재하지 않습니다: {log_path}")
            return []
    except Exception as e:
        logger.error(f"로그 파일 읽기 오류: {str(e)}", exc_info=True)
        return []

def main():
    """데이터 수집 인터페이스 페이지 실행 함수"""
    st.title("데이터 수집 인터페이스")
    
    # 탭 생성
    metadata_tab, comments_tab = st.tabs(["메타데이터 수집", "댓글 수집"])
    
    with metadata_tab:
        render_metadata_collection_form()
        
    with comments_tab:
        render_comment_collection_form()
    
    st.markdown("---")
    render_collection_logs()

if __name__ == "__main__":
    main()
