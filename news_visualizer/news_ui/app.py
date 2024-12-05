# app.py

# import sys
# import os

# 디버깅을 위한 sys.path 및 작업 디렉토리 출력
# print("sys.path:", sys.path)
# print("Current working directory:", os.getcwd())

# # # 'modules' 디렉토리를 Python 경로에 추가
# modules_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules'))
# if modules_path not in sys.path:
#     sys.path.append(modules_path)

from modules.database import Database
from logging_config import get_logger
from decorators import handle_exceptions

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

logger = get_logger('app')

def setup_page():
    """Streamlit 페이지 설정"""
    st.set_page_config(
        page_title="뉴스 기사 수집 대시보드",
        page_icon="📰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title("뉴스 기사 수집 대시보드")

def render_dashboard():
    """대시보드 시각화 렌더링"""
    db = Database()
    
    # 모든 키워드를 가져와 "전체" 옵션 추가
    keywords = ["전체"] + db.get_all_keywords()
    selected_keyword = st.selectbox("검색 키워드 선택", keywords)
    
    # 데이터베이스에서 날짜 범위 가져오기
    date_range = db.get_date_range()
    if date_range[0] and date_range[1]:
        # 날짜별 전체 기사 수 가져오기
        articles_by_date = db.get_articles_by_date(
            start_date=date_range[0],
            end_date=date_range[1],
            keyword=None if selected_keyword == "전체" else selected_keyword
        )
        
        # 날짜별 네이버 기사 수 가져오기
        naver_articles_by_date = db.get_naver_articles_by_date(
            start_date=date_range[0],
            end_date=date_range[1],
            keyword=None if selected_keyword == "전체" else selected_keyword
        )
        
        # 날짜별 댓글 수 가져오기
        comments_by_date = db.get_comments_by_date(
            start_date=date_range[0],
            end_date=date_range[1],
            keyword=None if selected_keyword == "전체" else selected_keyword
        )
        
        # Pandas 데이터프레임으로 변환
        articles_df = pd.DataFrame(articles_by_date, columns=["date", "article_count"])
        naver_articles_df = pd.DataFrame(naver_articles_by_date, columns=["date", "naver_article_count"])
        comments_df = pd.DataFrame(comments_by_date, columns=["date", "comment_count"])
        
        # 'date' 컬럼을 datetime 타입으로 변환
        articles_df["date"] = pd.to_datetime(articles_df["date"], errors='coerce')
        naver_articles_df["date"] = pd.to_datetime(naver_articles_df["date"], errors='coerce')
        comments_df["date"] = pd.to_datetime(comments_df["date"], errors='coerce')
        
        # 변환 실패한 행 제거
        articles_df = articles_df.dropna(subset=["date"])
        naver_articles_df = naver_articles_df.dropna(subset=["date"])
        comments_df = comments_df.dropna(subset=["date"])
        
        # 'date'를 기준으로 데이터프레임 병합
        merged_df = pd.merge(articles_df, naver_articles_df, on="date", how="left").fillna(0)
        merged_df = pd.merge(merged_df, comments_df, on="date", how="left").fillna(0)
        
        # 카운트를 정수형으로 변환
        merged_df["article_count"] = merged_df["article_count"].astype(int)
        merged_df["naver_article_count"] = merged_df["naver_article_count"].astype(int)
        merged_df["comment_count"] = merged_df["comment_count"].astype(int)
        
        # 날짜 형식을 문자열로 변환
        merged_df["날짜"] = merged_df["date"].dt.strftime("%Y-%m-%d")
        
        # 원본 'date' 컬럼 삭제
        merged_df = merged_df.drop(columns=["date"])
        
        # 컬럼명 변경
        merged_df.rename(columns={
            "article_count": "기사수(전체)",
            "naver_article_count": "기사수(네이버 뉴스)",
            "comment_count": "댓글수(네이버 뉴스)"
        }, inplace=True)
        
        # 컬럼 순서 재정렬
        merged_df = merged_df[["날짜", "기사수(전체)", "기사수(네이버 뉴스)", "댓글수(네이버 뉴스)"]]

        # KPI 카드
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 기사 수 (전체)", f"{merged_df['기사수(전체)'].sum():,}건")
        with col2:
            st.metric("총 기사 수 (네이버 뉴스)", f"{merged_df['기사수(네이버 뉴스)'].sum():,}건")
        with col3:
            st.metric("총 댓글 수", f"{merged_df['댓글수(네이버 뉴스)'].sum():,}건")

        # 시각화: 라인 차트
        st.subheader("기사 및 댓글 수 추이")
        merged_df_plot = merged_df.set_index("날짜")[["기사수(네이버 뉴스)", "기사수(전체)", "댓글수(네이버 뉴스)"]]
        
        # 이벤트 데이터 준비 (예시)
        events = [
            {"date": "2024-10-02", "description": "공정위 KM '콜 차단' 조치 발표 브리핑"},
            {"date": "2024-10-06", "description": "KM 국토위, 산자위 일반증인 채택 관련 보도"},
            {"date": "2024-10-07", "description": "공정위 DGT 부당수수료 심사보고서 KM 발송"},
            {"date": "2024-10-07", "description": "KM-대한적십자 MOU 체결 보도"},
            {"date": "2024-10-08", "description": "티머니 모빌리티 KM 소수지분 투자 관련 보도"},
            {"date": "2024-10-15", "description": "KM 대리기사 금품 절도 사건 보도"},
            {"date": "2024-10-16", "description": "카카오내비 '요즘뜨는' 서비스 출시"},
            {"date": "2024-10-18", "description": "KM-삼성물산 MOU 체결 보도"},
            {"date": "2024-10-22", "description": "택시연대 남부지검 집회"},
            {"date": "2024-10-22", "description": "카카오, 이프카카오 2024에서 AI서비스 '카나나' 공개"},
            {"date": "2024-10-23", "description": "KM 디벨로퍼스 '기술 블로그' 오픈"},
            {"date": "2024-10-24", "description": "국정감사 KM 증인출석 불발 관련 보도"},
            {"date": "2024-10-24", "description": "국정감사 윤한홍 위원장 KM '분식회계 혐의' 질책 관련 보도"},
            {"date": "2024-10-27", "description": "국정감사 허성무 의원 KM '콜 차단' 질책 관련 보도"},
            {"date": "2024-10-28", "description": "KM-로보티즈 MOU 체결 보도"},
            {"date": "2024-10-28", "description": "아이나비모빌리티, '가맹택시' 사업 진출"},
            {"date": "2024-10-30", "description": "KM-BGF리테일 MOU 체결 보도"},
            {"date": "2024-10-31", "description": "카카오 김범수 위원장, 보석으로 석방"},
            {"date": "2024-11-04", "description": "서울시 행정감사 참석"},
            {"date": "2024-11-05", "description": "검찰, '콜 몰아주기·차단 의혹' 카카오모빌리티 압수수색"},
            {"date": "2024-11-05", "description": "금융위 '중과실' 조치 사전 보도"},
            {"date": "2024-11-06", "description": "금융위 증권선물위원회 '중과실' 조치 의결"},
            {"date": "2024-11-18", "description": "KM-KD 통합상품 (외부명칭 '맞춤기사') 오픈"}
        ]
        events_df = pd.DataFrame(events)
        events_df["date"] = pd.to_datetime(events_df["date"])

        # Altair를 사용한 커스텀 라인 차트
        chart = alt.Chart(merged_df_plot.reset_index()).transform_fold(
            ["기사수(네이버 뉴스)", "기사수(전체)", "댓글수(네이버 뉴스)"],
            as_=["Type", "Count"]
        ).mark_line(point=True).encode(
            x=alt.X('날짜:T', title='날짜'),
            y=alt.Y('Count:Q', title='수량'),
            color=alt.Color('Type:N', scale=alt.Scale(
                domain=["기사수(네이버 뉴스)", "기사수(전체)", "댓글수(네이버 뉴스)"],
                range=["#2ca02c", "#888888", "#1f77b4"]  # 녹색, 회색, 파란색
            ), legend=alt.Legend(title="항목")),
            strokeDash=alt.condition(
                alt.datum.Type == "기사수(전체)",
                alt.value([4,4]),  # 회색 닷팅 선
                alt.value([0])     # 다른 항목은 실선
            )
        )
        
        # 이벤트 라인 추가
        event_lines = alt.Chart(events_df).mark_rule(strokeDash=[6,6], color='red').encode(
            x='date:T',
            tooltip=['description:N']
        )
        
        # 이벤트 텍스트 추가
        event_text = alt.Chart(events_df).mark_text(
            align='left',
            dx=5,
            dy=-5,
            color='red'
        ).encode(
            x='date:T',
            y=alt.value(0)  # y 위치를 적절히 조정
            # text='description:N'
        )
        
        # 최종 차트 결합
        final_chart = (chart + event_lines + event_text).properties(
            width=800,
            height=400
        )
        
        st.altair_chart(final_chart, use_container_width=True)
        


        # 데이터프레임 표시
        st.write("날짜별 수집 현황")
        st.dataframe(
            merged_df,
            use_container_width=True
        )
        



def main():
    """메인 대시보드 실행 함수"""
    setup_page()
    render_dashboard()

if __name__ == "__main__":
    db = Database()
    db.create_tables()
    main()