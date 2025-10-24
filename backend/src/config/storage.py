"""
Storage configuration for S3/MinIO artifact storage.

Supports both AWS S3 and local filesystem fallback.
Environment variables control storage backend selection.
"""

import os
from typing import Literal

# Storage backend type: 's3' or 'local'
STORAGE_TYPE: Literal["s3", "local"] = os.getenv("STORAGE_TYPE", "local")

# S3/MinIO Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "crewai-artifacts")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")  # For MinIO/custom S3 endpoints

# Local filesystem configuration (fallback)
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "/var/crewai/artifacts")

# Pre-signed URL expiration (in seconds)
PRESIGNED_URL_EXPIRATION = int(os.getenv("PRESIGNED_URL_EXPIRATION", "3600"))  # 1 hour default

# Multipart upload configuration
MULTIPART_THRESHOLD_MB = int(os.getenv("MULTIPART_THRESHOLD_MB", "5"))  # Files > 5MB use multipart
MULTIPART_CHUNKSIZE_MB = int(os.getenv("MULTIPART_CHUNKSIZE_MB", "5"))


def get_storage_config() -> dict:
    """
    Get storage configuration based on STORAGE_TYPE.

    Returns:
        dict: Storage configuration with appropriate settings
    """
    if STORAGE_TYPE == "s3":
        config = {
            "type": "s3",
            "access_key_id": AWS_ACCESS_KEY_ID,
            "secret_access_key": AWS_SECRET_ACCESS_KEY,
            "region": AWS_REGION,
            "bucket_name": S3_BUCKET_NAME,
            "endpoint_url": S3_ENDPOINT_URL,
            "presigned_url_expiration": PRESIGNED_URL_EXPIRATION,
            "multipart_threshold": MULTIPART_THRESHOLD_MB * 1024 * 1024,
            "multipart_chunksize": MULTIPART_CHUNKSIZE_MB * 1024 * 1024,
        }

        # Validate required S3 credentials
        if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
            raise ValueError(
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set when STORAGE_TYPE=s3"
            )

        return config

    elif STORAGE_TYPE == "local":
        return {
            "type": "local",
            "storage_path": LOCAL_STORAGE_PATH,
        }

    else:
        raise ValueError(f"Invalid STORAGE_TYPE: {STORAGE_TYPE}. Must be 's3' or 'local'")


def validate_storage_config() -> bool:
    """
    Validate storage configuration at startup.

    Returns:
        bool: True if configuration is valid

    Raises:
        ValueError: If configuration is invalid
    """
    try:
        config = get_storage_config()

        if config["type"] == "local":
            # Ensure local storage directory exists
            os.makedirs(config["storage_path"], exist_ok=True)

        return True

    except Exception as e:
        raise ValueError(f"Storage configuration validation failed: {e}")
