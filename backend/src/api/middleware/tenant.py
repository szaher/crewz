"""Tenant context middleware for schema isolation."""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text

from ...db.postgres import SessionLocal


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set PostgreSQL search_path based on tenant context.

    This ensures that all database queries within a request are scoped
    to the correct tenant schema.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with tenant context.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint handler

        Returns:
            HTTP response
        """
        # Skip tenant context for public endpoints
        public_paths = [
            "/health",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/docs",
            "/openapi.json",
        ]

        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        # Get tenant schema from request state (set by auth middleware)
        tenant_schema = getattr(request.state, "tenant_schema", None)

        if tenant_schema:
            # Create database session with tenant context
            db = SessionLocal()
            try:
                # Set search_path for this connection
                db.execute(text(f"SET search_path TO {tenant_schema}, public"))
                db.commit()

                # Store db session in request state
                request.state.db = db

                response = await call_next(request)
                return response
            finally:
                # Reset search_path
                db.execute(text("SET search_path TO public"))
                db.close()
        else:
            # No tenant context (e.g., unauthenticated request)
            return await call_next(request)


def get_tenant_db(request: Request):
    """
    Dependency to get database session with tenant context.

    Usage:
        @router.get("/flows")
        async def list_flows(db: Session = Depends(get_tenant_db)):
            # Queries will be scoped to tenant schema
            flows = db.query(Flow).all()
            return flows
    """
    return request.state.db if hasattr(request.state, "db") else None
