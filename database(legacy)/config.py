"""
Database configuration module for CommentWatch
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Database configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/commentwatch')

# Create engine and session factory
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


def init_db():
    """Initialize database by creating all tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
