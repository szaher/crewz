"""Tenant model for multi-tenancy."""

from sqlalchemy import Column, String, Boolean, Integer, Enum, JSON
from sqlalchemy.orm import relationship, deferred
from .base import BaseModel
import enum


class TenantStatus(str, enum.Enum):
    """Tenant status enumeration."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Tenant(BaseModel):
    """
    Tenant model for schema-per-tenant isolation.

    Each tenant gets its own PostgreSQL schema for data isolation.
    """

    __tablename__ = "tenants"

    name = Column(String(255), nullable=False)
    schema_name = Column(String(63), nullable=False, unique=True, index=True)
    status = Column(Enum(TenantStatus), nullable=False, default=TenantStatus.ACTIVE)
    api_key = Column(String(255), nullable=False, unique=True, index=True)

    # Resource limits
    max_users = Column(Integer, nullable=False, default=10)
    max_agents = Column(Integer, nullable=False, default=50)
    max_flows = Column(Integer, nullable=False, default=100)

    # Optional structured settings
    settings = deferred(Column(JSON, nullable=False, default=dict))

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name}, schema={self.schema_name})>"
