"""
UI components module for the dashboard application.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Union, Any

from .logging_config import get_logger
from .decorators import handle_exceptions
from .validators import validate_date_range
from .exceptions import UIError, ValidationError
from .visualization import ChartBuilder, DataProcessor

logger = get_logger('ui')


class DateRangeSelector:
    """Date range selector component with validation"""

    def __init__(self, key_prefix: str, default_days: int = 30, allow_future: bool = True):
        self.key_prefix = key_prefix
        self.default_days = default_days
        self.allow_future = allow_future
        self.default_end_date = datetime.now().date()
        self.default_start_date = (
            self.default_end_date - timedelta(days=default_days))

    @handle_exceptions("날짜 선택 중 오류가 발생했습니다")
    def render(self) -> Tuple[date, date]:
        """Render date range selector with validation"""
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "시작일",
                value=self.default_start_date,
                key=f"{self.key_prefix}_start"
            )
        with col2:
            end_date = st.date_input(
                "종료일",
                value=self.default_end_date,
                key=f"{self.key_prefix}_end"
            )

        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.min.time())

            validate_date_range(
                start_datetime,
                end_datetime
                # allow_future=self.allow_future
            )
        except Exception as e:
            st.error(str(e))
            return None, None

        return start_date, end_date


class KeywordSelector:
    """Keyword selector component with error handling"""

    @staticmethod
    @handle_exceptions("키워드 선택 중 오류가 발생했습니다")
    def render(keywords_data: List[Dict], default_text: str = "전체", key: str = None) -> str:
        """Render keyword selector"""
        return st.selectbox(
            "키워드 선택",
            [default_text] + [k['main_keyword']
                              for k in keywords_data if k.get('main_keyword')],
            key=key
        )


class MetricsDisplay:
    """Metrics display component with error handling"""

    @staticmethod
    @handle_exceptions("지표 표시 중 오류가 발생했습니다")
    def render(df: pd.DataFrame) -> None:
        """Render metrics display with validation"""
        if df.empty:
            logger.warning("Empty DataFrame provided to MetricsDisplay")
            st.warning("표시할 데이터가 없습니다.")
            return

        try:
            fig = ChartBuilder.create_summary_chart(df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                col1, col2, col3, col4 = st.columns(4)
                stats = DataProcessor.calculate_statistics(df)

                with col1:
                    st.metric("전체 기사 수",
                              f"{stats['total_articles']:,d} (네이버 뉴스: {stats['naver_articles']:,d})")
                with col2:
                    st.metric("총 댓글 수",
                              f"{stats['total_comments']:,d} (네이버 뉴스 기준)")
                with col3:
                    st.metric("네이버 뉴스 비율",
                              f"{stats['naver_ratio']:.1f}%")
                with col4:
                    st.metric("네이버 기사당 평균 댓글 수",
                              f"{stats['avg_comments_per_article']:.1f}")
        except Exception as e:
            logger.error(f"Error rendering metrics: {str(e)}")
            st.error("지표 표시 중 오류가 발생했습니다.")


class DataVisualization:
    """Data visualization component with error handling"""

    @staticmethod
    @handle_exceptions("차트 생성 중 오류가 발생했습니다")
    def create_trend_chart(df: pd.DataFrame) -> Union[go.Figure, None]:
        """Create trend chart with validation"""
        if df.empty:
            logger.warning("Empty DataFrame provided to create_trend_chart")
            return None

        try:
            return ChartBuilder.create_trend_chart(df)
        except Exception as e:
            logger.error(f"Error creating trend chart: {str(e)}")
            return None


class DataTable:
    """Data table component with error handling"""

    @staticmethod
    @handle_exceptions("데이터 테이블 표시 중 오류가 발생했습니다")
    def render(df: pd.DataFrame, get_articles_details_func: callable = None, keyword_filter: str = None) -> None:
        """Render data table with validation"""
        if df.empty:
            logger.warning("Empty DataFrame provided to DataTable")
            st.warning("표시할 데이터가 없습니다.")
            return

        try:
            df_display = df.copy()
            df_display.columns = ['날짜', '전체 기사 수',
                                  '네이버 뉴스 기사 수', '댓글 수 (네이버 뉴스)']
            df_display = df_display.fillna(0)

            st.dataframe(
                df_display.style.format({
                    '전체 기사 수': '{:,.0f}',
                    '네이버 뉴스 기사 수': '{:,.0f}',
                    '댓글 수 (네이버 뉴스)': '{:,.0f}'
                })
            )

            # Add date selection for article details
            selected_date = st.date_input("날짜 선택 (기사 목록 보기)", value=None)

            if selected_date and get_articles_details_func:
                # Fetch detailed articles for the selected date
                articles = get_articles_details_func(
                    selected_date, keyword_filter)

                if articles:
                    with st.expander(f"{selected_date.strftime('%Y-%m-%d')} 기사 목록", expanded=True):
                        for article in articles:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"**{article['title']}**")
                                if article['description']:
                                    st.markdown(
                                        f"{article['description'][:200]}...")
                                st.markdown(f"키워드: {article['main_keyword']}")
                            with col2:
                                st.markdown(
                                    f"댓글 수: {article['total_comments']:,d}")
                                if article['published_at']:
                                    st.markdown(
                                        f"발행일: {article['published_at'].strftime('%Y-%m-%d %H:%M')}")

                            # Display links
                            col1, col2 = st.columns(2)
                            with col1:
                                if article['url']:
                                    st.markdown(
                                        f"[네이버 뉴스 링크]({article['url']})")
                            with col2:
                                if article['original_url']:
                                    st.markdown(
                                        f"[언론사 원문 링크]({article['original_url']})")

                            st.markdown("---")
                else:
                    st.info("선택한 날짜에 기사가 없습니다.")

        except Exception as e:
            logger.error(f"Error rendering data table: {str(e)}")
            st.error("데이터 테이블을 표시하는 중 오류가 발생했습니다.")


@handle_exceptions("세션 상태 초기화 중 오류가 발생했습니다")
def initialize_session_state() -> None:
    """Initialize session state variables with error handling"""
    if 'collection_in_progress' not in st.session_state:
        st.session_state.collection_in_progress = False
    if 'last_collection_time' not in st.session_state:
        st.session_state.last_collection_time = None
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 0
    logger.debug("Session state initialized")


@handle_exceptions("데이터 수집 탭 렌더링 중 오류가 발생했습니다")
def render_collection_tab(
    keywords_data: List,
    collect_articles_func: callable,
    collect_comments_func: callable
) -> None:
    """Render data collection tab"""
    st.header("데이터 수집")

    # Article collection section
    st.subheader("기사 수집")
    new_keyword = st.text_input("새로운 키워드")

    date_selector = DateRangeSelector(
        "collect", allow_future=False)
    collect_start_date, collect_end_date = date_selector.render()

    if st.button("기사 수집", key="collect_articles"):
        if new_keyword and collect_start_date and collect_end_date:
            with st.spinner("기사를 수집하는 중..."):
                try:
                    saved_count, skipped_count = collect_articles_func(
                        new_keyword,
                        datetime.combine(collect_start_date,
                                         datetime.min.time()),
                        datetime.combine(collect_end_date, datetime.max.time())
                    )
                    if saved_count > 0:
                        st.success(
                            f"{saved_count}개의 기사가 수집되었습니다. (건너뜀: {skipped_count}개)")
                        st.session_state.active_tab = 1  # Switch to data view tab
                        st.experimental_rerun()
                    else:
                        st.warning("수집된 기사가 없습니다.")
                except ValidationError as e:
                    st.error(str(e))
                except Exception as e:
                    logger.error(f"Error during article collection: {str(e)}")
                    st.error("기사 수집 중 오류가 발생했습니다.")
        else:
            st.error("키워드와 날짜를 모두 입력해주세요.")

    # Comment collection section
    st.subheader("댓글 수집")
    comment_keyword = KeywordSelector.render(
        keywords_data, key="comment_keyword_selector")

    comment_date_selector = DateRangeSelector(
        "comment", allow_future=False)
    comment_start_date, comment_end_date = comment_date_selector.render()

    if st.button("댓글 수집", key="collect_comments"):
        if comment_start_date and comment_end_date:
            with st.spinner("댓글을 수집하는 중..."):
                try:
                    total_comments = collect_comments_func(
                        datetime.combine(comment_start_date,
                                         datetime.min.time()),
                        datetime.combine(comment_end_date,
                                         datetime.max.time()),
                        None if comment_keyword == "전체" else comment_keyword
                    )
                    st.success(f"댓글 수집이 완료되었습니다. (총 {total_comments}개 댓글 수집)")
                    st.session_state.active_tab = 1  # Switch to data view tab
                    st.experimental_rerun()
                except ValidationError as e:
                    st.error(str(e))
                except Exception as e:
                    logger.error(f"Error during comment collection: {str(e)}")
                    st.error("댓글 수집 중 오류가 발생했습니다.")
        else:
            st.error("날짜를 모두 선택해주세요.")


@handle_exceptions("데이터 조회 탭 렌더링 중 오류가 발생했습니다")
def render_data_view_tab(
    get_date_range_func: callable,
    get_keywords_summary_func: callable,
    get_articles_by_date_func: callable,
    get_articles_details_by_date_func: callable
) -> None:
    """Render data view tab"""
    st.header("데이터 조회")

    try:
        min_date, max_date = get_date_range_func()

        # Date range selector for viewing
        default_view_start = min_date if min_date else datetime.now().date() - \
            timedelta(days=30)
        default_view_end = max_date if max_date else datetime.now().date()

        date_selector = DateRangeSelector(
            "view",
            default_days=(default_view_end - default_view_start).days,
            allow_future=True
        )
        start_date, end_date = date_selector.render()

        if not start_date or not end_date:
            return

        # Keyword selector for viewing
        keywords_data = get_keywords_summary_func()
        view_keyword = KeywordSelector.render(
            keywords_data, key="view_keyword_selector")

        # Get filtered data
        keyword_filter = None if view_keyword == "전체" else view_keyword
        daily_data = get_articles_by_date_func(
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.max.time()),
            keyword_filter
        )

        if not daily_data:
            st.warning("선택한 기간에 데이터가 없습니다.")
            return

        # Create DataFrame for visualization
        df = pd.DataFrame(daily_data, columns=[
            'date', 'total_article_count', 'naver_article_count', 'comment_count'
        ])
        df = df.fillna(0)

        # Display metrics
        MetricsDisplay.render(df)

        # Create tabs for different visualizations
        chart_tab1, chart_tab2 = st.tabs(["추세 차트", "상세 데이터"])

        with chart_tab1:
            st.subheader("일별 기사 수집 현황")
            fig = DataVisualization.create_trend_chart(df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        with chart_tab2:
            st.subheader("상세 데이터")
            DataTable.render(
                df, get_articles_details_by_date_func, keyword_filter)

    except Exception as e:
        logger.error(f"Error rendering data view: {str(e)}")
        st.error("데이터 로딩 중 오류가 발생했습니다. 관리자에게 문의해주세요.")


@handle_exceptions("메인 UI 렌더링 중 오류가 발생했습니다")
def render_main_ui(
    keywords_data: List,
    collect_articles_func: callable,
    collect_comments_func: callable,
    get_date_range_func: callable,
    get_keywords_summary_func: callable,
    get_articles_by_date_func: callable,
    get_articles_details_by_date_func: callable
) -> None:
    """Render main UI with tabs"""
    # Create main tabs
    tab1, tab2 = st.tabs(["데이터 수집", "데이터 조회"])

    # Render tabs
    with tab1:
        render_collection_tab(
            keywords_data,
            collect_articles_func,
            collect_comments_func
        )

    with tab2:
        render_data_view_tab(
            get_date_range_func,
            get_keywords_summary_func,
            get_articles_by_date_func,
            get_articles_details_by_date_func
        )

    # Update active tab based on user selection
    if tab1.selected:
        st.session_state.active_tab = 0
    elif tab2.selected:
        st.session_state.active_tab = 1
