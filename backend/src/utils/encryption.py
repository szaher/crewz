"""Encryption utilities for sensitive data (API keys, credentials)."""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


# Get encryption key from environment (32 bytes for AES-256)
ENCRYPTION_KEY_B64 = os.getenv("ENCRYPTION_KEY")

if ENCRYPTION_KEY_B64:
    ENCRYPTION_KEY = base64.b64decode(ENCRYPTION_KEY_B64)
else:
    # For development only - generate a random key
    # In production, this must be set via environment variable
    ENCRYPTION_KEY = AESGCM.generate_key(bit_length=256)


def encrypt_api_key(plaintext: str) -> str:
    """
    Encrypt an API key or credential using AES-256-GCM.

    Args:
        plaintext: Plain text credential to encrypt

    Returns:
        Base64-encoded encrypted data (nonce + ciphertext)
    """
    if not plaintext:
        return ""

    aesgcm = AESGCM(ENCRYPTION_KEY)
    nonce = os.urandom(12)  # 96-bit nonce for GCM

    plaintext_bytes = plaintext.encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)

    # Combine nonce + ciphertext and encode as base64
    encrypted_data = nonce + ciphertext
    return base64.b64encode(encrypted_data).decode("utf-8")


def decrypt_api_key(encrypted_b64: str) -> str:
    """
    Decrypt an encrypted API key or credential.

    Args:
        encrypted_b64: Base64-encoded encrypted data

    Returns:
        Decrypted plain text credential

    Raises:
        Exception: If decryption fails
    """
    if not encrypted_b64:
        return ""

    try:
        encrypted_data = base64.b64decode(encrypted_b64)

        # Extract nonce and ciphertext
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        aesgcm = AESGCM(ENCRYPTION_KEY)
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)

        return plaintext_bytes.decode("utf-8")
    except Exception as e:
        raise Exception(f"Decryption failed: {str(e)}")


def generate_encryption_key() -> str:
    """
    Generate a new AES-256 encryption key.

    Returns:
        Base64-encoded 256-bit key for use in ENCRYPTION_KEY env var
    """
    key = AESGCM.generate_key(bit_length=256)
    return base64.b64encode(key).decode("utf-8")
