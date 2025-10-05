"""Pydantic schemas for request/response validation."""

from .auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    TokenPayload,
)
from .flows import (
    FlowCreate,
    FlowUpdate,
    FlowResponse,
    FlowListResponse,
    NodeData,
    EdgeData,
)
from .agents import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
)
from .tools import (
    ToolCreate,
    ToolUpdate,
    ToolResponse,
    ToolListResponse,
)
from .executions import (
    ExecutionCreate,
    ExecutionResponse,
    ExecutionListResponse,
    ExecutionStatus,
)
from .chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageCreate,
    ChatMessageResponse,
)

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RegisterResponse",
    "TokenPayload",
    # Flows
    "FlowCreate",
    "FlowUpdate",
    "FlowResponse",
    "FlowListResponse",
    "NodeData",
    "EdgeData",
    # Agents
    "AgentCreate",
    "AgentUpdate",
    "AgentResponse",
    "AgentListResponse",
    # Tools
    "ToolCreate",
    "ToolUpdate",
    "ToolResponse",
    "ToolListResponse",
    # Executions
    "ExecutionCreate",
    "ExecutionResponse",
    "ExecutionListResponse",
    "ExecutionStatus",
    # Chat
    "ChatSessionCreate",
    "ChatSessionResponse",
    "ChatMessageCreate",
    "ChatMessageResponse",
]
