"""API v1 endpoints."""

from fastapi import APIRouter

from . import auth, flows, executions, agents, tools, chat, crews  # , llm_providers

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(flows.router, prefix="/flows", tags=["Flows"])
api_router.include_router(executions.router, prefix="/executions", tags=["Executions"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(crews.router, prefix="/crews", tags=["Crews"])
api_router.include_router(tools.router, prefix="/tools", tags=["Tools"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
# api_router.include_router(llm_providers.router, prefix="/llm-providers", tags=["LLM Providers"])

__all__ = ["api_router"]
