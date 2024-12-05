# modules/database.py

from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import Column, Date, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field, Session, create_engine
from typing import Optional
import os
import pytz
from news_storage.src.models import Article, Content, Comment, CommentStats

# 한국 표준시(KST) 설정
KST = pytz.timezone('Asia/Seoul')

def get_kst_now():
    """Return current time in KST"""
    return datetime.now(KST)

class Event(SQLModel, table=True):
    __tablename__ = 'events'

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    date: datetime = Field(sa_column=Column(Date, nullable=False))
    description: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )

class Database:
    def __init__(self, db_url=None):
        db_url = db_url or os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/news_db')
        self.engine = create_engine(db_url)
        self.session = Session(self.engine)

    def create_tables(self):
        SQLModel.metadata.create_all(self.engine)

    def __del__(self):
        self.session.close()

    def get_date_range(self):
        """수집된 기사들의 날짜 범위 가져오기"""
        query = """
            SELECT MIN(published_date), MAX(published_date)
            FROM articles
        """
        result = self.session.execute(sa.text(query)).fetchone()
        return result[0], result[1]

    def get_all_keywords(self):
        """모든 키워드 목록 가져오기"""
        query = """
            SELECT DISTINCT main_keyword
            FROM articles
            ORDER BY main_keyword
        """
        result = self.session.execute(sa.text(query))
        return [row[0] for row in result]

    def get_articles_by_date(self, start_date, end_date, keyword=None):
        """날짜별 전체 기사 수 가져오기"""
        query = """
            SELECT DATE(published_date) as date, COUNT(*) as count
            FROM articles
            WHERE published_date BETWEEN :start_date AND :end_date
        """
        if keyword and keyword != "전체":
            query += " AND main_keyword = :keyword"
        query += " GROUP BY DATE(published_date) ORDER BY date"
        
        params = {"start_date": start_date, "end_date": end_date}
        if keyword and keyword != "전체":
            params["keyword"] = keyword
            
        return self.session.execute(sa.text(query), params).fetchall()

    def get_naver_articles_by_date(self, start_date, end_date, keyword=None):
        """날짜별 네이버 뉴스 기사 수 가져오기"""
        query = """
            SELECT DATE(a.published_date) as date, COUNT(*) as count
            FROM articles a
            WHERE a.published_date BETWEEN :start_date AND :end_date
              AND a.is_naver_news = TRUE
        """
        if keyword and keyword != "전체":
            query += " AND a.main_keyword = :keyword"
        query += " GROUP BY DATE(a.published_date) ORDER BY date"
        
        params = {"start_date": start_date, "end_date": end_date}
        if keyword and keyword != "전체":
            params["keyword"] = keyword
            
        return self.session.execute(sa.text(query), params).fetchall()

    def get_comments_by_date(self, start_date, end_date, keyword=None):
        """날짜별 댓글 수 가져오기"""
        query = """
            SELECT DATE(c.timestamp) as date, COUNT(*) as count
            FROM comments c
            JOIN articles a ON c.article_id = a.id
            WHERE c.timestamp BETWEEN :start_date AND :end_date
        """
        if keyword and keyword != "전체":
            query += " AND a.main_keyword = :keyword"
        query += " GROUP BY DATE(c.timestamp) ORDER BY date"
        
        params = {"start_date": start_date, "end_date": end_date}
        if keyword and keyword != "전체":
            params["keyword"] = keyword
            
        return self.session.execute(sa.text(query), params).fetchall()

    def get_articles_details_by_date(self, date, keyword=None):
        """특정 날짜의 기사 상세 정보 가져오기"""
        query = """
            SELECT title, publisher, naver_link, published_at
            FROM articles
            WHERE DATE(published_date) = :date
        """
        if keyword and keyword != "전체":
            query += " AND main_keyword = :keyword"
        query += " ORDER BY published_at DESC"
        
        params = {"date": date}
        if keyword and keyword != "전체":
            params["keyword"] = keyword
                
        return self.session.execute(sa.text(query), params).fetchall()

    def get_events(self):
        return self.session.query(Event).all()

    def add_event(self, date, description):
        event = Event(date=date, description=description)
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def update_event(self, event_id, date=None, description=None):
        event = self.session.query(Event).filter(Event.id == event_id).first()
        if event:
            if date:
                event.date = date
            if description:
                event.description = description
            self.session.commit()
            self.session.refresh(event)
        return event

    def delete_event(self, event_id):
        event = self.session.query(Event).filter(Event.id == event_id).first()
        if event:
            self.session.delete(event)
            self.session.commit()
        return event
