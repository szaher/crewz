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
    db: Session = Depends(get_db),
    # TODO: Add refresh token logic
):
    """
    Refresh an expired access token.

    Not yet implemented - placeholder for future enhancement.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh not yet implemented",
    )
