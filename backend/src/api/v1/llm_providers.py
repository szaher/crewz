"""
LLM Provider API endpoints
Manage LLM provider configurations (OpenAI, Anthropic, Ollama, vLLM)
"""

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ...db.postgres import get_db
from ...schemas.llm_providers import (
    LLMProviderCreate,
    LLMProviderUpdate,
    LLMProviderResponse,
    LLMProviderListResponse
)
from ...services.llm_provider_service import LLMProviderService
from ...api.middleware.auth import require_auth

router = APIRouter(prefix="/llm-providers", tags=["llm-providers"])


@router.get("", response_model=LLMProviderListResponse)
async def list_llm_providers(
    page: int = 1,
    page_size: int = 20,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """List all LLM providers for current tenant"""
    service = LLMProviderService(db)

    offset = (page - 1) * page_size
    providers, total = await service.list_providers(
        tenant_id=current_user["tenant_id"],
        offset=offset,
        limit=page_size,
        is_active=is_active
    )

    return LLMProviderListResponse(
        providers=providers,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=LLMProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_provider(
    provider_data: LLMProviderCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Create a new LLM provider configuration"""
    # Only admins can create LLM providers
    if current_user["role"] not in ["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create LLM providers"
        )

    service = LLMProviderService(db)
    provider = await service.create_provider(
        tenant_id=current_user["tenant_id"],
        provider_data=provider_data
    )

    return LLMProviderResponse(provider=provider)


@router.get("/{provider_id}", response_model=LLMProviderResponse)
async def get_llm_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Get LLM provider by ID"""
    service = LLMProviderService(db)
    provider = await service.get_provider(
        provider_id=provider_id,
        tenant_id=current_user["tenant_id"]
    )

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM provider not found"
        )

    return LLMProviderResponse(provider=provider)


@router.put("/{provider_id}", response_model=LLMProviderResponse)
async def update_llm_provider(
    provider_id: int,
    provider_data: LLMProviderUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Update LLM provider configuration"""
    # Only admins can update LLM providers
    if current_user["role"] not in ["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update LLM providers"
        )

    service = LLMProviderService(db)
    provider = await service.update_provider(
        provider_id=provider_id,
        tenant_id=current_user["tenant_id"],
        provider_data=provider_data
    )

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM provider not found"
        )

    return LLMProviderResponse(provider=provider)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Delete LLM provider"""
    # Only admins can delete LLM providers
    if current_user["role"] not in ["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete LLM providers"
        )

    service = LLMProviderService(db)
    success = await service.delete_provider(
        provider_id=provider_id,
        tenant_id=current_user["tenant_id"]
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM provider not found"
        )

    return None
