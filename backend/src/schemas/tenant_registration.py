"""Pydantic schemas for tenant registration and approval."""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from uuid import UUID
from datetime import datetime


class CompanySizeEnum(str):
    """Company size enumeration matching the model."""
    SIZE_1_10 = "1-10"
    SIZE_11_50 = "11-50"
    SIZE_51_200 = "51-200"
    SIZE_201_1000 = "201-1000"
    SIZE_1000_PLUS = "1000+"


class RegistrationStatusEnum(str):
    """Registration status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TenantRegistrationRequest(BaseModel):
    """Request schema for tenant registration (public endpoint)."""

    company_name: str = Field(..., min_length=2, max_length=255, description="Company/organization name")
    admin_email: EmailStr = Field(..., description="Email address for tenant administrator")
    admin_name: str = Field(..., min_length=2, max_length=255, description="Full name of tenant administrator")
    reason: str = Field(..., min_length=20, max_length=1000, description="Reason for registration")
    sample_data_requested: bool = Field(default=False, description="Request sample data to explore platform")
    company_size: Optional[str] = Field(None, description="Company size category")
    use_case: Optional[str] = Field(None, description="Primary use case for platform")

    @validator('company_size')
    def validate_company_size(cls, v):
        """Validate company size is one of the allowed values."""
        if v is not None and v not in [
            "1-10", "11-50", "51-200", "201-1000", "1000+"
        ]:
            raise ValueError("Invalid company size. Must be one of: 1-10, 11-50, 51-200, 201-1000, 1000+")
        return v


class TenantRegistrationResponse(BaseModel):
    """Response schema for tenant registration."""

    id: UUID
    company_name: str
    admin_email: str
    admin_name: str
    reason: str
    sample_data_requested: bool
    company_size: Optional[str] = None
    use_case: Optional[str] = None
    status: str
    rejection_reason: Optional[str] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    tenant_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2: orm_mode replacement


class RegistrationStatusResponse(BaseModel):
    """Response for checking registration status."""

    status: str = Field(..., description="Status: pending, approved, rejected, or not_found")
    submitted_at: Optional[datetime] = Field(None, description="When registration was submitted")
    message: Optional[str] = Field(None, description="Status message")


class PendingRegistrationsResponse(BaseModel):
    """Response for listing pending registrations."""

    registrations: list[TenantRegistrationResponse]
    total: int


class ApprovalNotesRequest(BaseModel):
    """Request for approval with optional notes."""

    notes: Optional[str] = Field(None, description="Internal notes for approval")


class RejectionRequest(BaseModel):
    """Request for rejection with required reason."""

    reason: str = Field(..., min_length=10, description="Reason for rejection (shown to requester)")


class TenantInfo(BaseModel):
    """Tenant information in approval response."""

    id: UUID
    name: str
    status: str


class AdminUserInfo(BaseModel):
    """Admin user information in approval response."""

    id: UUID
    email: str
    temporary_password: str


class ApprovalResponse(BaseModel):
    """Response for tenant registration approval."""

    registration: TenantRegistrationResponse
    tenant: TenantInfo
    admin_user: AdminUserInfo
    sample_data_loaded: bool


class SampleDataResponse(BaseModel):
    """Response for sample data installation."""

    message: str
    sample_data: dict = Field(..., description="Summary of created sample data")
