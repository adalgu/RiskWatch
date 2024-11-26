PostgreSQL은 강력하고 유연한 데이터베이스 시스템으로, 뉴스 수집기와 같은 비동기 모듈과 잘 통합될 수 있습니다. 최신 개발 관행을 반영하여 PostgreSQL용 DB 모듈을 설계하고 구현하기 위한 단계별 가이드를 제공하겠습니다. 이 가이드는 비동기 지원, ORM 사용, 데이터베이스 스키마 설계, 마이그레이션 관리, 그리고 모듈 간 독립성 유지 등을 포함합니다.

1. 선택할 도구 및 라이브러리

   • SQLAlchemy 2.0: 최신 버전으로 비동기 지원을 포함하며, 강력한 ORM 기능을 제공합니다.
   • Asyncpg: 고성능 비동기 PostgreSQL 드라이버입니다. SQLAlchemy와 함께 사용할 수도 있습니다.
   • Alembic: SQLAlchemy와 함께 사용하는 데이터베이스 마이그레이션 도구입니다.
   • Pydantic: 데이터 검증 및 설정 관리를 위한 라이브러리로, 모델 정의에 유용합니다.

2. 데이터베이스 스키마 설계

뉴스 수집기가 수집하는 데이터는 메타데이터, 콘텐츠, 댓글로 나뉩니다. 이를 기반으로 다음과 같은 테이블을 설계할 수 있습니다:

테이블 구조

    1.	articles: 뉴스 기사의 메타데이터를 저장합니다.
    2.	contents: 뉴스 기사의 본문과 관련 정보를 저장합니다.
    3.	comments: 뉴스 기사의 댓글을 저장합니다.
    4.	comment_stats: 댓글 통계 정보를 저장합니다.

ER 다이어그램 개요

articles (1) <--- (1) contents
articles (1) <--- (N) comments
comments (1) <--- (1) comment_stats

SQLAlchemy 모델 예제

from sqlalchemy import (
Column, String, Integer, Boolean, ForeignKey, DateTime, JSON, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

class Article(Base):
**tablename** = 'articles'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    naver_link = Column(String, unique=True, nullable=False)
    original_link = Column(String, unique=True, nullable=False)
    description = Column(String)
    publisher = Column(String)
    publisher_domain = Column(String)
    published_at = Column(DateTime(timezone=True))
    published_date = Column(String)
    collected_at = Column(DateTime(timezone=True))
    is_naver_news = Column(Boolean, default=False)

    content = relationship("Content", uselist=False, back_populates="article")
    comments = relationship("Comment", back_populates="article")

class Content(Base):
**tablename** = 'contents'

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey('articles.id'), unique=True)
    subheadings = Column(JSONB)  # List[str]
    content = Column(String)
    reporter = Column(String)
    media = Column(String)
    published_at = Column(DateTime(timezone=True))
    modified_at = Column(DateTime(timezone=True))
    category = Column(String)
    images = Column(JSONB)  # List[dict]
    collected_at = Column(DateTime(timezone=True))

    article = relationship("Article", back_populates="content")

class Comment(Base):
**tablename** = 'comments'

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey('articles.id'))
    comment_no = Column(String, unique=True, nullable=False)
    parent_comment_no = Column(String, nullable=True)
    content = Column(String)
    author = Column(String)
    profile_url = Column(String)
    timestamp = Column(DateTime(timezone=True))
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    is_reply = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    delete_type = Column(String, nullable=True)  # 'user', 'admin', or None
    collected_at = Column(DateTime(timezone=True))

    article = relationship("Article", back_populates="comments")
    stats = relationship("CommentStats", uselist=False, back_populates="comment")

