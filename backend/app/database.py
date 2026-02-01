"""
Database Configuration for FinanceApp
Supports SQLite for development and PostgreSQL for production.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database URL - Use environment variable for production
# For development, defaults to SQLite
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./financeapp.db"
)

# For PostgreSQL, use:
# DATABASE_URL = "postgresql://user:password@localhost/financeapp"

# SQLite specific configuration
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}  # Required for SQLite
    )
else:
    engine = create_engine(DATABASE_URL)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency injection for database sessions.
    Use this in FastAPI endpoints: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables.
    Call this on application startup.
    """
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
