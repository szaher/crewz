"""MongoDB connection for logs, chat, and audit trails."""

import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

# MongoDB configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://crewai:dev_password@localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "crewai_logs")

# Global MongoDB client
_mongo_client: Optional[AsyncIOMotorClient] = None


def get_mongo_client() -> AsyncIOMotorClient:
    """Get or create MongoDB client."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(MONGODB_URL)
    return _mongo_client


def get_mongo_db(db_name: Optional[str] = None) -> AsyncIOMotorDatabase:
    """
    Get MongoDB database.

    Args:
        db_name: Database name (defaults to MONGODB_DB_NAME)

    Returns:
        AsyncIOMotorDatabase instance
    """
    client = get_mongo_client()
    return client[db_name or MONGODB_DB_NAME]


def get_mongo_collection(
    collection_name: str, db_name: Optional[str] = None
) -> AsyncIOMotorCollection:
    """
    Get MongoDB collection.

    Args:
        collection_name: Collection name
        db_name: Database name (defaults to MONGODB_DB_NAME)

    Returns:
        AsyncIOMotorCollection instance
    """
    db = get_mongo_db(db_name)
    return db[collection_name]


async def close_mongo_connection() -> None:
    """Close MongoDB connection."""
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None


# MongoDB document schemas (for reference, not enforced)

# ExecutionNode collection
# {
#   "_id": ObjectId,
#   "execution_id": int,
#   "node_id": str,
#   "node_type": str,
#   "status": str,
#   "started_at": datetime,
#   "completed_at": datetime,
#   "input": dict,
#   "output": dict,
#   "error": str,
#   "logs": [str],
# }

# ChatMessage collection
# {
#   "_id": ObjectId,
#   "session_id": int,
#   "role": str,  # "user" | "assistant" | "system"
#   "content": str,
#   "created_at": datetime,
#   "metadata": dict,
# }

# AuditLog collection
# {
#   "_id": ObjectId,
#   "tenant_id": int,
#   "user_id": int,
#   "action": str,
#   "resource_type": str,
#   "resource_id": int,
#   "changes": dict,
#   "ip_address": str,
#   "user_agent": str,
#   "created_at": datetime,
# }
