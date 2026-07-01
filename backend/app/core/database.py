"""
Database configuration and models for audit history.
"""
import os
from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional


class AuditRecord(SQLModel, table=True):
    """Audit history record stored in SQLite."""
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(index=True)
    timestamp: str
    overall_score: float
    categories: str
    results_json: str


# Database file path
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "audit_history.db")

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db() -> None:
    """Initialize database tables on startup."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Dependency for FastAPI routes to get a database session."""
    with Session(engine) as session:
        yield session
