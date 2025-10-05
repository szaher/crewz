"""PostgreSQL connection and multi-tenant session management."""

import os
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager

from ..models.base import Base

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://crewai:dev_password@localhost:5432/crewai_platform"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables in public schema."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session for public schema (tenants table).

    Usage:
        db = next(get_db())
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_tenant_db(schema_name: str) -> Generator[Session, None, None]:
    """
    Get database session with tenant schema isolation.

    Args:
        schema_name: PostgreSQL schema name for the tenant

    Usage:
        with get_tenant_db("tenant_abc") as db:
            agents = db.query(Agent).all()
    """
    db = SessionLocal()
    try:
        # Set search_path to tenant schema
        db.execute(text(f"SET search_path TO {schema_name}, public"))
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        # Reset search_path
        db.execute(text("SET search_path TO public"))
        db.close()


def create_tenant_schema(schema_name: str) -> None:
    """
    Create a new tenant schema and initialize tables.

    Args:
        schema_name: PostgreSQL schema name for the tenant
    """
    with engine.connect() as conn:
        # Create schema
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        conn.commit()

        # Set search_path and create tables
        conn.execute(text(f"SET search_path TO {schema_name}, public"))
        Base.metadata.create_all(bind=conn)
        conn.commit()


def drop_tenant_schema(schema_name: str) -> None:
    """
    Drop a tenant schema and all its data.

    Args:
        schema_name: PostgreSQL schema name for the tenant
    """
    with engine.connect() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        conn.commit()
