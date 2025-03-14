import streamlit as st
import pandas as pd
import requests
import json
import time
import os
import sys
import logging
from datetime import datetime, timedelta

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.database import Database
from collection_service import send_collection_request
from logging_config import setup_logging

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

# 로그 파일 경로
log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "collection.log")

def setup_page():
    """페이지 설정"""
    st.set_page_config(
        page_title="데이터 수집",
        page_icon="📊",
        layout="wide"
    )
    
    # 사이드바 설정
    st.sidebar.title("데이터 수집")
    st.sidebar.info(
        """
        이 페이지에서는 키워드 기반으로 뉴스 기사와 댓글을 수집할 수 있습니다.
        
        - **메타데이터 수집**: 키워드로 뉴스 기사 메타데이터를 수집합니다.
        - **댓글 수집**: 네이버 뉴스 기사의 댓글을 수집합니다.
        """
    )

def get_db_connection():
    """데이터베이스 연결 객체 반환"""
    try:
        db = Database()
        return db
    except Exception as e:
        st.error(f"데이터베이스 연결 오류: {str(e)}")
        logger.error(f"데이터베이스 연결 오류: {str(e)}", exc_info=True)
        return None

def get_collection_status(db):
    """수집 상태 정보 가져오기"""
    try:
        # 최근 수집된 기사 수
        query = """
            SELECT COUNT(*) 
            FROM articles 
            WHERE collected_at > NOW() - INTERVAL '24 hours'
        """
        recent_articles = db.session.execute(query).scalar() or 0
        
        # 최근 수집된 댓글 수
        query = """
            SELECT COUNT(*) 
            FROM comments 
            WHERE collected_at > NOW() - INTERVAL '24 hours'
        """
        recent_comments = db.session.execute(query).scalar() or 0
        
        # 전체 기사 수
        query = "SELECT COUNT(*) FROM articles"
        total_articles = db.session.execute(query).scalar() or 0
        
        # 전체 댓글 수
        query = "SELECT COUNT(*) FROM comments"
        total_comments = db.session.execute(query).scalar() or 0
        
        # 최근 수집 작업
        query = """
            SELECT main_keyword, collected_at
            FROM articles
            ORDER BY collected_at DESC
            LIMIT 1
        """
        last_collection = db.session.execute(query).fetchone()
        
        return {
            "recent_articles": recent_articles,
            "recent_comments": recent_comments,
            "total_articles": total_articles,
            "total_comments": total_comments,
            "last_collection": last_collection
        }
    except Exception as e:
        logger.error(f"수집 상태 조회 오류: {str(e)}", exc_info=True)
        return None