class CommentStats(Base):
**tablename** = 'comment_stats'

    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey('comments.id'), unique=True)
    total_count = Column(Integer)
    published_at = Column(DateTime(timezone=True))
    current_count = Column(Integer)
    user_deleted_count = Column(Integer)
    admin_deleted_count = Column(Integer)
    gender_ratio = Column(JSONB)  # {'male': int, 'female': int}
    age_distribution = Column(JSONB)  # {'10s': int, '20s': int, ...}
    collected_at = Column(DateTime(timezone=True))

    comment = relationship("Comment", back_populates="stats")

3. 설정 및 연결

database.py 모듈 생성

비동기 SQLAlchemy를 설정하고 데이터베이스에 연결하기 위한 모듈을 작성합니다.

import os
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv() # .env 파일에서 환경 변수 로드

DATABASE_URL = os.getenv('DATABASE_URL') # 예: postgresql+asyncpg://user:password@localhost/dbname

# 비동기 엔진 생성

engine: AsyncEngine = create_async_engine(
DATABASE_URL,
echo=True, # 개발 중에는 True로 설정하여 SQL 로그 확인
pool_size=20,
max_overflow=0,
poolclass=NullPool # 필요에 따라 조정
)

# 세션 팩토리 생성

async*session = sessionmaker(
bind=engine,
expire_on_commit=False,
class*=AsyncSession
)

# 데이터베이스 초기화 함수

async def init_db():
import models # 모델을 임포트하여 메타데이터가 등록되도록 함
async with engine.begin() as conn:
await conn.run_sync(Base.metadata.create_all)

환경 변수 설정

.env 파일을 사용하여 데이터베이스 URL을 관리합니다.

DATABASE_URL=postgresql+asyncpg://user:password@localhost/news_db

4. 데이터베이스 마이그레이션

Alembic을 사용하여 데이터베이스 스키마를 관리합니다.

Alembic 설정

    1.	Alembic 초기화

alembic init alembic

    2.	alembic.ini 파일 수정

sqlalchemy.url을 환경 변수로 설정합니다.

sqlalchemy.url = postgresql+asyncpg://user:password@localhost/news_db

    3.	env.py 수정

비동기 엔진을 지원하도록 env.py를 수정합니다.

from logging.config import fileConfig
import asyncio
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context
import os
from dotenv import load_dotenv

# Load environment variables

load_dotenv()

# this is the Alembic Config object, which provides

# access to the values within the .ini file in use.

config = context.config

# Interpret the config file for Python logging.

fileConfig(config.config_file_name)

# Import models for autogenerate

from models import Base # models.py에서 Base 임포트

target_metadata = Base.metadata

def run_migrations_offline():
"""Run migrations in 'offline' mode."""
url = os.getenv('DATABASE_URL')
context.configure(
url=url,
target_metadata=target_metadata,
literal_binds=True,
dialect_opts={"paramstyle": "named"},
)

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
"""Run migrations in 'online' mode."""
connectable = AsyncEngine(
engine_from_config(
config.get_section(config.config_ini_section),
prefix='sqlalchemy.',
poolclass=pool.NullPool,
future=True,
)
)

    async with connectable.connect() as connection:
        await connection.run_sync(lambda conn: context.configure(
            connection=conn,
            target_metadata=target_metadata,
            compare_type=True,  # 기존 타입과 비교
        ))
        await connection.begin()
        try:
            await context.run_migrations()
            await connection.commit()
        except:
            await connection.rollback()
            raise

if context.is_offline_mode():
run_migrations_offline()
else:
asyncio.run(run_migrations_online())

    4.	마이그레이션 생성 및 적용

alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

5. DB 모듈 구현

CRUD 기능 구현

각 수집기 모듈이 데이터베이스와 상호 작용할 수 있도록 CRUD(Create, Read, Update, Delete) 기능을 구현합니다. 아래는 예시로 articles 테이블에 데이터를 삽입하는 함수입니다.

# db_operations.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Article, Content, Comment, CommentStats
from datetime import datetime
from typing import List, Dict

