from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, DateTime, Boolean, JSON, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

class Base(DeclarativeBase): pass

def utcnow(): return datetime.now(timezone.utc)

class Case(Base):
    __tablename__ = 'cases'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(80), default='RFA')
    subject: Mapped[str] = mapped_column(String(1000), default='')
    sender: Mapped[str] = mapped_column(String(500), default='')
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(40), default='pending')
    problem_statement: Mapped[str] = mapped_column(Text, default='')
    recommendation: Mapped[str] = mapped_column(Text, default='')
    explainability: Mapped[dict] = mapped_column(JSON, default=dict)
    draft_body: Mapped[str] = mapped_column(Text, default='')
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    extracted: Mapped[dict] = mapped_column(JSON, default=dict)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_key: Mapped[str] = mapped_column(String(255), index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(255), default='system')
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Feedback(Base):
    __tablename__ = 'feedback'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_key: Mapped[str] = mapped_column(String(255), index=True)
    decision: Mapped[str] = mapped_column(String(50))
    note: Mapped[str] = mapped_column(Text, default='')
    edited_draft: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(engine)
