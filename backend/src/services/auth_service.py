"""Authentication service for user registration, login, and token management."""

import secrets
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from passlib.context import CryptContext

from ..models import User, Tenant
from ..schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
)
from ..utils.jwt import create_access_token
from .tenant_service import TenantService

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    async def register(
        db: Session, request: RegisterRequest
    ) -> RegisterResponse:
        """
        Register a new user and optionally create a new tenant.

        Args:
            db: Database session
            request: Registration request data

        Returns:
            Registration response with user and tenant IDs

        Raises:
            HTTPException: If email already exists
        """
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create tenant if tenant_name provided
        tenant = None
        if request.tenant_name:
            tenant_service = TenantService()
            tenant = await tenant_service.create_tenant(
                db=db,
                name=request.tenant_name,
            )
        else:
            # Get default tenant or create one
            tenant = db.query(Tenant).first()
            if not tenant:
                tenant_service = TenantService()
                tenant = await tenant_service.create_tenant(
                    db=db,
                    name="Default Organization",
                )

        # Create user
        hashed_password = AuthService.hash_password(request.password)
        user = User(
            tenant_id=tenant.id,
            email=request.email,
            password_hash=hashed_password,
            full_name=request.full_name,
            role="admin" if request.tenant_name else "member",
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return RegisterResponse(
            user_id=user.id,
            tenant_id=tenant.id,
            email=user.email,
            message="Registration successful",
        )

    @staticmethod
    async def login(db: Session, request: LoginRequest) -> LoginResponse:
        """
        Authenticate user and generate access token.

        Args:
            db: Database session
            request: Login request data

        Returns:
            Login response with access token

        Raises:
            HTTPException: If credentials are invalid
        """
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Verify password
        if not AuthService.verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        # Get tenant info
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Tenant not found",
            )

        # Check tenant status
        if tenant.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tenant is {tenant.status}",
            )

        # Create access token
        access_token = create_access_token(
            user_id=user.id,
            tenant_id=tenant.id,
            tenant_schema=tenant.schema_name,
            role=user.role,
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            tenant_id=tenant.id,
            role=user.role,
        )

    @staticmethod
    async def get_current_user(db: Session, user_id: int) -> Optional[User]:
        """
        Get current user by ID.

        Args:
            db: Database session
            user_id: User ID from token

        Returns:
            User object or None
        """
        return db.query(User).filter(User.id == user_id).first()
