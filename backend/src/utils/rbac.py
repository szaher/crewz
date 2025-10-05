"""Role-Based Access Control utilities."""

from typing import List
from functools import wraps
from fastapi import HTTPException, status

# Role hierarchy
ROLES = {
    "admin": 3,
    "member": 2,
    "viewer": 1,
}

# Permission matrix: resource -> action -> required role level
PERMISSIONS = {
    "flows": {
        "read": 1,  # viewer
        "create": 2,  # member
        "update": 2,  # member
        "delete": 3,  # admin
        "execute": 2,  # member
    },
    "agents": {
        "read": 1,
        "create": 2,
        "update": 2,
        "delete": 3,
    },
    "crews": {
        "read": 1,
        "create": 2,
        "update": 2,
        "delete": 3,
    },
    "tools": {
        "read": 1,
        "create": 2,
        "update": 2,
        "delete": 3,
    },
    "users": {
        "read": 2,  # members can see users
        "create": 3,  # only admins can create users
        "update": 3,
        "delete": 3,
    },
    "executions": {
        "read": 1,
        "create": 2,
        "cancel": 2,  # can cancel own executions
    },
    "chat": {
        "read": 1,
        "create": 1,
        "update": 2,
        "delete": 2,
    },
}


def check_permission(user_role: str, resource: str, action: str) -> bool:
    """
    Check if a user role has permission for a resource action.

    Args:
        user_role: User role (admin, member, viewer)
        resource: Resource type (flows, agents, etc.)
        action: Action to perform (read, create, update, delete)

    Returns:
        True if permission granted, False otherwise
    """
    user_level = ROLES.get(user_role, 0)

    if resource not in PERMISSIONS:
        return False

    required_level = PERMISSIONS[resource].get(action, 999)

    return user_level >= required_level


def require_role(required_roles: List[str]):
    """
    Decorator to enforce role requirements on endpoints.

    Args:
        required_roles: List of roles that are allowed

    Usage:
        @require_role(["admin", "member"])
        async def create_flow(...):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs (set by auth middleware)
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            user_role = current_user.get("role")

            if user_role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {required_roles}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_permission(resource: str, action: str):
    """
    Decorator to enforce permission requirements on endpoints.

    Args:
        resource: Resource type
        action: Action to perform

    Usage:
        @require_permission("flows", "create")
        async def create_flow(...):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            user_role = current_user.get("role")

            if not check_permission(user_role, resource, action):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions for {action} on {resource}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
