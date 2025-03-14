import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import sys
import os
import logging
import numpy as np
import sqlalchemy as sa
from typing import List, Dict, Any, Optional

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.database import Database

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_page():
    """페이지 설정"""
    st.set_page_config(
        page_title="댓글 분석",
        page_icon="💬",
        layout="wide"
    )
    
    # 사이드바 설정
    st.sidebar.title("댓글 분석")
    st.sidebar.info(
        "이 페이지에서는 수집된 댓글의 분석 결과를 확인할 수 있습니다."
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

def get_top_articles_by_comments(db, limit=10):
    """댓글이 많은 상위 기사 목록"""
    try:
        query = """
            SELECT a.id, a.title, a.publisher, a.naver_link, a.published_date, 
                   a.main_keyword, COUNT(c.id) as comment_count
            FROM articles a
            JOIN comments c ON a.id = c.article_id
            GROUP BY a.id, a.title, a.publisher, a.naver_link, a.published_date, a.main_keyword
            ORDER BY comment_count DESC
            LIMIT :limit
        """
        result = db.session.execute(sa.text(query), {"limit": limit}).fetchall()
        
        # 결과를 데이터프레임으로 변환
        df = pd.DataFrame(result, columns=[
            '기사ID', '제목', '언론사', '네이버링크', '발행일', '키워드', '댓글수'
        ])
        
        # 제목 길이 제한 (표시용)
        df['짧은제목'] = df['제목'].apply(lambda x: x[:30] + '...' if len(x) > 30 else x)
        
        return df
    except Exception as e:
        logger.error(f"댓글 많은 기사 조회 오류: {str(e)}", exc_info=True)
        return pd.DataFrame()

def get_comment_stats_by_date(db, days=30):
    """일별 댓글 통계"""
    try:
        # 최근 N일 기준 날짜 계산
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT DATE(c.collected_at) as date, COUNT(*) as count
            FROM comments c
            WHERE c.collected_at > :cutoff_date
            GROUP BY DATE(c.collected_at)
            ORDER BY date
        """
        result = db.session.execute(sa.text(query), {"cutoff_date": cutoff_date}).fetchall()
        
        # 결과를 데이터프레임으로 변환
        df = pd.DataFrame(result, columns=['날짜', '댓글수'])
        
        return df
    except Exception as e:
        logger.error(f"일별 댓글 통계 조회 오류: {str(e)}", exc_info=True)
        return pd.DataFrame()

def get_comment_sentiment_data(db):
    """감정 분석 데이터 (실제 데이터가 있으면 사용, 없으면 가상 데이터)"""
    try:
        # 감정 분석 데이터가 있는지 확인
        query = """
            SELECT COUNT(*)
            FROM comment_stats
            WHERE sentiment_distribution IS NOT NULL
        """
        has_sentiment = db.session.execute(sa.text(query)).scalar() > 0
        
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
            result = db.session.execute(sa.text(query)).fetchone()
            
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

def get_keyword_frequency(db, limit=10):
    """키워드 빈도 분석"""
    try:
        # 실제 키워드 분석 데이터가 있는지 확인
        # 여기서는 가상 데이터 사용
        keywords = pd.DataFrame({
            '키워드': ['택시', '요금', '기사', '서비스', '앱', '안전', '불만', '대기', '불편', '개선'],
            '빈도': [120, 95, 80, 75, 70, 65, 60, 55, 50, 45]
        })
        return keywords
    except Exception as e:
        logger.error(f"키워드 빈도 분석 오류: {str(e)}", exc_info=True)
        return pd.DataFrame()

def get_sentiment_trend(db, days=30):
    """일별 감정 분석 추이 (가상 데이터)"""
    try:
        # 날짜 범위 생성
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()
        dates = pd.date_range(start_date, end_date, freq='D')
        
        # 기본 트렌드와 노이즈 생성
        np.random.seed(42)  # 재현성을 위한 시드 설정
        base_trend = np.sin(np.linspace(0, 4*np.pi, len(dates))) * 10 + 20  # 기본 사인파 트렌드
        noise = np.random.normal(0, 2, len(dates))  # 노이즈
        
        trend_data = []
        for i, date in enumerate(dates):
            # 긍정 댓글 (기본 트렌드 + 노이즈)
            positive = int(abs(base_trend[i] + noise[i]))
            # 부정 댓글 (긍정 댓글의 변형 + 노이즈)
            negative = int(abs(base_trend[i] * 1.2 + noise[i]))
            # 중립 댓글 (긍정과 부정의 중간 + 노이즈)
            neutral = int(abs((positive + negative) * 0.3 + noise[i]))
            
            trend_data.append({
                '날짜': date,
                '감정': '긍정',
                '댓글수': positive
            })
            trend_data.append({
                '날짜': date,
                '감정': '부정',
                '댓글수': negative
            })
            trend_data.append({
                '날짜': date,
                '감정': '중립',
                '댓글수': neutral
            })
        
        return pd.DataFrame(trend_data)
    except Exception as e:
        logger.error(f"감정 분석 추이 생성 오류: {str(e)}", exc_info=True)
        return pd.DataFrame()

def render_comments_analysis():
    """댓글 분석 결과 렌더링"""
    st.title("댓글 분석")
    
    # 데이터베이스 연결
    db = get_db_connection()
    if db is None:
        st.error("데이터베이스에 연결할 수 없습니다. 설정을 확인해주세요.")
        return
    
    try:
        # 댓글이 많은 상위 기사
        st.header("댓글이 많은 상위 기사")
        
        # 표시할 기사 수 선택
        top_n = st.slider("표시할 기사 수", min_value=5, max_value=20, value=10, step=5)
        
        # 데이터 가져오기
        df = get_top_articles_by_comments(db, limit=top_n)
        
        if df.empty:
            st.info("댓글이 있는 기사가 없습니다.")
            return
        
        # 차트 생성
        chart = alt.Chart(df).mark_bar().encode(
            y=alt.Y('짧은제목:N', sort='-x', title='기사 제목'),
            x=alt.X('댓글수:Q', title='댓글 수'),
            tooltip=['제목', '언론사', '발행일', '댓글수']
        ).properties(
            height=30 * len(df)
        )
        
        st.altair_chart(chart, use_container_width=True)
        
        # 데이터프레임으로 상세 정보 표시
        st.subheader("댓글 상위 기사 상세 정보")
        
        # 네이버 링크를 클릭 가능한 링크로 변환
        df['네이버링크'] = df['네이버링크'].apply(lambda x: f'{x}' if pd.notnull(x) else '')
        
        # 데이터프레임 표시
        st.markdown("""
        <style>
        .dataframe {
            font-size: 12px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # '짧은제목' 컬럼 제거하고 표시
        df_display = df.drop(columns=['짧은제목'])
        
        st.dataframe(
            df_display,
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
        
        # 댓글 긍정/부정 비율
        st.subheader("댓글 긍정/부정 비율")
        
        # 감정 분석 데이터 가져오기
        sentiment_data, is_real_data = get_comment_sentiment_data(db)
        
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
            width=400,
            height=400
        )
        
        st.altair_chart(pie_chart)
        
        # 일별 긍정/부정 트렌드
        st.subheader("일별 긍정/부정 트렌드")
        
        # 표시할 기간 선택
        trend_days = st.slider("표시할 기간 (일)", min_value=7, max_value=90, value=30, step=1, key="trend_days")
        
        # 감정 분석 추이 데이터 가져오기
        trend_df = get_sentiment_trend(db, days=trend_days)
        
        st.caption("※ 실제 감정 분석 추이 데이터가 없어 가상 데이터를 표시합니다.")
        
        # 스택 영역 차트 생성
        trend_chart = alt.Chart(trend_df).mark_area().encode(
            x=alt.X('날짜:T', title='날짜'),
            y=alt.Y('댓글수:Q', stack='zero', title='댓글 수'),
            color=alt.Color('감정:N', scale=alt.Scale(
                domain=['긍정', '중립', '부정'],
                range=['#2ecc71', '#95a5a6', '#e74c3c']
            )),
            tooltip=['날짜', '감정', '댓글수']
        ).properties(
            width=800,
            height=400
        )
        
        st.altair_chart(trend_chart, use_container_width=True)
        
        # 댓글 키워드 순위
        st.subheader("댓글 키워드 순위")
        
        # 키워드 빈도 데이터 가져오기
        comment_keywords = get_keyword_frequency(db)
        
        st.caption("※ 실제 키워드 분석 데이터가 없어 가상 데이터를 표시합니다.")
        
        comment_chart = alt.Chart(comment_keywords).mark_bar().encode(
            y=alt.Y('키워드:N', sort='-x'),
            x='빈도:Q',
            tooltip=['키워드', '빈도']
        ).properties(
            width=600,
            height=300
        )
        
        st.altair_chart(comment_chart, use_container_width=True)
        
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {str(e)}")
        st.error("데이터베이스 연결을 확인해주세요.")
        logger.error(f"댓글 분석 오류: {str(e)}", exc_info=True)

def main():
    setup_page()
    render_comments_analysis()

if __name__ == "__main__":
    main()
