"""
Main application module for the dashboard.
Integrates all components and provides the main entry point.
"""

import streamlit as st
from datetime import datetime
from contextlib import contextmanager

from database import Database, SessionLocal
from .logging_config import get_logger
from .decorators import handle_exceptions
from .collection_service import (
    collect_articles_parallel,
    collect_comments_parallel,
    get_collection_status
)
from .ui import (
    initialize_session_state,
    render_main_ui
)

logger = get_logger('app')


@contextmanager
def get_db():
    """Database session context manager"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@handle_exceptions("대시보드 초기화 중 오류가 발생했습니다")
def setup_page():
    """Initialize Streamlit page configuration"""
    st.set_page_config(
        page_title="뉴스 기사 수집 현황",
        page_icon="📰",
        layout="wide",
        initial_sidebar_state="collapsed"  # 탭 레이아웃에서는 사이드바를 숨김
    )
    st.title("뉴스 기사 수집 현황 대시보드")


def collect_comments_wrapper(start_date: datetime, end_date: datetime, keyword: str = None) -> int:
    """Wrapper function for comment collection to match expected interface"""
    db = Database()
    articles = db.get_articles_for_comment_collection(
        start_date, end_date, keyword)
    if articles:
        return collect_comments_parallel(articles)
    return 0


def get_date_range_wrapper():
    """Wrapper function for get_date_range to handle database session"""
    db = Database()
    return db.get_date_range()


def get_keywords_summary_wrapper():
    """Wrapper function for get_keywords_summary to handle database session"""
    db = Database()
    return db.get_keywords_summary()


def get_articles_by_date_wrapper(start_date: datetime, end_date: datetime, keyword: str = None):
    """Wrapper function for get_articles_by_date to handle database session"""
    db = Database()
    return db.get_articles_by_date(start_date, end_date, keyword)


def get_articles_details_by_date_wrapper(date: datetime, keyword: str = None):
    """Wrapper function for get_articles_details_by_date to handle database session"""
    db = Database()
    return db.get_articles_details_by_date(date, keyword)


@handle_exceptions("대시보드 실행 중 오류가 발생했습니다")
def main():
    """Main application entry point"""
    try:
        # Initialize page
        setup_page()

        # Initialize session state
        initialize_session_state()

        # Get initial keywords data
        db = Database()
        keywords_data = db.get_keywords_summary()

        # Render main UI with tabs
        render_main_ui(
            keywords_data=keywords_data,
            collect_articles_func=collect_articles_parallel,
            collect_comments_func=collect_comments_wrapper,
            get_date_range_func=get_date_range_wrapper,
            get_keywords_summary_func=get_keywords_summary_wrapper,
            get_articles_by_date_func=get_articles_by_date_wrapper,
            get_articles_details_by_date_func=get_articles_details_by_date_wrapper
        )

    except Exception as e:
        logger.error(f"Critical dashboard error: {str(e)}")
        st.error("대시보드 로딩 중 치명적인 오류가 발생했습니다. 관리자에게 문의해주세요.")


if __name__ == "__main__":
    main()
