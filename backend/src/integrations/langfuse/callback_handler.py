"""
CrewAI Langfuse callback handler for LLM execution tracing.

Captures LLM interactions with <2% overhead (FR-021) and sends them to Langfuse
for observability. Implements graceful degradation if Langfuse is unavailable.
"""

import asyncio
import time
from typing import Optional, Dict, Any, TYPE_CHECKING
from uuid import UUID
from datetime import datetime

from langfuse import Langfuse

from src.config.langfuse import get_langfuse_client

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class CrewAILangfuseHandler:
    """
    Async callback handler for CrewAI LLM execution tracing.

    Captures LLM start, end, and error events with minimal overhead (<2%).
    Propagates execution context (execution_id, tenant_id, agent_id, tool_id).
    """

    def __init__(
        self,
        execution_id: UUID,
        tenant_id: UUID,
        langfuse_client: Optional[Langfuse] = None,
        enable_async: bool = True,
        db_session: Optional["Session"] = None
    ):
        """
        Initialize Langfuse callback handler.

        Args:
            execution_id: UUID of the current execution
            tenant_id: UUID of the tenant
            langfuse_client: Optional Langfuse client (defaults to global client)
            enable_async: Enable async trace sending (reduces overhead)
            db_session: Optional database session for trace persistence
        """
        self.execution_id = execution_id
        self.tenant_id = tenant_id
        self.enable_async = enable_async
        self.db_session = db_session

        # Get Langfuse client (may be None if disabled)
        self.client = langfuse_client or get_langfuse_client()

        # Active traces (keyed by trace_id)
        self._active_traces: Dict[str, Dict[str, Any]] = {}

        # Completed traces for batch persistence
        self._completed_traces: list[Dict[str, Any]] = []

        # Performance tracking
        self._overhead_ms = 0
        self._trace_count = 0

    async def on_llm_start(
        self,
        agent_id: Optional[UUID] = None,
        tool_id: Optional[UUID] = None,
        prompt: str = "",
        model_name: str = "",
        provider: str = "",
        **kwargs
    ) -> str:
        """
        Called when LLM interaction starts.

        Args:
            agent_id: UUID of the agent making the call
            tool_id: UUID of the tool making the call
            prompt: Input prompt text
            model_name: LLM model name (e.g., gpt-4)
            provider: LLM provider (e.g., openai)
            **kwargs: Additional context

        Returns:
            trace_id: Unique identifier for this trace
        """
        start_time = time.time()

        # Generate trace_id
        trace_id = f"{self.execution_id}_{int(time.time() * 1000)}"

        # Store trace context
        trace_context = {
            "trace_id": trace_id,
            "execution_id": str(self.execution_id),
            "tenant_id": str(self.tenant_id),
            "agent_id": str(agent_id) if agent_id else None,
            "tool_id": str(tool_id) if tool_id else None,
            "prompt": prompt,
            "model_name": model_name,
            "provider": provider,
            "start_time": datetime.utcnow(),
            "start_timestamp": time.time(),
            **kwargs
        }

        self._active_traces[trace_id] = trace_context

        # Send to Langfuse asynchronously if enabled
        if self.client and self.enable_async:
            asyncio.create_task(self._send_trace_start(trace_context))

        # Track overhead
        overhead = (time.time() - start_time) * 1000
        self._overhead_ms += overhead

        return trace_id

    async def on_llm_end(
        self,
        trace_id: str,
        response: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd: float,
        latency_ms: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Called when LLM interaction completes successfully.

        Args:
            trace_id: Trace identifier from on_llm_start
            response: LLM response text
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_tokens: Total tokens (should equal prompt + completion)
            cost_usd: Estimated cost in USD
            latency_ms: LLM call latency in milliseconds
            **kwargs: Additional context

        Returns:
            trace_data: Complete trace data for persistence
        """
        start_time = time.time()

        # Get trace context
        trace_context = self._active_traces.get(trace_id, {})

        if not trace_context:
            # Trace not found (shouldn't happen, but handle gracefully)
            return {}

        # Complete trace data
        end_time = datetime.utcnow()
        trace_data = {
            **trace_context,
            "response": response,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "end_time": end_time,
            "error_message": None,
            **kwargs
        }

        # Send to Langfuse asynchronously
        if self.client and self.enable_async:
            asyncio.create_task(self._send_trace_end(trace_data))

        # Store for batch persistence
        self._completed_traces.append(trace_data)

        # Persist to database if session provided
        if self.db_session:
            asyncio.create_task(self._persist_trace(trace_data))

        # Clean up active trace
        self._active_traces.pop(trace_id, None)

        # Track overhead
        overhead = (time.time() - start_time) * 1000
        self._overhead_ms += overhead
        self._trace_count += 1

        return trace_data

    async def on_llm_error(
        self,
        trace_id: str,
        error_message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Called when LLM interaction fails.

        Args:
            trace_id: Trace identifier from on_llm_start
            error_message: Error description
            **kwargs: Additional context

        Returns:
            trace_data: Trace data with error information
        """
        start_time = time.time()

        # Get trace context
        trace_context = self._active_traces.get(trace_id, {})

        if not trace_context:
            return {}

        # Complete trace data with error
        end_time = datetime.utcnow()
        trace_data = {
            **trace_context,
            "response": "",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "latency_ms": int((time.time() - trace_context.get("start_timestamp", time.time())) * 1000),
            "end_time": end_time,
            "error_message": error_message,
            **kwargs
        }

        # Send to Langfuse asynchronously
        if self.client and self.enable_async:
            asyncio.create_task(self._send_trace_error(trace_data))

        # Store for batch persistence
        self._completed_traces.append(trace_data)

        # Persist to database if session provided
        if self.db_session:
            asyncio.create_task(self._persist_trace(trace_data))

        # Clean up active trace
        self._active_traces.pop(trace_id, None)

        # Track overhead
        overhead = (time.time() - start_time) * 1000
        self._overhead_ms += overhead
        self._trace_count += 1

        return trace_data

    async def _send_trace_start(self, trace_context: Dict[str, Any]):
        """Send trace start event to Langfuse (async, fire-and-forget)."""
        if not self.client:
            return

        try:
            # Create Langfuse trace
            self.client.trace(
                id=trace_context["trace_id"],
                name=f"LLM Call - {trace_context['model_name']}",
                user_id=trace_context["tenant_id"],
                metadata={
                    "execution_id": trace_context["execution_id"],
                    "agent_id": trace_context.get("agent_id"),
                    "tool_id": trace_context.get("tool_id"),
                    "provider": trace_context["provider"],
                    "model": trace_context["model_name"],
                },
                input=trace_context["prompt"]
            )

            # Flush asynchronously (non-blocking)
            await asyncio.to_thread(self.client.flush)

        except Exception as e:
            # Graceful degradation - log error but don't fail execution
            print(f"Warning: Failed to send trace start to Langfuse: {e}")

    async def _send_trace_end(self, trace_data: Dict[str, Any]):
        """Send trace completion event to Langfuse (async, fire-and-forget)."""
        if not self.client:
            return

        try:
            # Update Langfuse trace
            self.client.trace(
                id=trace_data["trace_id"],
                output=trace_data["response"],
                metadata={
                    "execution_id": trace_data["execution_id"],
                    "agent_id": trace_data.get("agent_id"),
                    "tool_id": trace_data.get("tool_id"),
                    "provider": trace_data["provider"],
                    "model": trace_data["model_name"],
                    "prompt_tokens": trace_data["prompt_tokens"],
                    "completion_tokens": trace_data["completion_tokens"],
                    "total_tokens": trace_data["total_tokens"],
                    "cost_usd": trace_data["cost_usd"],
                    "latency_ms": trace_data["latency_ms"],
                }
            )

            # Flush asynchronously
            await asyncio.to_thread(self.client.flush)

        except Exception as e:
            print(f"Warning: Failed to send trace end to Langfuse: {e}")

    async def _send_trace_error(self, trace_data: Dict[str, Any]):
        """Send trace error event to Langfuse (async, fire-and-forget)."""
        if not self.client:
            return

        try:
            # Update Langfuse trace with error
            self.client.trace(
                id=trace_data["trace_id"],
                metadata={
                    "execution_id": trace_data["execution_id"],
                    "agent_id": trace_data.get("agent_id"),
                    "tool_id": trace_data.get("tool_id"),
                    "provider": trace_data["provider"],
                    "model": trace_data["model_name"],
                    "error": trace_data["error_message"],
                    "latency_ms": trace_data["latency_ms"],
                }
            )

            # Flush asynchronously
            await asyncio.to_thread(self.client.flush)

        except Exception as e:
            print(f"Warning: Failed to send trace error to Langfuse: {e}")

    def get_overhead_percentage(self, total_execution_time_ms: float) -> float:
        """
        Calculate tracing overhead as percentage of total execution time.

        Args:
            total_execution_time_ms: Total execution time in milliseconds

        Returns:
            overhead_percentage: Overhead as percentage (should be <2% per FR-021)
        """
        if total_execution_time_ms == 0:
            return 0.0

        return (self._overhead_ms / total_execution_time_ms) * 100

    def get_trace_count(self) -> int:
        """Get number of traces captured."""
        return self._trace_count

    async def _persist_trace(self, trace_data: Dict[str, Any]):
        """
        Persist trace to PostgreSQL database (async, fire-and-forget).

        Args:
            trace_data: Complete trace data
        """
        if not self.db_session:
            return

        try:
            from src.services.trace_service import TraceService

            trace_service = TraceService(self.db_session)
            await trace_service.create_trace(trace_data)

        except Exception as e:
            # Graceful degradation - log error but don't fail execution
            print(f"Warning: Failed to persist trace to database: {e}")

    async def flush(self):
        """Flush all pending traces to Langfuse and persist to database."""
        if self.client:
            try:
                await asyncio.to_thread(self.client.flush)
            except Exception as e:
                print(f"Warning: Failed to flush Langfuse traces: {e}")

        # Persist any remaining traces
        if self.db_session and self._completed_traces:
            try:
                from src.services.trace_service import TraceService

                trace_service = TraceService(self.db_session)
                for trace_data in self._completed_traces:
                    await trace_service.create_trace(trace_data)

                # Clear completed traces after persistence
                self._completed_traces.clear()

            except Exception as e:
                print(f"Warning: Failed to batch persist traces to database: {e}")

    def get_completed_traces(self) -> list[Dict[str, Any]]:
        """Get all completed traces for this execution."""
        return self._completed_traces.copy()
