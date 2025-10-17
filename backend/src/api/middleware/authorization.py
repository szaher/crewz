"""Authorization middleware for automatic permission checks on API endpoints."""

from typing import Optional, Callable, List
from uuid import UUID
from functools import wraps
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from ...db.postgres import get_db
from ...services.authorization_service import AuthorizationService
from .auth import require_auth


def require_permission(
    resource_type: str,
    action: str,
    resource_id_param: Optional[str] = None,
):
    """
    Decorator to require specific permission for an endpoint.

    Args:
        resource_type: Type of resource (e.g., 'crew', 'flow', 'agent')
        action: Action to check ('read', 'write', 'execute', 'delete')
        resource_id_param: Path/query parameter name containing resource ID (optional)

    Usage:
        @router.get("/crews/{crew_id}")
        @require_permission("crew", "read", resource_id_param="crew_id")
        async def get_crew(crew_id: UUID, ...):
            ...

        @router.post("/crews")
        @require_permission("crew", "write")  # No resource_id for create
        async def create_crew(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request, current_user, and db from kwargs
            request: Optional[Request] = kwargs.get('request')
            current_user: Optional[dict] = kwargs.get('current_user')
            db: Optional[Session] = kwargs.get('db')

            if not request or not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authorization middleware misconfigured: missing dependencies"
                )

            # Extract user info
            user_id = UUID(current_user['id']) if isinstance(current_user['id'], str) else current_user['id']
            tenant_id = UUID(current_user['tenant_id']) if isinstance(current_user['tenant_id'], str) else current_user['tenant_id']

            # Extract resource_id if parameter specified
            resource_id: Optional[UUID] = None
            if resource_id_param:
                # Check path parameters first
                if resource_id_param in kwargs:
                    resource_id = kwargs[resource_id_param]
                # Then check query parameters
                elif hasattr(request, 'query_params') and resource_id_param in request.query_params:
                    resource_id = UUID(request.query_params[resource_id_param])

            # Get request metadata
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent')

            # Check permission
            authz_service = AuthorizationService(db)
            result = authz_service.check_permission(
                user_id=user_id,
                tenant_id=tenant_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            if result['decision'] == 'deny':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {result['reason']}"
                )

            # Permission granted, call the actual endpoint
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_any_permission(
    checks: List[tuple[str, str, Optional[str]]],
):
    """
    Decorator to require any one of multiple permissions (OR logic).

    Args:
        checks: List of (resource_type, action, resource_id_param) tuples

    Usage:
        @router.get("/crews/{crew_id}/execute")
        @require_any_permission([
            ("crew", "execute", "crew_id"),
            ("crew", "write", "crew_id"),  # Admins with write can also execute
        ])
        async def execute_crew(crew_id: UUID, ...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies
            request: Optional[Request] = kwargs.get('request')
            current_user: Optional[dict] = kwargs.get('current_user')
            db: Optional[Session] = kwargs.get('db')

            if not request or not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authorization middleware misconfigured: missing dependencies"
                )

            # Extract user info
            user_id = UUID(current_user['id']) if isinstance(current_user['id'], str) else current_user['id']
            tenant_id = UUID(current_user['tenant_id']) if isinstance(current_user['tenant_id'], str) else current_user['tenant_id']
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent')

            authz_service = AuthorizationService(db)
            all_denied = True
            last_reason = ""

            # Check each permission (OR logic)
            for resource_type, action, resource_id_param in checks:
                # Extract resource_id if parameter specified
                resource_id: Optional[UUID] = None
                if resource_id_param:
                    if resource_id_param in kwargs:
                        resource_id = kwargs[resource_id_param]
                    elif hasattr(request, 'query_params') and resource_id_param in request.query_params:
                        resource_id = UUID(request.query_params[resource_id_param])

                # Check permission
                result = authz_service.check_permission(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                if result['decision'] == 'allow':
                    # At least one permission allows, grant access
                    all_denied = False
                    break

                last_reason = result['reason']

            if all_denied:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {last_reason}"
                )

            # Permission granted, call the actual endpoint
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_all_permissions(
    checks: List[tuple[str, str, Optional[str]]],
):
    """
    Decorator to require all permissions (AND logic).

    Args:
        checks: List of (resource_type, action, resource_id_param) tuples

    Usage:
        @router.post("/crews/{crew_id}/share")
        @require_all_permissions([
            ("crew", "read", "crew_id"),  # Must be able to read the crew
            ("user", "write", None),       # Must be able to modify users
        ])
        async def share_crew(crew_id: UUID, ...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies
            request: Optional[Request] = kwargs.get('request')
            current_user: Optional[dict] = kwargs.get('current_user')
            db: Optional[Session] = kwargs.get('db')

            if not request or not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authorization middleware misconfigured: missing dependencies"
                )

            # Extract user info
            user_id = UUID(current_user['id']) if isinstance(current_user['id'], str) else current_user['id']
            tenant_id = UUID(current_user['tenant_id']) if isinstance(current_user['tenant_id'], str) else current_user['tenant_id']
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent')

            authz_service = AuthorizationService(db)

            # Check all permissions (AND logic)
            for resource_type, action, resource_id_param in checks:
                # Extract resource_id if parameter specified
                resource_id: Optional[UUID] = None
                if resource_id_param:
                    if resource_id_param in kwargs:
                        resource_id = kwargs[resource_id_param]
                    elif hasattr(request, 'query_params') and resource_id_param in request.query_params:
                        resource_id = UUID(request.query_params[resource_id_param])

                # Check permission
                result = authz_service.check_permission(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                if result['decision'] == 'deny':
                    # Any permission denies, deny access
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {result['reason']}"
                    )

            # All permissions granted, call the actual endpoint
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_super_admin(func: Callable):
    """
    Decorator to require super admin role.

    Usage:
        @router.get("/admin/tenants/pending")
        @require_super_admin
        async def list_pending_tenants(...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user: Optional[dict] = kwargs.get('current_user')

        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        if not current_user.get('is_super_admin', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super admin access required"
            )

        return await func(*args, **kwargs)

    return wrapper


def require_tenant_admin(func: Callable):
    """
    Decorator to require tenant admin role.

    Usage:
        @router.post("/authz/roles")
        @require_tenant_admin
        async def create_role(...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user: Optional[dict] = kwargs.get('current_user')

        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        role = current_user.get('role', '')
        if role not in ['admin', 'tenant-admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant admin role required"
            )

        return await func(*args, **kwargs)

    return wrapper
