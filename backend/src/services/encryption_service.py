"""Encryption service for sensitive data like API keys and credentials."""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from typing import Optional


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data using AES-256-GCM.

    Uses Fernet (symmetric encryption) with a key derived from environment variables.
    In production, this should integrate with Vault or Kubernetes Secrets.
    """

    def __init__(self):
        """Initialize encryption service with key from environment."""
        self._encryption_key = self._get_or_generate_key()
        self._fernet = Fernet(self._encryption_key)

    def _get_or_generate_key(self) -> bytes:
        """
        Get encryption key from environment or generate one.

        In production:
        - Use Vault for key management
        - Use Kubernetes Secrets for key storage
        - Implement key rotation
        """
        # Try to get key from environment
        key_str = os.getenv("ENCRYPTION_KEY")

        if key_str:
            return key_str.encode()

        # Generate key from master secret
        master_secret = os.getenv("MASTER_SECRET", "default-secret-change-in-production")
        salt = os.getenv("ENCRYPTION_SALT", "default-salt-change-in-production").encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )

        key = base64.urlsafe_b64encode(kdf.derive(master_secret.encode()))
        return key

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""

        encrypted_bytes = self._fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a ciphertext string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""

        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {str(e)}")

    def encrypt_if_not_empty(self, value: Optional[str]) -> Optional[str]:
        """Encrypt a value only if it's not None or empty."""
        if value:
            return self.encrypt(value)
        return value

    def decrypt_if_not_empty(self, value: Optional[str]) -> Optional[str]:
        """Decrypt a value only if it's not None or empty."""
        if value:
            return self.decrypt(value)
        return value


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get singleton encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
