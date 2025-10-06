"""ClickHouse feedback ingestion worker via Redis pub/sub."""

import asyncio
import json
from typing import Dict, Any
import structlog
from datetime import datetime

logger = structlog.get_logger()


class FeedbackIngestionWorker:
    """
    Background worker that subscribes to Redis feedback events
    and ingests them into ClickHouse for analytics.
    """

    def __init__(self, redis_client, clickhouse_client):
        """
        Initialize ingestion worker.

        Args:
            redis_client: Redis client instance
            clickhouse_client: ClickHouse client instance
        """
        self.redis = redis_client
        self.clickhouse = clickhouse_client
        self.channel = "feedback:submitted"
        self.running = False
        self.batch = []
        self.batch_size = 100
        self.batch_timeout = 5.0  # seconds

    async def start(self):
        """Start the ingestion worker."""
        self.running = True

        logger.info(
            "feedback_ingestion_worker_starting",
            channel=self.channel,
            batch_size=self.batch_size,
            batch_timeout=self.batch_timeout
        )

        # Create Redis pubsub
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.channel)

        # Start batch flush timer
        flush_task = asyncio.create_task(self._periodic_flush())

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await self._handle_message(message["data"])

                if not self.running:
                    break

        except Exception as e:
            logger.error("feedback_ingestion_worker_error", error=str(e))
            raise
        finally:
            flush_task.cancel()
            await pubsub.unsubscribe(self.channel)
            await self._flush_batch()  # Flush remaining events
            logger.info("feedback_ingestion_worker_stopped")

    async def stop(self):
        """Stop the ingestion worker."""
        logger.info("feedback_ingestion_worker_stopping")
        self.running = False

    async def _handle_message(self, data: bytes):
        """
        Handle incoming feedback event.

        Args:
            data: Raw message data from Redis
        """
        try:
            event = json.loads(data.decode("utf-8"))

            # Transform event for ClickHouse schema
            clickhouse_event = self._transform_event(event)

            # Add to batch
            self.batch.append(clickhouse_event)

            logger.debug(
                "feedback_event_received",
                feedback_id=event.get("id"),
                batch_size=len(self.batch)
            )

            # Flush if batch is full
            if len(self.batch) >= self.batch_size:
                await self._flush_batch()

        except Exception as e:
            logger.error(
                "feedback_event_processing_failed",
                error=str(e),
                data=data[:200]
            )

    def _transform_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform feedback event to ClickHouse schema.

        Args:
            event: Feedback event from Redis

        Returns:
            Transformed event for ClickHouse
        """
        return {
            "id": event["id"],
            "tenant_id": event["tenant_id"],
            "user_id": event["user_id"],
            "feedback_type": event["feedback_type"],
            "execution_id": event.get("execution_id") or 0,
            "agent_id": event.get("agent_id") or 0,
            "chat_session_id": event.get("chat_session_id") or "",
            "rating": event["rating"],
            "sentiment": event.get("sentiment") or "neutral",
            "sentiment_score": event.get("sentiment_score") or 0.0,
            "tags": event.get("tags", []),
            "created_at": event["created_at"],
            "date": event["date"]
        }

    async def _flush_batch(self):
        """Flush current batch to ClickHouse."""
        if not self.batch:
            return

        try:
            # Insert batch into ClickHouse
            rows_inserted = await asyncio.to_thread(
                self.clickhouse.insert,
                "feedback_events",
                self.batch
            )

            logger.info(
                "feedback_batch_flushed",
                rows_inserted=rows_inserted,
                batch_size=len(self.batch)
            )

            # Clear batch
            self.batch = []

        except Exception as e:
            logger.error(
                "feedback_batch_flush_failed",
                error=str(e),
                batch_size=len(self.batch)
            )
            # Don't clear batch on error - will retry on next flush

    async def _periodic_flush(self):
        """Periodically flush batch even if not full."""
        while self.running:
            await asyncio.sleep(self.batch_timeout)
            if self.batch:
                await self._flush_batch()


# Singleton worker instance
_ingestion_worker: FeedbackIngestionWorker = None


async def start_ingestion_worker(redis_client, clickhouse_client):
    """
    Start the feedback ingestion worker.

    Args:
        redis_client: Redis client instance
        clickhouse_client: ClickHouse client instance
    """
    global _ingestion_worker

    if _ingestion_worker and _ingestion_worker.running:
        logger.warning("feedback_ingestion_worker_already_running")
        return

    _ingestion_worker = FeedbackIngestionWorker(redis_client, clickhouse_client)
    await _ingestion_worker.start()


async def stop_ingestion_worker():
    """Stop the feedback ingestion worker."""
    global _ingestion_worker

    if _ingestion_worker:
        await _ingestion_worker.stop()
        _ingestion_worker = None
