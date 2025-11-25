"""
Async SQLAlchemy helpers and schema definition for audit logs.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import ARRAY, Column, DateTime, MetaData, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()
metadata = MetaData()

audit_logs_table = Table(
    "audit_logs",
    metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True, default=uuid4),
    Column("timestamp", DateTime(timezone=True), nullable=False, default=datetime.utcnow),
    Column("route", String(32), nullable=False),
    Column("prompt", Text, nullable=False),
    Column("detected_topics", ARRAY(String(32)), nullable=False, default=list),
)


def _build_async_url() -> str:
    db_url = settings.resolved_database_url
    if "postgresql+psycopg" in db_url:
        return db_url.replace("postgresql+psycopg", "postgresql+asyncpg")
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return db_url


engine = create_async_engine(_build_async_url(), echo=settings.debug)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

