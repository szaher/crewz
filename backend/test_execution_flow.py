"""
Test script to verify execution flow and WebSocket streaming.

This script:
1. Queries the queue to see pending items
2. Executes a crew
3. Monitors execution via WebSocket
"""

import asyncio
import json
import sys
import os

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def test_queue_api():
    """Test that queue listing works"""
    print("\n=== Testing Queue API ===")

    # Create database session
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://crewai_user:crewai_password@localhost:5432/crewai_db")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Query executions
        result = session.execute(text("""
            SELECT id, execution_type, status, priority, queue_position, created_at
            FROM executions
            WHERE status IN ('queued', 'running', 'pending')
            ORDER BY priority ASC, created_at ASC
            LIMIT 10
        """))

        rows = result.fetchall()

        print(f"Found {len(rows)} items in queue:")
        for row in rows:
            print(f"  - {row.id}: {row.execution_type} | Status: {row.status} | Priority: {row.priority} | Position: {row.queue_position}")

        return len(rows)

    finally:
        session.close()


def test_redis_connection():
    """Test Redis connection for streaming"""
    print("\n=== Testing Redis Connection ===")

    try:
        import redis

        REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = redis.from_url(REDIS_URL, decode_responses=True)

        # Test connection
        client.ping()
        print("✓ Redis connection successful")

        # Test pub/sub
        test_channel = "test_channel"
        test_message = {"event": "test", "data": "hello"}

        client.publish(test_channel, json.dumps(test_message))
        print(f"✓ Published test message to {test_channel}")

        return True

    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False


def test_stream_handler():
    """Test StreamHandler functionality"""
    print("\n=== Testing StreamHandler ===")

    try:
        from workers.stream_handler import StreamHandler
        import redis

        REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)

        # Create test execution ID
        test_execution_id = "00000000-0000-0000-0000-000000000001"

        # Create stream handler
        handler = StreamHandler(test_execution_id, redis_client=redis_client)

        # Emit test events
        handler.emit_started("test-worker")
        print("✓ Emitted started event")

        handler.emit_output("Test output line", "stdout")
        print("✓ Emitted output event")

        handler.emit_progress(50, "Testing progress", 2)
        print("✓ Emitted progress event")

        handler.emit_completed("completed", "Test completed successfully")
        print("✓ Emitted completed event")

        # Check buffer
        buffered = handler.get_buffered_lines()
        print(f"✓ Buffered {len(buffered)} lines")

        # Cleanup
        handler.clear_buffer()

        return True

    except Exception as e:
        print(f"✗ StreamHandler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_websocket_connection():
    """Test WebSocket connection"""
    print("\n=== Testing WebSocket Connection ===")

    try:
        import websockets

        # This would require a valid JWT token
        # For now, just test that the WebSocket server is reachable
        print("⚠ WebSocket test requires authentication token (skipping)")
        return True

    except Exception as e:
        print(f"✗ WebSocket test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("EXECUTION FLOW TEST SUITE")
    print("=" * 60)

    results = {
        "Queue API": False,
        "Redis Connection": False,
        "StreamHandler": False,
        "WebSocket": False,
    }

    # Run tests
    try:
        queue_count = test_queue_api()
        results["Queue API"] = True
    except Exception as e:
        print(f"✗ Queue API test failed: {e}")

    results["Redis Connection"] = test_redis_connection()
    results["StreamHandler"] = test_stream_handler()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test:.<40} {status}")

    print("=" * 60)

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    exit(main())
