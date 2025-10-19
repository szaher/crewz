"""WebSocket stream handler for execution output streaming.

Captures stdout/stderr, emits execution.output events to Socket.IO room,
buffers last 100 lines in Redis for reconnection replay.
"""
import time
from datetime import datetime
from typing import Optional, List
from src.config.settings import Settings


class StreamHandler:
    """Handler for streaming execution output via WebSocket."""

    BUFFER_SIZE = 100  # Keep last 100 lines in Redis

    def __init__(self, execution_id: str, redis_client=None):
        """
        Initialize stream handler.

        Args:
            execution_id: Execution UUID string
            redis_client: Redis client (injected for testing)
        """
        self.execution_id = execution_id
        self.room_name = f"execution:{execution_id}"
        self.buffer_key = f"execution_buffer:{execution_id}"

        # Collect all logs for artifact creation
        self.log_lines = []

        if redis_client:
            self.redis = redis_client
        else:
            import redis
            settings = Settings()
            self.redis = redis.from_url(str(settings.REDIS_URL), decode_responses=True)

        # Socket.IO client (will be initialized when available)
        self.socketio = None
        self._init_socketio()

    def _init_socketio(self):
        """Initialize Socket.IO client if available."""
        try:
            # Import Socket.IO if available
            # For now, we'll emit to Redis pub/sub as fallback
            pass
        except ImportError:
            pass

    def emit_started(self, worker_id: str):
        """
        Emit execution.started event.

        Args:
            worker_id: Worker hostname
        """
        event = {
            "event": "execution.started",
            "job_id": self.execution_id,
            "worker_id": worker_id,
            "started_at": datetime.utcnow().isoformat()
        }

        self._emit_event(event)

    def emit_output(self, line: str, stream_type: str = "stdout"):
        """
        Emit execution.output event.

        Args:
            line: Output line
            stream_type: "stdout" or "stderr"
        """
        # Collect log line for artifact creation
        timestamp = datetime.utcnow().isoformat()
        self.log_lines.append({
            "line": line,
            "stream_type": stream_type,
            "timestamp": timestamp
        })

        event = {
            "event": "execution.output",
            "line": line,
            "timestamp": timestamp,
            "stream_type": stream_type
        }

        self._emit_event(event)
        self._buffer_line(line, stream_type)

    def emit_progress(self, percent: int, current_step: str, total_steps: int):
        """
        Emit execution.progress event.

        Args:
            percent: Progress percentage (0-100)
            current_step: Current step description
            total_steps: Total number of steps
        """
        event = {
            "event": "execution.progress",
            "percent": percent,
            "current_step": current_step,
            "total_steps": total_steps
        }

        self._emit_event(event)

    def emit_completed(self, status: str, result_summary: str, artifacts: List[dict] = None):
        """
        Emit execution.completed event.

        Args:
            status: "completed", "failed", or "cancelled"
            result_summary: Summary of results
            artifacts: List of artifact metadata dicts
        """
        event = {
            "event": "execution.completed",
            "status": status,
            "result_summary": result_summary,
            "artifacts": artifacts or []
        }

        self._emit_event(event)

    def emit_error(self, error_type: str, message: str, traceback: Optional[str] = None):
        """
        Emit execution.error event.

        Args:
            error_type: Error type/class name
            message: Error message
            traceback: Stack trace (optional)
        """
        event = {
            "event": "execution.error",
            "error_type": error_type,
            "message": message,
            "traceback": traceback
        }

        self._emit_event(event)

    def _emit_event(self, event: dict):
        """
        Emit event to WebSocket room.

        Args:
            event: Event data dict
        """
        import json

        # Publish to Redis pub/sub channel
        # This allows Socket.IO server to pick up events
        channel = f"execution_events:{self.execution_id}"
        self.redis.publish(channel, json.dumps(event))

    def _buffer_line(self, line: str, stream_type: str):
        """
        Buffer output line in Redis (keep last 100 lines).

        Args:
            line: Output line
            stream_type: "stdout" or "stderr"
        """
        import json

        buffered_line = json.dumps({
            "line": line,
            "stream_type": stream_type,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Add to Redis list
        self.redis.lpush(self.buffer_key, buffered_line)

        # Trim to last 100 lines
        self.redis.ltrim(self.buffer_key, 0, self.BUFFER_SIZE - 1)

        # Set expiration (1 hour)
        self.redis.expire(self.buffer_key, 3600)

    def get_buffered_lines(self) -> List[dict]:
        """
        Get buffered output lines for replay on reconnect.

        Returns:
            List of line dicts (oldest first)
        """
        import json

        # Get all buffered lines (returns newest first from Redis)
        lines_json = self.redis.lrange(self.buffer_key, 0, -1)

        # Parse and reverse (to get oldest first)
        lines = [json.loads(line) for line in lines_json]
        lines.reverse()

        return lines

    def clear_buffer(self):
        """Clear buffered output lines."""
        self.redis.delete(self.buffer_key)

    def get_all_logs(self) -> str:
        """
        Get all collected logs as a formatted string.

        Returns:
            Formatted log string with timestamps
        """
        log_text = []
        for log in self.log_lines:
            timestamp = log.get("timestamp", "")
            stream_type = log.get("stream_type", "stdout")
            line = log.get("line", "")
            log_text.append(f"[{timestamp}] [{stream_type.upper()}] {line}")

        return "\n".join(log_text)


class OutputCapture:
    """
    Context manager to capture stdout/stderr and stream via WebSocket.

    Usage:
        with OutputCapture(stream_handler) as capture:
            print("This will be streamed")
            # ... execution code ...
    """

    def __init__(self, stream_handler: StreamHandler):
        """
        Initialize output capture.

        Args:
            stream_handler: StreamHandler instance
        """
        self.stream_handler = stream_handler
        self.original_stdout = None
        self.original_stderr = None

    def __enter__(self):
        """Start capturing output."""
        import sys
        from io import StringIO

        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # Create capturing streams
        self.stdout_capture = StringIO()
        self.stderr_capture = StringIO()

        sys.stdout = self._create_streaming_wrapper(self.stdout_capture, "stdout")
        sys.stderr = self._create_streaming_wrapper(self.stderr_capture, "stderr")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original stdout/stderr."""
        import sys

        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

    def _create_streaming_wrapper(self, buffer, stream_type):
        """Create a file-like wrapper that streams output."""
        class StreamingWrapper:
            def __init__(self, buffer, stream_handler, stream_type):
                self.buffer = buffer
                self.stream_handler = stream_handler
                self.stream_type = stream_type

            def write(self, text):
                self.buffer.write(text)
                if text.strip():  # Only emit non-empty lines
                    self.stream_handler.emit_output(text, stream_type=self.stream_type)

            def flush(self):
                self.buffer.flush()

        return StreamingWrapper(buffer, self.stream_handler, stream_type)
