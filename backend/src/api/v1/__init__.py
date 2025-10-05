"""API v1 endpoints."""

from fastapi import APIRouter

from . import auth, flows, executions, agents, tools, chat

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(flows.router, prefix="/flows", tags=["Flows"])
api_router.include_router(executions.router, prefix="/executions", tags=["Executions"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(tools.router, prefix="/tools", tags=["Tools"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])

__all__ = ["api_router"]
