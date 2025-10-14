"""Authentication middleware for JWT verification."""

from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ...db.postgres import get_db
from ...utils.jwt import verify_token, get_user_id_from_token, extract_tenant_from_token
from ...services.auth_service import AuthService

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token
        db: Database session

    Returns:
        User information dict with id, email, role, tenant_id, tenant_schema

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Verify and decode token
    try:
        payload = verify_token(token)
    except HTTPException:
        raise

    # Extract user info from token using utility functions
    user_id = get_user_id_from_token(token)  # Returns UUID
    tenant_id, tenant_schema = extract_tenant_from_token(token)  # Returns (UUID, str)
    role = payload.get("role")

    # Fetch user from database to ensure it still exists and is active
    user = await AuthService.get_current_user(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Check if user has super-admin role
    is_super_admin = user.is_super_admin if hasattr(user, 'is_super_admin') else False

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": role,
        "tenant_id": tenant_id,
        "tenant_schema": tenant_schema,
        "is_super_admin": is_super_admin,
    }


def require_auth(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency to require authentication.

    Usage in endpoint:
        @router.get("/protected")
        async def protected_endpoint(user: Dict = Depends(require_auth)):
            return {"user_id": user["id"]}
    """
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
) -> Optional[Dict[str, Any]]:
    """
    Get current user if authenticated, None otherwise.

    Useful for endpoints that have optional authentication.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
