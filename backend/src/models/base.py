"""Base model with common fields."""

from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declarative_base
from ..utils.uuid import generate_uuid_v7

Base = declarative_base()


class BaseModel(Base):
    """Base model with common fields for all entities."""

    __abstract__ = True

    id = Column(postgresql.UUID(as_uuid=True), primary_key=True, default=generate_uuid_v7)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
