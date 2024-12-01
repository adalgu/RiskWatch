"""
Main application module for the dashboard.
Integrates all components and provides the main entry point.
"""

import os
import streamlit as st
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import time

import pika
import json

from logging_config import get_logger
from decorators import handle_exceptions

logger = get_logger('app')

# Configuration from environment variables
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/news_db')
RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
LOG_FILE_PATH = os.getenv('COLLECTOR_LOG_PATH', '/app/logs/collector.log')

# Database setup
engine = sa.create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Database:
    def __init__(self):
        self.session = SessionLocal()

    def __del__(self):
        self.session.close()

    def get_date_range(self):
        """Get the date range of collected articles"""
        query = """
            SELECT MIN(published_date), MAX(published_date)
            FROM articles
        """
        result = self.session.execute(text(query)).fetchone()
        return result[0], result[1]

    def get_keywords_summary(self):
        """Get summary of collected articles by keyword"""
        query = """
            SELECT main_keyword, COUNT(*) as article_count,
                   MIN(published_date) as earliest_date,
                   MAX(published_date) as latest_date
            FROM articles
            GROUP BY main_keyword
            ORDER BY article_count DESC
        """
        return self.session.execute(text(query)).fetchall()

    def get_articles_by_date(self, start_date, end_date, keyword=None):
        """Get articles within date range and optionally filtered by keyword"""
        query = """
            SELECT DATE(published_date) as date, COUNT(*) as count
            FROM articles
            WHERE published_date BETWEEN :start_date AND :end_date
        """
        if keyword:
            query += " AND main_keyword = :keyword"
        query += " GROUP BY DATE(published_date) ORDER BY date"
        
        params = {"start_date": start_date, "end_date": end_date}
        if keyword:
            params["keyword"] = keyword
            
        return self.session.execute(text(query), params).fetchall()

    def get_articles_details_by_date(self, date, keyword=None):
        """Get detailed article information for a specific date"""
        query = """
            SELECT title, publisher, naver_link, published_at
            FROM articles
            WHERE DATE(published_date) = :date
        """
        if keyword:
            query += " AND main_keyword = :keyword"
        query += " ORDER BY published_at DESC"
        
        params = {"date": date}
        if keyword:
            params["keyword"] = keyword
            
        return self.session.execute(text(query), params).fetchall()

    def get_all_keywords(self):
        """Get list of all keywords"""
        query = """
            SELECT DISTINCT main_keyword
            FROM articles
            ORDER BY main_keyword
        """
        result = self.session.execute(text(query))
        return [row[0] for row in result]

def get_recent_logs(start_time=None):
    """Get recent collection logs"""
    try:
        if os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
                logs = f.readlines()
                
            # Filter logs by start time if provided
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
            
            # Return last 100 lines if no start time
            return logs[-100:]
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return []

def publish_collection_request(keyword, start_date, end_date, method, min_delay, max_delay, batch_size):
    """Publish collection request to RabbitMQ"""
    try:
        # RabbitMQ connection
        parameters = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Declare queue
        channel.queue_declare(queue='collection_requests', durable=True)

        # Prepare message
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

        # Publish message
        channel.basic_publish(
            exchange='',
            routing_key='collection_requests',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )

        connection.close()
        return True, datetime.now()
    except Exception as e:
        logger.error(f"Failed to publish collection request: {str(e)}")
        return False, None

@handle_exceptions("대시보드 초기화 중 오류가 발생했습니다")
def setup_page():
    """Initialize Streamlit page configuration"""
    st.set_page_config(
        page_title="뉴스 기사 수집 현황",
        page_icon="📰",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    st.title("뉴스 기사 수집 현황 대시보드")

def render_collection_form():
    """Render the collection request form"""
    st.header("데이터 수집 요청")
    
    with st.form("collection_form"):
        keyword = st.text_input("검색 키워드", placeholder="예: 삼성전자")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("시작일")
        with col2:
            end_date = st.date_input("종료일")
            
        # Add new parameters
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
                    # Store request time in session state
                    st.session_state['last_request_time'] = request_time
                    # Set auto-refresh
                    st.session_state['auto_refresh'] = True
                else:
                    st.error("수집 요청 전송 중 오류가 발생했습니다.")
            else:
                if min_delay > max_delay:
                    st.warning("최소 딜레이는 최대 딜레이보다 작거나 같아야 합니다.")
                else:
                    st.warning("모든 필드를 입력해주세요.")

def render_collection_status():
    """Render collection status information"""
    st.header("수집 현황")
    
    db = Database()
    
    # Get all keywords and add an "전체" option
    keywords = ["전체"] + db.get_all_keywords()
    selected_keyword = st.selectbox("검색 키워드 선택", keywords)
    
    # Get date range from database
    date_range = db.get_date_range()
    if date_range[0] and date_range[1]:
        # Get articles by date
        articles_by_date = db.get_articles_by_date(
            start_date=date_range[0],
            end_date=date_range[1],
            keyword=None if selected_keyword == "전체" else selected_keyword
        )
        
        if articles_by_date:
            # Create a table with the data
            st.write("날짜별 수집 현황")
            
            # Convert to a format suitable for display
            data = {
                "날짜": [row.date.strftime("%Y-%m-%d") for row in articles_by_date],
                "기사 개수": [row.count for row in articles_by_date]
            }
            
            # Display as a table
            st.dataframe(
                data,
                column_config={
                    "날짜": st.column_config.TextColumn("날짜", width=200),
                    "기사 개수": st.column_config.NumberColumn("기사 개수", width=200)
                },
                hide_index=True
            )
            
            # Show total
            total_articles = sum(row.count for row in articles_by_date)
            st.write(f"총 기사 수: {total_articles:,}건")
        else:
            st.info("선택한 키워드에 대한 수집 데이터가 없습니다.")
    else:
        st.info("수집된 데이터가 없습니다.")

def render_collection_logs():
    """Render real-time collection logs"""
    st.header("수집 로그")
    
    # Add auto-refresh toggle
    auto_refresh = st.checkbox("자동 새로고침", 
                             value=st.session_state.get('auto_refresh', False),
                             help="5초마다 로그를 자동으로 새로고침합니다")
    st.session_state['auto_refresh'] = auto_refresh
    
    # Get logs since last request
    if 'last_request_time' in st.session_state:
        logs = get_recent_logs(st.session_state['last_request_time'])
        if logs:
            log_text = ''.join(logs)
            st.text_area("실시간 수집 로그", log_text, height=400)
        else:
            st.info("아직 수집 로그가 없습니다.")
    else:
        st.info("수집 요청을 시작하면 로그가 표시됩니다.")
    
    # Auto-refresh if enabled
    if auto_refresh:
        time.sleep(5)
        st.rerun()

@handle_exceptions("대시보드 실행 중 오류가 발생했습니다")
def main():
    """Main application entry point"""
    try:
        # Initialize page
        setup_page()
        
        # Render main sections
        render_collection_form()
        st.markdown("---")
        render_collection_status()
        st.markdown("---")
        render_collection_logs()

    except Exception as e:
        logger.error(f"Critical dashboard error: {str(e)}")
        st.error("대시보드 로딩 중 치명적인 오류가 발생했습니다. 관리자에게 문의해주세요.")

if __name__ == "__main__":
    main()
