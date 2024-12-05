### 2.3. 데이터 수집 인터페이스 페이지 (`pages/1_Collection.py`) 생성

# 데이터 수집 인터페이스(데이터 수집 요청, 수집 로그)를 별도의 페이지로 분리합니다.

# pages/1_Collection.py

import sys
import os

# 'modules' 디렉토리를 Python 경로에 추가
modules_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'modules'))
if modules_path not in sys.path:
    sys.path.append(modules_path)

from database import Database
from logging_config import get_logger
from decorators import handle_exceptions

import streamlit as st
import pandas as pd
import time
from datetime import datetime
import json
import pika

logger = get_logger('collection')

def render_collection_form():
    """수집 요청 폼 렌더링"""
    st.header("데이터 수집 요청")
    
    with st.form("collection_form"):
        keyword = st.text_input("검색 키워드", placeholder="예: 삼성전자")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("시작일", value=datetime.today())
        with col2:
            end_date = st.date_input("종료일", value=datetime.today())
            
        # 추가 파라미터
        method = st.selectbox("수집 방법", options=["SEARCH", "API"], help="SEARCH: 네이버 검색, API: 네이버 뉴스 API")
        
        col3, col4 = st.columns(2)
        with col3:
            min_delay = st.number_input("최소 딜레이 (초)", min_value=1, max_value=10, value=1, help="요청 사이의 최소 대기 시간")
        with col4:
            max_delay = st.number_input("최대 딜레이 (초)", min_value=1, max_value=10, value=3, help="요청 사이의 최대 대기 시간")
            
        batch_size = st.number_input("배치 크기", min_value=10, max_value=10000, value=100, help="한 번에 수집할 기사 수")
            
        submitted = st.form_submit_button("수집 시작")
        
        if submitted:
            if keyword and start_date and end_date and min_delay <= max_delay:
                # 수집 요청 로직 (예시: RabbitMQ에 메시지 발행)
                success, request_time = publish_collection_request(
                    keyword=keyword,
                    start_date=start_date,
                    end_date=end_date,
                    method=method,
                    min_delay=min_delay,
                    max_delay=max_delay,
                    batch_size=batch_size
                )
                if success:
                    st.success("수집 요청이 성공적으로 전송되었습니다.")
                    # 세션 상태에 요청 시간 저장
                    st.session_state['last_request_time'] = request_time
                else:
                    st.error("수집 요청 전송 중 오류가 발생했습니다.")
            else:
                if min_delay > max_delay:
                    st.warning("최소 딜레이는 최대 딜레이보다 작거나 같아야 합니다.")
                else:
                    st.warning("모든 필드를 입력해주세요.")

def publish_collection_request(keyword, start_date, end_date, method, min_delay, max_delay, batch_size):
    """RabbitMQ에 수집 요청 메시지 발행"""
    try:
        RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
        parameters = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # 큐 선언
        channel.queue_declare(queue='collection_requests', durable=True)

        # 메시지 준비
        message = {
            'keyword': keyword,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'method': method,
            'min_delay': min_delay,
            'max_delay': max_delay,
            'batch_size': batch_size,
            'request_time': datetime.now().isoformat()
        }

        # 메시지 발행
        channel.basic_publish(
            exchange='',
            routing_key='collection_requests',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # 메시지 지속성
            )
        )

        connection.close()
        return True, datetime.now()
    except Exception as e:
        st.error(f"수집 요청 발행 실패: {e}")
        return False, None

def render_collection_logs():
    """수집 로그 렌더링"""
    st.header("수집 로그")
    
    LOG_FILE_PATH = os.getenv('COLLECTOR_LOG_PATH', '/app/logs/collector.log')
    
    # 자동 새로고침 토글
    auto_refresh = st.checkbox("자동 새로고침", value=False, help="5초마다 로그를 자동으로 새로고침합니다")
    
    # 최근 로그 가져오기
    logs = get_recent_logs(LOG_FILE_PATH, st.session_state.get('last_request_time'))
    if logs:
        log_text = ''.join(logs)
        st.text_area("실시간 수집 로그", log_text, height=400)
    else:
        st.info("아직 수집 로그가 없습니다.")
    
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
            if start_time:
                filtered_logs = []
                for log in logs:
                    try:
                        log_time_str = log.split(' - ')[0]
                        log_time = datetime.strptime(log_time_str, '%Y-%m-%d %H:%M:%S,%f')
                        if log_time >= start_time:
                            filtered_logs.append(log)
                    except (ValueError, IndexError):
                        continue
                return filtered_logs
            
            # 시작 시간이 없으면 마지막 100줄 반환
            return logs[-100:]
    except Exception as e:
        st.error(f"로그 파일 읽기 오류: {e}")
        return []

def main():
    """데이터 수집 인터페이스 페이지 실행 함수"""
    st.title("데이터 수집 인터페이스(개발중)")
    
    render_collection_form()
    st.markdown("---")
    render_collection_logs()

if __name__ == "__main__":
    main()