async def create_article(session: AsyncSession, article_data: Dict) -> Article:
article = Article(
title=article_data['title'],
naver_link=article_data['naver_link'],
original_link=article_data['original_link'],
description=article_data.get('description'),
publisher=article_data.get('publisher'),
publisher_domain=article_data.get('publisher_domain'),
published_at=datetime.fromisoformat(article_data['published_at']),
published_date=article_data.get('published_date'),
collected_at=datetime.fromisoformat(article_data['collected_at']),
is_naver_news=article_data.get('is_naver_news', False)
)
session.add(article)
await session.commit()
await session.refresh(article)
return article

async def create_content(session: AsyncSession, content_data: Dict, article_id: int) -> Content:
content = Content(
article_id=article_id,
subheadings=content_data.get('subheadings'),
content=content_data.get('content'),
reporter=content_data.get('reporter'),
media=content_data.get('media'),
published_at=datetime.fromisoformat(content_data['published_at']),
modified_at=datetime.fromisoformat(content_data['modified_at']),
category=content_data.get('category'),
images=content_data.get('images'),
collected_at=datetime.fromisoformat(content_data['collected_at'])
)
session.add(content)
await session.commit()
await session.refresh(content)
return content

async def create_comments(session: AsyncSession, comments_data: List[Dict], article_id: int) -> List[Comment]:
comments = []
for data in comments_data:
comment = Comment(
article_id=article_id,
comment_no=data['comment_no'],
parent_comment_no=data.get('parent_comment_no'),
content=data.get('content'),
author=data.get('author'),
profile_url=data.get('profile_url'),
timestamp=datetime.fromisoformat(data['timestamp']),
likes=data.get('likes', 0),
dislikes=data.get('dislikes', 0),
reply_count=data.get('reply_count', 0),
is_reply=data.get('is_reply', False),
is_deleted=data.get('is_deleted', False),
delete_type=data.get('delete_type'),
collected_at=datetime.fromisoformat(data['collected_at'])
)
session.add(comment)
comments.append(comment)
await session.commit()
for comment in comments:
await session.refresh(comment)
return comments

async def create_comment_stats(session: AsyncSession, stats_data: Dict, comment_id: int) -> CommentStats:
stats = CommentStats(
comment_id=comment_id,
total_count=stats_data['total_count'],
published_at=datetime.fromisoformat(stats_data['published_at']),
current_count=stats_data['stats']['current_count'],
user_deleted_count=stats_data['stats']['user_deleted_count'],
admin_deleted_count=stats_data['stats']['admin_deleted_count'],
gender_ratio=stats_data['stats']['gender_ratio'],
age_distribution=stats_data['stats']['age_distribution'],
collected_at=datetime.fromisoformat(stats_data['collected_at'])
)
session.add(stats)
await session.commit()
await session.refresh(stats)
return stats

트랜잭션 관리 및 비동기 세션 사용

뉴스 수집기의 각 모듈에서 DB 작업을 수행할 때, 비동기 세션을 사용하여 트랜잭션을 관리합니다.

# example_usage.py

from database import async_session
from db_operations import create_article, create_content, create_comments, create_comment_stats
from datetime import datetime

async def store_collected_data(metadata_result, content_result, comment_result):
async with async_session() as session:
async with session.begin(): # Article 생성
article = await create_article(session, metadata_result['articles'][0])

            # Content 생성
            await create_content(session, content_result['content'], article.id)

            # Comments 생성
            comments = await create_comments(session, comment_result['comments'], article.id)

            # CommentStats 생성 (예시: 첫 번째 댓글에 통계 추가)
            if comment_result.get('stats') and comments:
                await create_comment_stats(session, comment_result['stats'], comments[0].id)

6. 수집기 모듈과 DB 모듈 통합

뉴스 수집기의 각 수집기(메타데이터, 콘텐츠, 댓글)에서 데이터를 수집한 후 DB 모듈의 CRUD 함수를 호출하여 데이터를 저장합니다.

예시: MetadataCollector와 DB 통합

# metadata_collector.py

