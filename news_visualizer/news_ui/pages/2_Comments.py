import streamlit as st
import pandas as pd
import altair as alt
from sqlalchemy import create_engine, text
import numpy as np
from datetime import datetime, timedelta

def setup_page():
    """Streamlit 페이지 설정"""
    st.set_page_config(
        page_title="댓글 분석",
        page_icon="💬",
        layout="wide"
    )
    st.title("댓글 분석")

def get_most_commented_kakao_articles():
    """카카오모빌리티 관련 기사 중 댓글이 많은 순으로 10개 조회"""
    engine = create_engine("postgresql://postgres:password@postgres:5432/news_db")
    
    query = text("""
    WITH comment_counts AS (
        SELECT 
            article_id,
            COUNT(*) as comment_count
        FROM comments
        GROUP BY article_id
    )
    SELECT 
        COALESCE(cc.comment_count, 0) as comment_count,
        a.title,
        a.publisher,
        a.published_at,
        a.naver_link,
        a.id
    FROM articles a
    LEFT JOIN comment_counts cc ON a.id = cc.article_id
    WHERE 
        a.title LIKE '%카카오모빌리티%' OR
        a.main_keyword LIKE '%카카오모빌리티%'
    ORDER BY comment_count DESC
    LIMIT 10;
    """)
    
    return pd.read_sql_query(query, engine)

def render_comments_analysis():
    """댓글 분석 페이지 렌더링"""
    st.subheader("카카오모빌리티 관련 기사 댓글 분석")
    
    try:
        # 데이터 로드
        df = get_most_commented_kakao_articles()
        
        # 날짜 형식 변환
        df['published_at'] = pd.to_datetime(df['published_at']).dt.strftime('%Y-%m-%d %H:%M')
        
        # 컬럼명 한글화
        df.columns = ['댓글수', '제목', '언론사', '발행일시', '네이버링크', '기사 ID']
        
        # 순위 컬럼 추가 (1부터 시작)
        df.insert(0, '순위', range(1, len(df) + 1))
        
        # 제목이 너무 길 경우 자르기
        df['짧은제목'] = df['제목'].apply(lambda x: x[:30] + '...' if len(x) > 30 else x)
        
        # 막대 차트로 시각화 (Altair 사용)
        st.subheader("댓글 상위 10개 기사")
        
        chart = alt.Chart(df).mark_bar().encode(
            y=alt.Y('짧은제목:N', 
                   sort=alt.EncodingSortField(field='댓글수', order='descending'),
                   title='기사 제목'),
            x=alt.X('댓글수:Q', title='댓글 수'),
            tooltip=['순위', '제목', '언론사', '발행일시', '댓글수']
        ).properties(
            width=800,
            height=400
        )
        
        st.altair_chart(chart, use_container_width=True)
        
        # 데이터프레임으로 상세 정보 표시
        st.subheader("댓글 상위 10개 기사 상세 정보")
        
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
                "순위": st.column_config.NumberColumn(
                    "순위",
                    help="댓글 수 기준 순위",
                    format="%d위"
                ),
                "네이버링크": st.column_config.LinkColumn(),
                "댓글수": st.column_config.NumberColumn(
                    "댓글수",
                    help="기사에 달린 총 댓글 수",
                    format="%d개"
                )
            }
        )

        # 댓글 긍정/부정 비율
        st.subheader("댓글 긍정/부정 비율")
        
        # 가상의 데이터
        sentiment_data = pd.DataFrame({
            '감정': ['긍정', '부정', '중립'],
            '비율': [35, 45, 20]
        })
        
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

        # 일자별 긍정/부정 트렌드
        st.subheader("일자별 긍정/부정 트렌드")
        
        # 가상의 데이터 생성
        start_date = datetime(2024, 9, 1)
        end_date = datetime(2024, 12, 13)
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

        trend_df = pd.DataFrame(trend_data)
        
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

        # 기사 키워드 순위
        st.subheader("기사 키워드 순위")
        
        # 가상의 데이터
        article_keywords = pd.DataFrame({
            '키워드': ['플랫폼', '택시', '서비스', '규제', '기사', '요금', '앱', '안전', '경쟁', '혁신'],
            '빈도': [120, 95, 80, 75, 70, 65, 60, 55, 50, 45]
        })
        
        keyword_chart = alt.Chart(article_keywords).mark_bar().encode(
            y=alt.Y('키워드:N', sort='-x'),
            x='빈도:Q',
            tooltip=['키워드', '빈도']
        ).properties(
            width=600,
            height=300
        )
        
        st.altair_chart(keyword_chart, use_container_width=True)

        # 댓글 키워드 순위
        st.subheader("댓글 키워드 순위")
        
        # 가상의 데이터
        comment_keywords = pd.DataFrame({
            '키워드': ['요금', '기사님', '불만', '서비스', '안전', '대기', '불편', '개선', '앱', '친절'],
            '빈도': [150, 130, 110, 100, 90, 85, 80, 75, 70, 65]
        })
        
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

def main():
    setup_page()
    render_comments_analysis()

if __name__ == "__main__":
    main()