def render_collection_status(db):
    """수집 상태 표시"""
    st.subheader("수집 상태")
    
    if db is None:
        st.warning("데이터베이스에 연결할 수 없습니다. 상태를 표시할 수 없습니다.")
        return
    
    status = get_collection_status(db)
    if status is None:
        st.warning("수집 상태를 가져올 수 없습니다.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("최근 24시간 기사", f"{status['recent_articles']:,}개")
    
    with col2:
        st.metric("최근 24시간 댓글", f"{status['recent_comments']:,}개")
    
    with col3:
        st.metric("전체 기사", f"{status['total_articles']:,}개")
    
    with col4:
        st.metric("전체 댓글", f"{status['total_comments']:,}개")
    
    if status['last_collection']:
        st.info(f"최근 수집: {status['last_collection'][0]} ({status['last_collection'][1]})")

def render_metadata_collection_form():
    """메타데이터 수집 폼 렌더링"""
    st.header("메타데이터 수집")
    
    with st.form("metadata_collection_form"):
        # 키워드 입력
        keyword = st.text_input("검색 키워드", help="수집할 뉴스 기사의 검색 키워드를 입력하세요.")
        
        # 날짜 범위 선택
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("시작일", datetime.now() - timedelta(days=7))
        with col2:
            end_date = st.date_input("종료일", datetime.now())
        
        # 수집 방법 선택
        method = st.selectbox(
            "수집 방법",
            ["naver_news_search", "naver_news_api"],
            format_func=lambda x: "네이버 뉴스 검색" if x == "naver_news_search" else "네이버 뉴스 API"
        )
        
        # 고급 설정
        with st.expander("고급 설정"):
            col1, col2 = st.columns(2)
            with col1:
                min_delay = st.number_input("최소 딜레이(초)", min_value=1, max_value=10, value=1)
            with col2:
                max_delay = st.number_input("최대 딜레이(초)", min_value=1, max_value=10, value=3)
            
            batch_size = st.slider("배치 크기", min_value=10, max_value=100, value=30, step=10,
                                  help="한 번에 처리할 기사 수")
            
            auto_collect_comments = st.checkbox("자동으로 댓글 수집", value=True,
                                              help="메타데이터 수집 후 자동으로 댓글 수집을 시작합니다.")
        
        # 제출 버튼
        submitted = st.form_submit_button("수집 시작")
        
        if submitted:
            if keyword and start_date and end_date:
                if min_delay <= max_delay:
                    # 수집 요청 전송
                    success, request_time = send_collection_request(
                        keyword, start_date, end_date, method, min_delay, max_delay,
                        "metadata", batch_size, auto_collect_comments
                    )
                    if success:
                        st.success("메타데이터 수집 요청이 성공적으로 전송되었습니다.")
                        logger.info(f"메타데이터 수집 요청 성공 - 키워드: {keyword}, 시작일: {start_date}, 종료일: {end_date}")
                        # 세션 상태에 요청 시간 저장
                        if 'last_request_time' not in st.session_state:
                            st.session_state['last_request_time'] = {}
                        st.session_state['last_request_time'] = request_time
                    else:
                        st.error("메타데이터 수집 요청 전송 중 오류가 발생했습니다.")
                else:
                    st.warning("최소 딜레이는 최대 딜레이보다 작거나 같아야 합니다.")
            else:
                st.warning("모든 필드를 입력해주세요.")

def render_comment_collection_form():
    """댓글 수집 폼 렌더링"""
    st.header("댓글 수집")
    
    with st.form("comment_collection_form"):
        # 키워드 입력
        keyword = st.text_input("검색 키워드", help="수집할 댓글의 기사 검색 키워드를 입력하세요.")
        
        # 날짜 범위 선택
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("시작일", datetime.now() - timedelta(days=7), key="comment_start_date")
        with col2:
            end_date = st.date_input("종료일", datetime.now(), key="comment_end_date")
        
        # 수집 방법 선택
        method = st.selectbox(
            "수집 방법",
            ["naver_news_comments"],
            format_func=lambda x: "네이버 뉴스 댓글"
        )
        
        # 고급 설정
        with st.expander("고급 설정"):
            col1, col2 = st.columns(2)
            with col1:
                min_delay = st.number_input("최소 딜레이(초)", min_value=1, max_value=10, value=2, key="comment_min_delay")
            with col2:
                max_delay = st.number_input("최대 딜레이(초)", min_value=1, max_value=10, value=5, key="comment_max_delay")
        
        # 제출 버튼
        submitted = st.form_submit_button("수집 시작")
        
        if submitted:
            if keyword and start_date and end_date:
                if min_delay <= max_delay:
                    # 수집 요청 전송
                    success, request_time = send_collection_request(
                        keyword, start_date, end_date, method, min_delay, max_delay,
                        "comments"
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
                    st.warning("최소 딜레이는 최대 딜레이보다 작거나 같아야 합니다.")
            else:
                st.warning("모든 필드를 입력해주세요.")

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

def get_recent_collections(db, limit=5):
    """최근 수집 내역 가져오기"""
    try:
        query = """
            SELECT main_keyword, method, COUNT(*) as article_count, 
                   MIN(published_date) as start_date, MAX(published_date) as end_date,
                   MAX(collected_at) as collected_at
            FROM articles
            GROUP BY main_keyword, method
            ORDER BY MAX(collected_at) DESC
            LIMIT :limit
        """
        result = db.session.execute(query, {"limit": limit}).fetchall()
        
        # 결과를 데이터프레임으로 변환
        df = pd.DataFrame(result, columns=[
            '키워드', '수집방법', '기사수', '시작일', '종료일', '수집일시'
        ])
        
        return df
    except Exception as e:
        logger.error(f"최근 수집 내역 조회 오류: {str(e)}", exc_info=True)
        return pd.DataFrame()

def render_recent_collections(db):
    """최근 수집 내역 표시"""
    st.header("최근 수집 내역")
    
    if db is None:
        st.warning("데이터베이스에 연결할 수 없습니다. 수집 내역을 표시할 수 없습니다.")
        return
    
    recent_collections = get_recent_collections(db)
    
    if recent_collections.empty:
        st.info("아직 수집 내역이 없습니다.")
        return
    
    # 수집 방법 이름 변환
    recent_collections['수집방법'] = recent_collections['수집방법'].apply(
        lambda x: "네이버 뉴스 검색" if x == "naver_news_search" else 
                 "네이버 뉴스 API" if x == "naver_news_api" else x
    )
    
    st.dataframe(
        recent_collections,
        use_container_width=True,
        column_config={
            "기사수": st.column_config.NumberColumn(
                "기사수",
                help="수집된 기사 수",
                format="%d개"
            ),
            "시작일": st.column_config.DatetimeColumn(
                "시작일",
                format="YYYY-MM-DD"
            ),
            "종료일": st.column_config.DatetimeColumn(
                "종료일",
                format="YYYY-MM-DD"
            ),
            "수집일시": st.column_config.DatetimeColumn(
                "수집일시",
                format="YYYY-MM-DD HH:mm:ss"
            )
        }
    )

def main():
    """데이터 수집 인터페이스 페이지 실행 함수"""
    setup_page()
    st.title("데이터 수집 인터페이스")
    
    # 데이터베이스 연결
    db = get_db_connection()
    
    # 수집 상태 표시
    render_collection_status(db)
    
    st.markdown("---")
    
    # 최근 수집 내역 표시
    render_recent_collections(db)
    
    st.markdown("---")
    
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
