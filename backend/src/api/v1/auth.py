"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db.postgres import get_db
from ...schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
)
from ...services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new user and optionally create a new tenant.

    - **email**: Valid email address
    - **password**: Minimum 8 characters
    - **full_name**: User's full name
    - **tenant_name**: Optional - creates new tenant if provided
    """
    return await AuthService.register(db, request)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return JWT access token.

    - **email**: User's email
    - **password**: User's password

    Returns JWT token for subsequent authenticated requests.
    """
    return await AuthService.login(db, request)


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    """
    Refresh an expired access token using a refresh token.

    - **refresh_token**: Valid refresh token from previous login

    Returns new access token and optionally new refresh token.
    """
    auth_service = AuthService(db)
    try:
        # Validate and decode refresh token
        token_data = await auth_service.validate_refresh_token(refresh_token)

        # Generate new access token
        new_access_token = await auth_service.create_access_token(
            user_id=token_data["user_id"],
            tenant_id=token_data["tenant_id"]
        )

        # Optionally rotate refresh token for enhanced security
        new_refresh_token = await auth_service.create_refresh_token(
            user_id=token_data["user_id"],
            tenant_id=token_data["tenant_id"]
        )

        return LoginResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
