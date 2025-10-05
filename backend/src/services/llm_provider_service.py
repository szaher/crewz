"""LLM Provider service for managing LLM provider configurations."""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Tuple, Optional
from ..models.llm_provider import LLMProvider, LLMProviderType
from ..schemas.llm_providers import LLMProviderCreate, LLMProviderUpdate


class LLMProviderService:
    """Service for managing LLM providers."""

    def __init__(self, db: Session):
        self.db = db

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

        # Create provider
        provider = LLMProvider(
            tenant_id=tenant_id,
            name=provider_data.name,
            provider_type=LLMProviderType(provider_data.provider_type),
            model_name=provider_data.model_name,
            api_key=provider_data.api_key,
            api_base=provider_data.api_base,
            config=provider_data.config,
            is_default=provider_data.is_default,
        )

        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)

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

        for key, value in update_data.items():
            setattr(provider, key, value)

        self.db.commit()
        self.db.refresh(provider)

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

    def _to_dict(self, provider: LLMProvider) -> dict:
        """Convert LLM provider model to dictionary."""
        return {
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