from db_operations import create_article
from database import async_session

class MetadataCollector:
async def collect(self, method, keyword, \*\*kwargs): # 데이터 수집 로직 (API 또는 검색 방식)
result = {...} # 수집된 데이터
return result

    async def save_to_db(self, data):
        async with async_session() as session:
            async with session.begin():
                article = await create_article(session, data)
                # 추가적인 저장 로직

예시: 전체 수집 및 저장 프로세스

# main.py

import asyncio
from collectors.metadata_collector import MetadataCollector
from collectors.content_collector import ContentCollector
from collectors.comment_collector import CommentCollector
from example_usage import store_collected_data

async def main(): # 메타데이터 수집
metadata_collector = MetadataCollector()
metadata_result = await metadata_collector.collect(
method='api',
keyword='검색어',
max_articles=10
)

    # 콘텐츠 수집
    content_collector = ContentCollector()
    content_tasks = [
        content_collector.collect(article['naver_link'])
        for article in metadata_result['articles']
    ]
    content_results = await asyncio.gather(*content_tasks)

    # 댓글 수집
    comment_collector = CommentCollector()
    comment_tasks = [
        comment_collector.collect(article['naver_link'], include_stats=True)
        for article in metadata_result['articles']
    ]
    comment_results = await asyncio.gather(*comment_tasks)

    # 데이터베이스에 저장
    save_tasks = [
        store_collected_data(metadata, content, comment)
        for metadata, content, comment in zip(metadata_result['articles'], content_results, comment_results)
    ]
    await asyncio.gather(*save_tasks)

if **name** == '**main**':
asyncio.run(main())

7. 추가 고려 사항

1. 데이터 유효성 검증

Pydantic을 사용하여 데이터의 유효성을 검증할 수 있습니다. 이는 데이터베이스에 잘못된 데이터가 저장되는 것을 방지합니다.

from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

class ArticleModel(BaseModel):
title: str
naver_link: HttpUrl
original_link: HttpUrl
description: Optional[str]
publisher: Optional[str]
publisher_domain: Optional[str]
published_at: datetime
published_date: str
collected_at: datetime
is_naver_news: bool = False

class ContentModel(BaseModel):
subheadings: List[str]
content: str
reporter: str
media: str
published_at: datetime
modified_at: datetime
category: str
images: List[dict]
collected_at: datetime

class CommentModel(BaseModel):
comment_no: str
parent_comment_no: Optional[str]
content: str
author: str
profile_url: HttpUrl
timestamp: datetime
likes: int = 0
dislikes: int = 0
reply_count: int = 0
is_reply: bool = False
is_deleted: bool = False
delete_type: Optional[str]
collected_at: datetime

class CommentStatsModel(BaseModel):
total_count: int
published_at: datetime
stats: dict
collected_at: datetime

2. 에러 핸들링 및 로깅

DB 모듈에서 발생할 수 있는 예외를 적절히 처리하고, 로깅을 통해 문제를 추적할 수 있도록 합니다.

import logging

logger = logging.getLogger(**name**)

async def create_article(session: AsyncSession, article_data: Dict) -> Article:
try:
article = Article(
title=article_data['title'],
naver_link=article_data['naver_link'],
original_link=article_data['original_link'],
description=article_data.get('description'),
publisher=article_data.get('publisher'),
publisher_domain=article_data.get('publisher_domain'),
published_at=datetime.fromisoformat(article_data['published_at']),
published_date=article_data.get('published_date'),
collected_at=datetime.fromisoformat(article_data['collected_at']),
is_naver_news=article_data.get('is_naver_news', False)
)
session.add(article)
await session.commit()
await session.refresh(article)
return article
except Exception as e:
logger.error(f"Error creating article: {e}")
await session.rollback()
raise

