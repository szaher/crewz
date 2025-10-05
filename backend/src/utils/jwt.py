"""JWT token utilities for authentication."""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import HTTPException, status

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours


def create_access_token(
    user_id: int,
    tenant_id: int,
    tenant_schema: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID
        tenant_id: Tenant ID
        tenant_schema: PostgreSQL schema name for the tenant
        role: User role (admin, member, viewer)
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.utcnow() + expires_delta

    to_encode = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "tenant_schema": tenant_schema,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def extract_tenant_from_token(token: str) -> tuple[int, str]:
    """
    Extract tenant information from JWT token.

    Args:
        token: JWT token string

    Returns:
        Tuple of (tenant_id, tenant_schema)

    Raises:
        HTTPException: If token is invalid or missing tenant info
    """
    payload = verify_token(token)

    tenant_id = payload.get("tenant_id")
    tenant_schema = payload.get("tenant_schema")

    if not tenant_id or not tenant_schema:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing tenant information",
        )

    return tenant_id, tenant_schema


def get_user_id_from_token(token: str) -> int:
    """
    Extract user ID from JWT token.

    Args:
        token: JWT token string

    Returns:
        User ID

    Raises:
        HTTPException: If token is invalid or missing user ID
    """
    payload = verify_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )

    return int(user_id)
