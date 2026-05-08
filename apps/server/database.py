
from __future__ import annotations

import datetime
import os

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# NOTE: The original scaffold imported a non-existent `create_all`.
# We keep schema management centralized via `Base.metadata.create_all`.

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@db/echoinsight")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class MediaTask(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, index=True)
    filename = Column(String)
    source_type = Column(String, nullable=True)  # upload | youtube
    source_url = Column(Text, nullable=True)
    storage_path = Column(Text, nullable=True)
    status = Column(String, default="PENDING") # PENDING, PROCESSING, COMPLETED, FAILED
    transcript_text = Column(Text, nullable=True)
    summary_text = Column(Text, nullable=True)
    result_text = Column(Text, nullable=True)  # legacy alias for summary_text
    error_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class MediaChunk(Base):
    __tablename__ = "chunks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    idx = Column(Integer, nullable=False)
    start_s = Column(Float, nullable=True)
    end_s = Column(Float, nullable=True)
    text = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)  # JSON list[float]

def _ensure_tasks_columns() -> None:
    insp = inspect(engine)
    if "tasks" not in insp.get_table_names():
        return

    existing = {c["name"] for c in insp.get_columns("tasks")}
    desired: dict[str, str] = {
        "source_type": "VARCHAR",
        "source_url": "TEXT",
        "storage_path": "TEXT",
        "transcript_text": "TEXT",
        "summary_text": "TEXT",
        "error_text": "TEXT",
        "result_text": "TEXT",
    }

    with engine.begin() as conn:
        for col, typ in desired.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col} {typ}"))

def init_db():
    Base.metadata.create_all(bind=engine)
    _ensure_tasks_columns()