3. 성능 최적화

   • 배치 삽입: 대량의 데이터를 삽입할 때는 배치 삽입을 사용하여 성능을 향상시킵니다.
   • 인덱스 최적화: 자주 조회하는 컬럼에 인덱스를 추가하여 조회 성능을 높입니다.
   • 커넥션 풀링: SQLAlchemy의 커넥션 풀 설정을 최적화하여 동시 연결을 효율적으로 관리합니다.

4. 테스트 작성

DB 모듈의 기능을 검증하기 위한 단위 테스트 및 통합 테스트를 작성합니다. pytest와 같은 테스트 프레임워크를 사용할 수 있습니다.

# test_db_operations.py

import pytest
from database import async_session, init_db
from db_operations import create_article
from models import Base

@pytest.fixture(scope='module')
async def setup_database():
await init_db()
yield # 테스트 후 데이터베이스 정리 로직 추가

@pytest.mark.asyncio
async def test_create_article(setup_database):
async with async_session() as session:
article_data = {
'title': 'Test Article',
'naver_link': 'https://n.news.naver.com/article/test',
'original_link': 'https://original.link/test',
'description': 'Test Description',
'publisher': 'Test Publisher',
'publisher_domain': 'testpublisher.com',
'published_at': '2024-03-20T14:30:00+09:00',
'published_date': '2024.03.20',
'collected_at': '2024-04-01T10:00:00+09:00',
'is_naver_news': True
}
article = await create_article(session, article_data)
assert article.id is not None
assert article.title == 'Test Article'

8. 모듈 독립성 유지

DB 모듈과 뉴스 수집기 모듈을 독립적으로 유지하기 위해 다음과 같은 방법을 사용할 수 있습니다:
• 명확한 인터페이스 정의: DB 모듈이 제공하는 함수와 클래스의 인터페이스를 명확히 정의하여 다른 모듈이 쉽게 사용할 수 있도록 합니다.
• 의존성 관리: DB 모듈은 필요한 의존성만을 포함하고, 다른 모듈에 대한 의존성을 가지지 않도록 설계합니다.
• 패키지화: DB 모듈을 별도의 패키지로 구성하여 다른 프로젝트에서도 재사용할 수 있도록 합니다.

예시: 인터페이스 정의

# db_interface.py

from typing import Dict, List
from models import Article, Content, Comment, CommentStats

class DBInterface:
async def add_article(self, article_data: Dict) -> Article:
pass

    async def add_content(self, content_data: Dict, article_id: int) -> Content:
        pass

    async def add_comments(self, comments_data: List[Dict], article_id: int) -> List[Comment]:
        pass

    async def add_comment_stats(self, stats_data: Dict, comment_id: int) -> CommentStats:
        pass

구현 예시

# db_operations.py

from db_interface import DBInterface
from models import Article, Content, Comment, CommentStats
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List

class PostgresDB(DBInterface):
async def add_article(self, article_data: Dict) -> Article: # 구현 내용
...

    async def add_content(self, content_data: Dict, article_id: int) -> Content:
        # 구현 내용
        ...

    async def add_comments(self, comments_data: List[Dict], article_id: int) -> List[Comment]:
        # 구현 내용
        ...

    async def add_comment_stats(self, stats_data: Dict, comment_id: int) -> CommentStats:
        # 구현 내용
        ...

이렇게 인터페이스를 정의하면, DB 구현체를 교체하거나 다른 데이터베이스로 확장할 때도 수집기 모듈에 영향을 주지 않고 변경할 수 있습니다.

결론

PostgreSQL용 DB 모듈을 현대적으로 설계하고 구현하기 위해서는 비동기 ORM 사용, 효율적인 스키마 설계, 마이그레이션 관리, 그리고 모듈 간 독립성 유지가 중요합니다. 위에서 제공한 가이드와 예시 코드를 바탕으로, 더욱 발전된 DB 모듈을 구축할 수 있을 것입니다. 필요에 따라 추가적인 최적화와 기능 확장을 고려하여 프로젝트의 요구 사항에 맞게 조정하시기 바랍니다.
