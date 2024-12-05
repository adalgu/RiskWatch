"""
Data visualization module for the dashboard application.
Provides optimized visualization components and data processing utilities.
"""

import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from plotly.subplots import make_subplots

from .logging_config import get_logger
from .decorators import handle_exceptions, log_execution_time

logger = get_logger('visualization')


class DataProcessor:
    """Data processing utilities for visualization"""

    @staticmethod
    def prepare_trend_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data for trend visualization.

        Args:
            df: Input DataFrame

        Returns:
            Processed DataFrame
        """
        try:
            df_processed = df.copy()

            # Convert to datetime
            df_processed['date'] = pd.to_datetime(df_processed['date'])

            # Sort by date
            df_processed.sort_values('date', inplace=True)

            # Fill missing dates with zeros
            if not df_processed.empty:
                date_range = pd.date_range(
                    df_processed['date'].min(),
                    df_processed['date'].max(),
                    freq='D'
                )
                df_processed.set_index('date', inplace=True)
                df_processed = df_processed.reindex(date_range, fill_value=0)
                df_processed.reset_index(inplace=True)
                df_processed.rename(columns={'index': 'date'}, inplace=True)

            # Calculate moving averages
            if len(df_processed) > 1:
                df_processed['total_ma'] = df_processed['total_article_count'].rolling(
                    window=7, min_periods=1).mean()
                df_processed['naver_ma'] = df_processed['naver_article_count'].rolling(
                    window=7, min_periods=1).mean()
                df_processed['comment_ma'] = df_processed['comment_count'].rolling(
                    window=7, min_periods=1).mean()

            return df_processed

        except Exception as e:
            logger.error(f"Error processing trend data: {str(e)}")
            return df

    @staticmethod
    def calculate_statistics(df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate various statistics from the data.

        Args:
            df: Input DataFrame

        Returns:
            Dictionary of statistics
        """
        try:
            stats = {
                'total_articles': int(df['total_article_count'].sum()),
                'naver_articles': int(df['naver_article_count'].sum()),
                'total_comments': int(df['comment_count'].sum()),
                'avg_comments_per_article': 0,
                'naver_ratio': 0,
                'daily_avg_articles': df['total_article_count'].mean(),
                'daily_avg_comments': df['comment_count'].mean(),
                'max_daily_articles': int(df['total_article_count'].max()),
                'max_daily_comments': int(df['comment_count'].max()),
            }

            if stats['naver_articles'] > 0:
                stats['avg_comments_per_article'] = stats['total_comments'] / \
                    stats['naver_articles']

            if stats['total_articles'] > 0:
                stats['naver_ratio'] = (
                    stats['naver_articles'] / stats['total_articles']) * 100

            return stats

        except Exception as e:
            logger.error(f"Error calculating statistics: {str(e)}")
            return {}


