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
from ...services.versioning_service import VersioningService
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


@router.get("/{provider_id}/versions", response_model=dict)
async def get_provider_versions(
    provider_id: int,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Get version history for an LLM provider.

    Returns:
    - versions: List of version entries with configuration snapshots and diffs
    - total: Total number of versions
    - page: Current page number
    - page_size: Number of items per page
    """
    if page_size > 50:
        page_size = 50

    versioning_service = VersioningService(db)
    offset = (page - 1) * page_size

    versions, total = versioning_service.get_provider_versions(
        provider_id=provider_id,
        limit=page_size,
        offset=offset
    )

    return {
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "action": v.action.value,
                "changed_by_user_id": v.changed_by_user_id,
                "configuration": v.configuration,
                "diff_from_previous": v.diff_from_previous,
                "change_description": v.change_description,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{provider_id}/rollback/{version_number}", response_model=LLMProviderResponse)
async def rollback_provider(
    provider_id: int,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Rollback an LLM provider to a specific version.

    - **version_number**: Version number to rollback to

    Only admins can rollback providers.
    """
    # Only admins can rollback providers
    if current_user["role"] not in ["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can rollback LLM providers"
        )

    versioning_service = VersioningService(db)

    try:
        provider = versioning_service.rollback_provider(
            provider_id=provider_id,
            version_number=version_number,
            changed_by_user_id=current_user.get("user_id")
        )

        service = LLMProviderService(db)
        return LLMProviderResponse(provider=service._to_dict(provider))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
