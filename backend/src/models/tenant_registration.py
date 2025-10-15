"""TenantRegistration model for managing tenant registration approval workflow."""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class RegistrationStatus(str, enum.Enum):
    """Registration status enumeration."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CompanySize(str, enum.Enum):
    """Company size enumeration."""

    SIZE_1_10 = "1-10"
    SIZE_11_50 = "11-50"
    SIZE_51_200 = "51-200"
    SIZE_201_1000 = "201-1000"
    SIZE_1000_PLUS = "1000+"


class TenantRegistration(BaseModel):
    """
    Tenant registration model for super admin approval workflow.

    Tracks registration requests from prospective tenants,
    requiring super admin approval before tenant creation.
    """

    __tablename__ = "tenant_registrations"

    # Company information
    company_name = Column(String(255), nullable=False, index=True)
    admin_email = Column(String(255), nullable=False, unique=True, index=True)
    admin_name = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)

    # Optional fields
    sample_data_requested = Column(Boolean, nullable=False, default=False)
    company_size = Column(Enum(CompanySize), nullable=True)
    use_case = Column(Text, nullable=True)

    # Status tracking
    status = Column(Enum(RegistrationStatus), nullable=False, default=RegistrationStatus.PENDING, index=True)
    rejection_reason = Column(Text, nullable=True)

    # Approval tracking
    approved_by = Column(postgresql.UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Tenant reference (populated after approval)
    tenant_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)

    # Relationships
    approver = relationship("User", foreign_keys=[approved_by])
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    def __repr__(self):
        return f"<TenantRegistration(id={self.id}, company={self.company_name}, status={self.status})>"