class ChartBuilder:
    """Chart building utilities"""

    @staticmethod
    @handle_exceptions("차트 생성 중 오류가 발생했습니다")
    @log_execution_time
    def create_trend_chart(df: pd.DataFrame) -> Union[go.Figure, None]:
        """
        Create an enhanced trend chart with moving averages.

        Args:
            df: Input DataFrame

        Returns:
            Plotly figure object
        """
        if df.empty:
            logger.warning("Empty DataFrame provided to create_trend_chart")
            return None

        try:
            # Process data
            df_processed = DataProcessor.prepare_trend_data(df)

            # Create figure with secondary y-axis
            fig = make_subplots(specs=[[{"secondary_y": True}]])

            # Add traces for article counts
            fig.add_trace(
                go.Bar(
                    x=df_processed['date'],
                    y=df_processed['total_article_count'],
                    name='전체 기사 수',
                    marker_color='rgba(173, 216, 230, 0.7)',
                    hovertemplate='날짜: %{x}<br>전체 기사 수: %{y:,.0f}<extra></extra>'
                ),
                secondary_y=False
            )

            fig.add_trace(
                go.Bar(
                    x=df_processed['date'],
                    y=df_processed['naver_article_count'],
                    name='네이버 뉴스 기사 수',
                    marker_color='rgba(30, 144, 255, 0.8)',
                    hovertemplate='날짜: %{x}<br>네이버 뉴스 기사 수: %{y:,.0f}<extra></extra>'
                ),
                secondary_y=False
            )

            # Add moving averages
            if 'total_ma' in df_processed.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_processed['date'],
                        y=df_processed['total_ma'],
                        name='전체 기사 추세 (7일)',
                        line=dict(color='rgba(173, 216, 230, 1)',
                                  width=2, dash='dot'),
                        hovertemplate='날짜: %{x}<br>7일 평균: %{y:.1f}<extra></extra>'
                    ),
                    secondary_y=False
                )

            if 'naver_ma' in df_processed.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_processed['date'],
                        y=df_processed['naver_ma'],
                        name='네이버 뉴스 추세 (7일)',
                        line=dict(color='rgba(30, 144, 255, 1)',
                                  width=2, dash='dot'),
                        hovertemplate='날짜: %{x}<br>7일 평균: %{y:.1f}<extra></extra>'
                    ),
                    secondary_y=False
                )

            # Add comment count trace
            fig.add_trace(
                go.Scatter(
                    x=df_processed['date'],
                    y=df_processed['comment_count'],
                    name='댓글 수 (네이버 뉴스)',
                    line=dict(color='#ff7f0e', width=2),
                    hovertemplate='날짜: %{x}<br>댓글 수: %{y:,.0f}<extra></extra>'
                ),
                secondary_y=True
            )

            if 'comment_ma' in df_processed.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_processed['date'],
                        y=df_processed['comment_ma'],
                        name='댓글 추세 (7일)',
                        line=dict(color='rgba(255, 127, 14, 0.7)',
                                  width=2, dash='dot'),
                        hovertemplate='날짜: %{x}<br>7일 평균: %{y:.1f}<extra></extra>'
                    ),
                    secondary_y=True
                )

            # Update layout
            fig.update_layout(
                barmode='overlay',
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(t=50),
                showlegend=True,
                plot_bgcolor='white',
                paper_bgcolor='white',
                xaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(0,0,0,0.1)',
                    title="날짜"
                ),
                yaxis=dict(
                    title="기사 수",
                    showgrid=True,
                    gridcolor='rgba(0,0,0,0.1)',
                    zeroline=True,
                    zerolinecolor='rgba(0,0,0,0.2)',
                    titlefont=dict(color='#1f77b4'),
                    tickfont=dict(color='#1f77b4')
                ),
                yaxis2=dict(
                    title="댓글 수",
                    showgrid=False,
                    titlefont=dict(color='#ff7f0e'),
                    tickfont=dict(color='#ff7f0e'),
                    zeroline=False
                )
            )

            # Add annotation
            fig.add_annotation(
                text="* 댓글 수는 네이버 뉴스 기사 기준 | 점선은 7일 이동평균",
                xref="paper", yref="paper",
                x=0, y=-0.15,
                showarrow=False,
                font=dict(size=10, color="gray"),
                align="left"
            )

            return fig

        except Exception as e:
            logger.error(f"Error creating trend chart: {str(e)}")
            return None

    @staticmethod
    @handle_exceptions("차트 생성 중 오류가 발생했습니다")
    def create_summary_chart(df: pd.DataFrame) -> Union[go.Figure, None]:
        """
        Create a summary chart showing key metrics.

        Args:
            df: Input DataFrame

        Returns:
            Plotly figure object
        """
        try:
            stats = DataProcessor.calculate_statistics(df)

            if not stats:
                return None

            # Create figure
            fig = go.Figure()

            # Add metrics
            metrics = [
                ('전체 기사', stats['total_articles'], '#1f77b4'),
                ('네이버 뉴스', stats['naver_articles'], '#2ca02c'),
                ('총 댓글', stats['total_comments'], '#ff7f0e'),
                ('기사당 평균 댓글', round(
                    stats['avg_comments_per_article'], 1), '#9467bd')
            ]

            # Calculate domain positions
            width = 0.2  # Width of each indicator
            gap = (1.0 - (len(metrics) * width)) / \
                (len(metrics) + 1)  # Gap between indicators

            for i, (label, value, color) in enumerate(metrics):
                x_start = gap + (i * (width + gap))
                x_end = x_start + width

                fig.add_trace(go.Indicator(
                    mode="number",
                    value=value,
                    title={"text": label},
                    domain={'x': [x_start, x_end], 'y': [0, 1]},
                    number={'font': {'color': color, 'size': 24},
                            'valueformat': ',.1f' if isinstance(value, float) else ',d'}
                ))

            fig.update_layout(
                grid={'rows': 1, 'columns': len(metrics)},
                margin=dict(t=30, b=0, l=0, r=0),
                height=150,
                showlegend=False
            )

            return fig

        except Exception as e:
            logger.error(f"Error creating summary chart: {str(e)}")
            return None
