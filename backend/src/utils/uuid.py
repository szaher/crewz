"""UUID utilities for the CrewAI platform.

This module provides utilities for generating and working with UUIDv7,
a time-ordered UUID format that provides better database performance
compared to UUIDv4 while maintaining uniqueness and security.
"""

from typing import Union
from uuid import UUID
import uuid6


def generate_uuid_v7() -> UUID:
    """Generate a UUIDv7 (time-ordered UUID).
    
    UUIDv7 provides:
    - Time-based ordering (sortable by creation time)
    - Better PostgreSQL B-tree index performance
    - Non-guessable (includes random component)
    - Compatible with standard UUID type
    
    Returns:
        UUID: A newly generated UUIDv7 instance
        
    Example:
        >>> id = generate_uuid_v7()
        >>> print(id)
        018e1234-5678-7abc-def0-123456789abc
    """
    return uuid6.uuid7()


def uuid_to_string(uuid_obj: UUID) -> str:
    """Convert UUID object to string representation.
    
    Args:
        uuid_obj: UUID object to convert
        
    Returns:
        str: String representation in RFC 4122 format (36 characters with hyphens)
        
    Example:
        >>> uuid_obj = generate_uuid_v7()
        >>> uuid_to_string(uuid_obj)
        '018e1234-5678-7abc-def0-123456789abc'
    """
    return str(uuid_obj)


def string_to_uuid(uuid_str: str) -> UUID:
    """Convert string to UUID object.
    
    Args:
        uuid_str: String representation of UUID (36 characters with hyphens)
        
    Returns:
        UUID: Parsed UUID object
        
    Raises:
        ValueError: If the string is not a valid UUID format
        
    Example:
        >>> uuid_obj = string_to_uuid('018e1234-5678-7abc-def0-123456789abc')
        >>> print(type(uuid_obj))
        <class 'uuid.UUID'>
    """
    return UUID(uuid_str)


def is_valid_uuid(value: Union[str, UUID]) -> bool:
    """Check if a value is a valid UUID.
    
    Args:
        value: String or UUID object to validate
        
    Returns:
        bool: True if valid UUID, False otherwise
        
    Example:
        >>> is_valid_uuid('018e1234-5678-7abc-def0-123456789abc')
        True
        >>> is_valid_uuid('invalid-uuid')
        False
        >>> is_valid_uuid(generate_uuid_v7())
        True
    """
    if isinstance(value, UUID):
        return True
    
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False
