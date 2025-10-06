"""LLM Provider service for managing LLM provider configurations."""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Tuple, Optional
from ..models.llm_provider import LLMProvider, LLMProviderType
from ..schemas.llm_providers import LLMProviderCreate, LLMProviderUpdate
from .encryption_service import get_encryption_service
from .versioning_service import VersioningService


class LLMProviderService:
    """Service for managing LLM providers."""

    def __init__(self, db: Session):
        self.db = db
        self.encryption = get_encryption_service()
        self.versioning = VersioningService(db)

    async def create_provider(
        self,
        tenant_id: int,
        provider_data: LLMProviderCreate
    ) -> dict:
        """Create a new LLM provider."""
        # If this is set as default, unset other defaults
        if provider_data.is_default:
            self.db.query(LLMProvider).filter(
                and_(
                    LLMProvider.tenant_id == tenant_id,
                    LLMProvider.is_default == True
                )
            ).update({"is_default": False})

        # Encrypt API key before storing
        encrypted_api_key = self.encryption.encrypt_if_not_empty(provider_data.api_key)

        # Create provider
        provider = LLMProvider(
            tenant_id=tenant_id,
            name=provider_data.name,
            provider_type=LLMProviderType(provider_data.provider_type),
            model_name=provider_data.model_name,
            api_key=encrypted_api_key,
            api_base=provider_data.api_base,
            config=provider_data.config,
            is_default=provider_data.is_default,
        )

        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)

        # Create initial version
        config = self.versioning.config_to_dict(provider)
        self.versioning.create_provider_version(
            provider_id=provider.id,
            configuration=config,
            action="create",
            change_description="Initial provider creation"
        )

        return self._to_dict(provider)

    async def get_provider(
        self,
        provider_id: int,
        tenant_id: int
    ) -> Optional[dict]:
        """Get LLM provider by ID."""
        provider = self.db.query(LLMProvider).filter(
            and_(
                LLMProvider.id == provider_id,
                LLMProvider.tenant_id == tenant_id
            )
        ).first()

        return self._to_dict(provider) if provider else None

    async def list_providers(
        self,
        tenant_id: int,
        offset: int = 0,
        limit: int = 20,
        is_active: Optional[bool] = None
    ) -> Tuple[List[dict], int]:
        """List LLM providers for a tenant."""
        query = self.db.query(LLMProvider).filter(
            LLMProvider.tenant_id == tenant_id
        )

        if is_active is not None:
            query = query.filter(LLMProvider.is_active == is_active)

        total = query.count()
        providers = query.offset(offset).limit(limit).all()

        return [self._to_dict(p) for p in providers], total

    async def update_provider(
        self,
        provider_id: int,
        tenant_id: int,
        provider_data: LLMProviderUpdate
    ) -> Optional[dict]:
        """Update LLM provider."""
        provider = self.db.query(LLMProvider).filter(
            and_(
                LLMProvider.id == provider_id,
                LLMProvider.tenant_id == tenant_id
            )
        ).first()

        if not provider:
            return None

        # If setting as default, unset other defaults
        if provider_data.is_default and not provider.is_default:
            self.db.query(LLMProvider).filter(
                and_(
                    LLMProvider.tenant_id == tenant_id,
                    LLMProvider.is_default == True,
                    LLMProvider.id != provider_id
                )
            ).update({"is_default": False})

        # Update fields
        update_data = provider_data.model_dump(exclude_unset=True)
        if 'provider_type' in update_data:
            update_data['provider_type'] = LLMProviderType(update_data['provider_type'])

        # Encrypt API key if being updated
        if 'api_key' in update_data and update_data['api_key']:
            update_data['api_key'] = self.encryption.encrypt(update_data['api_key'])

        for key, value in update_data.items():
            setattr(provider, key, value)

        self.db.commit()
        self.db.refresh(provider)

        # Create version for update
        config = self.versioning.config_to_dict(provider)
        self.versioning.create_provider_version(
            provider_id=provider.id,
            configuration=config,
            action="update",
            change_description="Provider configuration updated"
        )

        return self._to_dict(provider)

    async def delete_provider(
        self,
        provider_id: int,
        tenant_id: int
    ) -> bool:
        """Delete LLM provider."""
        provider = self.db.query(LLMProvider).filter(
            and_(
                LLMProvider.id == provider_id,
                LLMProvider.tenant_id == tenant_id
            )
        ).first()

        if not provider:
            return False

        self.db.delete(provider)
        self.db.commit()

        return True

    def _to_dict(self, provider: LLMProvider, include_api_key: bool = False) -> dict:
        """
        Convert LLM provider model to dictionary.

        Args:
            provider: LLM provider model
            include_api_key: If True, return masked API key. Never return decrypted key in API responses.
        """
        result = {
            "id": provider.id,
            "name": provider.name,
            "provider_type": provider.provider_type.value,
            "model_name": provider.model_name,
            "api_base": provider.api_base,
            "config": provider.config,
            "is_active": provider.is_active,
            "is_default": provider.is_default,
            "created_at": provider.created_at.isoformat() if provider.created_at else None,
            "updated_at": provider.updated_at.isoformat() if provider.updated_at else None,
        }

        # Never expose encrypted keys in API responses
        # Show masked version for confirmation
        if include_api_key and provider.api_key:
            result["api_key_set"] = True
        else:
            result["api_key_set"] = bool(provider.api_key)

        return result

    def get_decrypted_api_key(self, provider: LLMProvider) -> Optional[str]:
        """
        Get decrypted API key for internal use (e.g., making LLM calls).

        Args:
            provider: LLM provider model

        Returns:
            Decrypted API key or None
        """
        if provider.api_key:
            return self.encryption.decrypt(provider.api_key)
        return None
