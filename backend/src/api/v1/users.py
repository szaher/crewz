"""User profile and management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db.postgres import get_db
from ..middleware.auth import require_auth
from ...models import User
from ...schemas.user_profile import (
    UserProfileResponse,
    UserProfileUpdate,
    UserAdminResponse,
    UserCreateRequest,
    UserUpdateRequest,
    UserListResponse,
)
from pydantic import BaseModel, Field, EmailStr
from ...services.auth_service import AuthService
import secrets
from datetime import datetime, timedelta


router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Return the current authenticated user's profile."""
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    role_val = getattr(user.role, 'value', user.role)
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=role_val,
        tenant_id=user.tenant_id,
        is_active=bool(user.is_active),
    )


@router.put("/me", response_model=UserProfileResponse)
async def update_me(
    update: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Update allowed fields on current user's profile (e.g., full_name)."""
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.full_name = update.full_name
    db.commit()
    db.refresh(user)

    role_val = getattr(user.role, 'value', user.role)
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=role_val,
        tenant_id=user.tenant_id,
        is_active=bool(user.is_active),
    )


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)


@router.post("/me/change-password")
async def change_password(
    body: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Change current user's password after verifying the current password."""
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Verify current password
    if not AuthService.verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    # Update password
    user.password_hash = AuthService.hash_password(body.new_password)
    db.commit()

    return {"message": "Password updated"}


def _ensure_admin(current_user: dict):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


@router.get("", response_model=UserListResponse)
async def list_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """List users in the current tenant (admin only)."""
    _ensure_admin(current_user)

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    query = db.query(User).filter(User.tenant_id == current_user["tenant_id"])
    if q:
        pattern = f"%{q}%"
        from sqlalchemy import or_
        query = query.filter(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    def _map(u: User) -> UserAdminResponse:
        role_val = getattr(u.role, 'value', u.role)
        return UserAdminResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=role_val,
            is_active=bool(u.is_active),
            created_at=u.created_at.isoformat(),
        )

    return UserListResponse(users=[_map(u) for u in users], total=total, page=page, page_size=page_size)


@router.post("", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Create a new user in the current tenant (admin only)."""
    _ensure_admin(current_user)

    # Check email uniqueness
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create user
    user = User(
        tenant_id=current_user["tenant_id"],
        email=body.email,
        password_hash=AuthService.hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    role_val = getattr(user.role, 'value', user.role)
    return UserAdminResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=role_val,
        is_active=bool(user.is_active),
        created_at=user.created_at.isoformat(),
    )


@router.put("/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Update a user in the current tenant (admin only)."""
    _ensure_admin(current_user)

    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == current_user["tenant_id"])
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = AuthService.hash_password(body.password)

    db.commit()
    db.refresh(user)

    role_val = getattr(user.role, 'value', user.role)
    return UserAdminResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=role_val,
        is_active=bool(user.is_active),
        created_at=user.created_at.isoformat(),
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Delete a user in the current tenant (admin only). Prevent self-delete."""
    _ensure_admin(current_user)

    if user_id == current_user["id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")

    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == current_user["tenant_id"])
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.delete(user)
    db.commit()

    return {"status": "deleted"}


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field('member', pattern=r'^(admin|member|viewer)$')
    expires_in_hours: int = Field(168, ge=1, le=24*30)  # default 7 days


class InviteUserResponse(BaseModel):
    invite_token: str
    expires_at: str


@router.post("/invite", response_model=InviteUserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: InviteUserRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Invite a new user by generating a password set token (admin only)."""
    _ensure_admin(current_user)

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=body.expires_in_hours)

    temp_password = secrets.token_urlsafe(12)
    user = User(
        tenant_id=current_user["tenant_id"],
        email=body.email,
        password_hash=AuthService.hash_password(temp_password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
        password_reset_token=token,
        password_reset_expires=expires,
        require_password_change=True,
    )
    db.add(user)
    db.commit()

    return InviteUserResponse(invite_token=token, expires_at=expires.isoformat())
