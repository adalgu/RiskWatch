import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import sys
import os
import logging
from typing import List, Dict, Any, Optional

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.database import Database
from modules.models import Article, Comment, CommentStats

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_page():
    """페이지 설정"""
    st.set_page_config(
        page_title="DB 결과 확인",
        page_icon="📊",
        layout="wide"
    )
    
    # 사이드바 설정
    st.sidebar.title("DB 결과 확인")
    st.sidebar.info(
        "이 페이지에서는 데이터베이스에 저장된 기사와 댓글 데이터를 확인할 수 있습니다."
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

def get_article_summary(db: Database):
    """기사 데이터 요약 정보"""
    try:
        # 전체 기사 수
        query = "SELECT COUNT(*) FROM articles"
        total_articles = db.session.execute(query).scalar()
        
        # 네이버 기사 수
        query = "SELECT COUNT(*) FROM articles WHERE is_naver_news = TRUE"
        naver_articles = db.session.execute(query).scalar()
        
        # 키워드별 기사 수
        query = """
            SELECT main_keyword, COUNT(*) as count
            FROM articles
            GROUP BY main_keyword
            ORDER BY count DESC
            LIMIT 10
        """
        keyword_counts = db.session.execute(query).fetchall()
        
        # 최근 수집 날짜
        query = """
            SELECT MAX(collected_at)
            FROM articles
        """
        last_collected = db.session.execute(query).scalar()
        
        return {
            "total_articles": total_articles,
            "naver_articles": naver_articles,
            "keyword_counts": keyword_counts,
            "last_collected": last_collected
        }
    except Exception as e:
        logger.error(f"기사 요약 정보 조회 오류: {str(e)}", exc_info=True)
        return None

def get_comment_summary(db: Database):
    """댓글 데이터 요약 정보"""
    try:
        # 전체 댓글 수
        query = "SELECT COUNT(*) FROM comments"
        total_comments = db.session.execute(query).scalar()
        
        # 댓글이 있는 기사 수
        query = """
            SELECT COUNT(DISTINCT article_id)
            FROM comments
        """
        articles_with_comments = db.session.execute(query).scalar()
        
        # 기사당 평균 댓글 수
        query = """
            SELECT AVG(comment_count)
            FROM (
                SELECT article_id, COUNT(*) as comment_count
                FROM comments
                GROUP BY article_id
            ) as subquery
        """
        avg_comments_per_article = db.session.execute(query).scalar()
        
        # 최근 수집 날짜
        query = """
            SELECT MAX(collected_at)
            FROM comments
        """
        last_collected = db.session.execute(query).scalar()
        
        return {
            "total_comments": total_comments,
            "articles_with_comments": articles_with_comments,
            "avg_comments_per_article": avg_comments_per_article,
            "last_collected": last_collected
        }
    except Exception as e:
        logger.error(f"댓글 요약 정보 조회 오류: {str(e)}", exc_info=True)
        return None

def get_top_articles_by_comments(db: Database, limit: int = 10):
    """댓글이 많은 상위 기사 목록"""
    try:
        query = """
            SELECT a.id, a.title, a.publisher, a.naver_link, a.published_date, 
                   COUNT(c.id) as comment_count
            FROM articles a
            JOIN comments c ON a.id = c.article_id
            GROUP BY a.id, a.title, a.publisher, a.naver_link, a.published_date
            ORDER BY comment_count DESC
            LIMIT :limit
        """
        result = db.session.execute(query, {"limit": limit}).fetchall()
        
        # 결과를 데이터프레임으로 변환
        df = pd.DataFrame(result, columns=[
            '기사ID', '제목', '언론사', '네이버링크', '발행일', '댓글수'
        ])
        
        return df
    except Exception as e:
        logger.error(f"댓글 많은 기사 조회 오류: {str(e)}", exc_info=True)
        return pd.DataFrame()

def get_recent_articles(db: Database, days: int = 7, limit: int = 20):
    """최근 수집된 기사 목록"""
    try:
        # 최근 N일 기준 날짜 계산
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT a.id, a.title, a.publisher, a.naver_link, a.published_date, 
                   a.main_keyword, a.collected_at
            FROM articles a
            WHERE a.collected_at > :cutoff_date
            ORDER BY a.collected_at DESC
            LIMIT :limit
        """
        result = db.session.execute(query, {
            "cutoff_date": cutoff_date,
            "limit": limit
        }).fetchall()
        
        # 결과를 데이터프레임으로 변환
        df = pd.DataFrame(result, columns=[
            '기사ID', '제목', '언론사', '네이버링크', '발행일', '키워드', '수집일시'
        ])
        
        return df
    except Exception as e:
        logger.error(f"최근 기사 조회 오류: {str(e)}", exc_info=True)
        return pd.DataFrame()

def get_sentiment_data(db: Database):
    """감정 분석 데이터 (실제 데이터가 있으면 사용, 없으면 가상 데이터)"""
    try:
        # 감정 분석 데이터가 있는지 확인
        query = """
            SELECT COUNT(*)
            FROM comment_stats
            WHERE sentiment_distribution IS NOT NULL
        """
        has_sentiment = db.session.execute(query).scalar() > 0
        
        if has_sentiment:
            # 실제 감정 분석 데이터 사용
            query = """
                SELECT 
                    SUM((sentiment_distribution->>'positive')::float) as positive,
                    SUM((sentiment_distribution->>'neutral')::float) as neutral,
                    SUM((sentiment_distribution->>'negative')::float) as negative
                FROM comment_stats
                WHERE sentiment_distribution IS NOT NULL
            """
            result = db.session.execute(query).fetchone()
            
            if result and result[0] is not None:
                total = sum(filter(None, result))
                if total > 0:
                    sentiment_data = pd.DataFrame({
                        '감정': ['긍정', '중립', '부정'],
                        '비율': [
                            round(result[0] / total * 100 if result[0] else 0, 1),
                            round(result[1] / total * 100 if result[1] else 0, 1),
                            round(result[2] / total * 100 if result[2] else 0, 1)
                        ]
                    })
                    return sentiment_data, True
        
        # 가상 데이터 생성
        sentiment_data = pd.DataFrame({
            '감정': ['긍정', '중립', '부정'],
            '비율': [35, 20, 45]
        })
        return sentiment_data, False
    except Exception as e:
        logger.error(f"감정 분석 데이터 조회 오류: {str(e)}", exc_info=True)
        # 오류 시 가상 데이터 반환
        sentiment_data = pd.DataFrame({
            '감정': ['긍정', '중립', '부정'],
            '비율': [35, 20, 45]
        })
        return sentiment_data, False

def get_daily_article_trend(db: Database, days: int = 30):
    """일별 기사 수집 추이"""
    try:
        # 최근 N일 기준 날짜 계산
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT DATE(collected_at) as date, COUNT(*) as count
            FROM articles
            WHERE collected_at > :cutoff_date
            GROUP BY DATE(collected_at)
            ORDER BY date
        """
        result = db.session.execute(query, {"cutoff_date": cutoff_date}).fetchall()
        
        # 결과를 데이터프레임으로 변환
        df = pd.DataFrame(result, columns=['날짜', '기사수'])
        
        return df
    except Exception as e:
        logger.error(f"일별 기사 추이 조회 오류: {str(e)}", exc_info=True)
        return pd.DataFrame()

def get_daily_comment_trend(db: Database, days: int = 30):
    """일별 댓글 수집 추이"""
    try:
        # 최근 N일 기준 날짜 계산
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT DATE(collected_at) as date, COUNT(*) as count
            FROM comments
            WHERE collected_at > :cutoff_date
            GROUP BY DATE(collected_at)
            ORDER BY date
        """
        result = db.session.execute(query, {"cutoff_date": cutoff_date}).fetchall()
        
        # 결과를 데이터프레임으로 변환
        df = pd.DataFrame(result, columns=['날짜', '댓글수'])
        
        return df
    except Exception as e:
        logger.error(f"일별 댓글 추이 조회 오류: {str(e)}", exc_info=True)
        return pd.DataFrame()

def render_dashboard(db: Database):
    """대시보드 렌더링"""
    st.title("데이터베이스 결과 확인")
    
    # 데이터베이스 연결 상태 확인
    if db is None:
        st.error("데이터베이스에 연결할 수 없습니다. 설정을 확인해주세요.")
        return
    
    # 요약 정보 가져오기
    article_summary = get_article_summary(db)
    comment_summary = get_comment_summary(db)
    
    if not article_summary or not comment_summary:
        st.error("데이터베이스에서 요약 정보를 가져오는 중 오류가 발생했습니다.")
        return
    
    # 요약 정보 표시
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("기사 데이터 요약")
        st.metric("전체 기사 수", f"{article_summary['total_articles']:,}개")
        st.metric("네이버 기사 수", f"{article_summary['naver_articles']:,}개")
        st.write(f"최근 수집: {article_summary['last_collected']}")
        
        # 키워드별 기사 수
        st.subheader("키워드별 기사 수")
        keyword_df = pd.DataFrame(article_summary['keyword_counts'], columns=['키워드', '기사수'])
        
        # 차트 생성
        keyword_chart = alt.Chart(keyword_df).mark_bar().encode(
            y=alt.Y('키워드:N', sort='-x', title='키워드'),
            x=alt.X('기사수:Q', title='기사 수'),
            tooltip=['키워드', '기사수']
        ).properties(
            height=300
        )
        
        st.altair_chart(keyword_chart, use_container_width=True)
    
    with col2:
        st.subheader("댓글 데이터 요약")
        st.metric("전체 댓글 수", f"{comment_summary['total_comments']:,}개")
        st.metric("댓글 있는 기사 수", f"{comment_summary['articles_with_comments']:,}개")
        if comment_summary['avg_comments_per_article']:
            st.metric("기사당 평균 댓글 수", f"{comment_summary['avg_comments_per_article']:.1f}개")
        st.write(f"최근 수집: {comment_summary['last_collected']}")
        
        # 감정 분석 파이 차트
        st.subheader("댓글 감정 분석")
        sentiment_data, is_real_data = get_sentiment_data(db)
        
        if not is_real_data:
            st.caption("※ 실제 감정 분석 데이터가 없어 가상 데이터를 표시합니다.")
        
        pie_chart = alt.Chart(sentiment_data).mark_arc().encode(
            theta='비율:Q',
            color=alt.Color('감정:N', scale=alt.Scale(
                domain=['긍정', '중립', '부정'],
                range=['#2ecc71', '#95a5a6', '#e74c3c']
            )),
            tooltip=['감정', '비율']
        ).properties(
            height=300
        )
        
        st.altair_chart(pie_chart, use_container_width=True)
    
    # 일별 추이 차트
    st.subheader("일별 데이터 수집 추이")
    
    # 기간 선택
    days = st.slider("표시할 기간 (일)", min_value=7, max_value=90, value=30, step=1)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("일별 기사 수집 추이")
        article_trend = get_daily_article_trend(db, days)
        
        if not article_trend.empty:
            article_chart = alt.Chart(article_trend).mark_line(point=True).encode(
                x=alt.X('날짜:T', title='날짜'),
                y=alt.Y('기사수:Q', title='기사 수'),
                tooltip=['날짜', '기사수']
            ).properties(
                height=300
            )
            
            st.altair_chart(article_chart, use_container_width=True)
        else:
            st.info("표시할 기사 추이 데이터가 없습니다.")
    
    with col2:
        st.subheader("일별 댓글 수집 추이")
        comment_trend = get_daily_comment_trend(db, days)
        
        if not comment_trend.empty:
            comment_chart = alt.Chart(comment_trend).mark_line(point=True).encode(
                x=alt.X('날짜:T', title='날짜'),
                y=alt.Y('댓글수:Q', title='댓글 수'),
                tooltip=['날짜', '댓글수']
            ).properties(
                height=300
            )
            
            st.altair_chart(comment_chart, use_container_width=True)
        else:
            st.info("표시할 댓글 추이 데이터가 없습니다.")
    
    # 댓글이 많은 상위 기사
    st.subheader("댓글이 많은 상위 기사")
    top_articles = get_top_articles_by_comments(db)
    
    if not top_articles.empty:
        # 네이버 링크를 클릭 가능한 링크로 변환
        top_articles['네이버링크'] = top_articles['네이버링크'].apply(
            lambda x: f'{x}' if pd.notnull(x) else ''
        )
        
        st.dataframe(
            top_articles,
            use_container_width=True,
            column_config={
                "기사ID": None,  # 숨김
                "네이버링크": st.column_config.LinkColumn(),
                "발행일": st.column_config.DatetimeColumn(
                    "발행일",
                    format="YYYY-MM-DD HH:mm"
                ),
                "댓글수": st.column_config.NumberColumn(
                    "댓글수",
                    help="기사에 달린 총 댓글 수",
                    format="%d개"
                )
            }
        )
    else:
        st.info("댓글이 있는 기사가 없습니다.")
    
    # 최근 수집된 기사
    st.subheader("최근 수집된 기사")
    recent_days = st.slider("최근 기간 선택 (일)", min_value=1, max_value=30, value=7, step=1)
    recent_articles = get_recent_articles(db, days=recent_days)
    
    if not recent_articles.empty:
        # 네이버 링크를 클릭 가능한 링크로 변환
        recent_articles['네이버링크'] = recent_articles['네이버링크'].apply(
            lambda x: f'{x}' if pd.notnull(x) else ''
        )
        
        st.dataframe(
            recent_articles,
            use_container_width=True,
            column_config={
                "기사ID": None,  # 숨김
                "네이버링크": st.column_config.LinkColumn(),
                "발행일": st.column_config.DatetimeColumn(
                    "발행일",
                    format="YYYY-MM-DD HH:mm"
                ),
                "수집일시": st.column_config.DatetimeColumn(
                    "수집일시",
                    format="YYYY-MM-DD HH:mm:ss"
                )
            }
        )
    else:
        st.info(f"최근 {recent_days}일 동안 수집된 기사가 없습니다.")

def main():
    setup_page()
    db = get_db_connection()
    render_dashboard(db)

if __name__ == "__main__":
    main()
