"""
Main application module for the dashboard.
Integrates all components and provides the main entry point.
"""

import os
import streamlit as st
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import pika
import json

from logging_config import get_logger
from decorators import handle_exceptions

logger = get_logger('app')

# Configuration from environment variables
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/news_db')
RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')

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
        result = self.session.execute(query).fetchone()
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
        return self.session.execute(query).fetchall()

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
            
        return self.session.execute(query, params).fetchall()

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
            
        return self.session.execute(query, params).fetchall()

def publish_collection_request(keyword, start_date, end_date):
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
        return True
    except Exception as e:
        logger.error(f"Failed to publish collection request: {str(e)}")
        return False

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
            
        submitted = st.form_submit_button("수집 시작")
        
        if submitted:
            if keyword and start_date and end_date:
                if publish_collection_request(keyword, start_date, end_date):
                    st.success("수집 요청이 성공적으로 전송되었습니다.")
                else:
                    st.error("수집 요청 전송 중 오류가 발생했습니다.")
            else:
                st.warning("모든 필드를 입력해주세요.")

def render_collection_status():
    """Render collection status information"""
    st.header("수집 현황")
    
    db = Database()
    keywords_data = db.get_keywords_summary()
    
    if keywords_data:
        st.write("키워드별 수집 현황")
        for row in keywords_data:
            with st.expander(f"{row.main_keyword} ({row.article_count}건)"):
                st.write(f"최초 수집일: {row.earliest_date}")
                st.write(f"최근 수집일: {row.latest_date}")
    else:
        st.info("수집된 데이터가 없습니다.")

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

    except Exception as e:
        logger.error(f"Critical dashboard error: {str(e)}")
        st.error("대시보드 로딩 중 치명적인 오류가 발생했습니다. 관리자에게 문의해주세요.")

if __name__ == "__main__":
    main()
