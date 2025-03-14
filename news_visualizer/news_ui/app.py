import streamlit as st
import os
import logging
from modules.database import Database
from logging_config import setup_logging

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

def main():
    """메인 앱 실행 함수"""
    # 페이지 설정
    st.set_page_config(
        page_title="뉴스 댓글 분석 대시보드",
        page_icon="📰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 사이드바 설정
    st.sidebar.title("뉴스 댓글 분석 대시보드")
    st.sidebar.info(
        """
        이 대시보드는 뉴스 기사와 댓글을 수집하고 분석하는 도구입니다.
        
        - **데이터 수집**: 키워드로 기사 메타데이터와 댓글을 수집합니다.
        - **댓글 분석**: 수집된 댓글의 통계와 분석 결과를 확인합니다.
        - **DB 결과 확인**: 데이터베이스에 저장된 기사와 댓글을 조회합니다.
        """
    )
    
    # 메인 페이지 콘텐츠
    st.title("뉴스 댓글 분석 대시보드")
    st.markdown(
        """
        ## 👋 환영합니다!
        
        이 대시보드에서는 다음과 같은 작업을 수행할 수 있습니다:
        
        ### 1. 데이터 수집
        - **메타데이터 수집**: 키워드로 뉴스 기사 메타데이터를 수집합니다.
        - **댓글 수집**: 네이버 뉴스 기사의 댓글을 수집합니다.
        
        ### 2. 댓글 분석
        - 수집된 댓글의 통계와 트렌드를 분석합니다.
        - 댓글이 많은 기사를 확인합니다.
        - 감정 분석 및 키워드 분석 결과를 확인합니다.
        
        ### 3. DB 결과 확인
        - 데이터베이스에 저장된 기사와 댓글 데이터를 조회합니다.
        - 수집 통계와 추이를 확인합니다.
        
        왼쪽 사이드바의 메뉴를 통해 각 기능에 접근할 수 있습니다.
        """
    )
    
    # 데이터베이스 연결 상태 확인
    try:
        db = Database()
        # 간단한 쿼리로 연결 테스트
        result = db.session.execute("SELECT 1").fetchone()
        if result:
            st.success("✅ 데이터베이스 연결 상태: 정상")
        else:
            st.error("❌ 데이터베이스 연결 상태: 오류")
    except Exception as e:
        st.error(f"❌ 데이터베이스 연결 상태: 오류 ({str(e)})")
        logger.error(f"데이터베이스 연결 오류: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
