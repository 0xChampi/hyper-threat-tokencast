"""
Database session management for Tokencast
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base

# Database URL from environment
# Use SQLite for local development if DATABASE_URL not set
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./tokencast.db"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session for dependency injection

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: Session = Depends(get_db)):
            # use db session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
