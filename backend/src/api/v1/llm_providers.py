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
from ...services.llm_service import LLMService
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

    # Prevent deletion if provider is referenced by agents or crews
    from ...models.agent import Agent
    from ...models.crew import Crew

    agent_refs = db.query(Agent).filter(Agent.llm_provider_id == provider_id).count()
    crew_refs = db.query(Crew).filter(Crew.manager_llm_provider_id == provider_id).count()

    if agent_refs > 0 or crew_refs > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Provider is in use by {agent_refs} agent(s) and {crew_refs} crew(s). Reassign or delete dependents first."
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


@router.get("/default", response_model=LLMProviderResponse)
async def get_default_provider(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Get the tenant's default LLM provider."""
    from ...models.llm_provider import LLMProvider

    provider = (
        db.query(LLMProvider)
        .filter(
            LLMProvider.tenant_id == current_user["tenant_id"],
            LLMProvider.is_default == True,
            LLMProvider.is_active == True,
        )
        .first()
    )

    if not provider:
        raise HTTPException(status_code=404, detail="Default provider not set")

    service = LLMProviderService(db)
    return LLMProviderResponse(provider=service._to_dict(provider))


@router.post("/{provider_id}/set-default", response_model=LLMProviderResponse)
async def set_default_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Set a specific LLM provider as the tenant default (admin-only)."""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can set a default provider",
        )

    service = LLMProviderService(db)
    updated = await service.set_default_provider(
        tenant_id=current_user["tenant_id"], provider_id=provider_id
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Provider not found")

    return LLMProviderResponse(provider=updated)


@router.post("/{provider_id}/test", response_model=dict)
async def test_llm_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Test connectivity and credentials for a provider by performing a trivial completion."""
    # Ensure provider belongs to tenant
    service = LLMProviderService(db)
    provider = await service.get_provider(provider_id=provider_id, tenant_id=current_user["tenant_id"])
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Fast pre-checks
    if not provider.get("api_key_set") and provider.get("provider_type") in ("openai", "anthropic", "custom"):
        return {"success": False, "message": "API key is not set for this provider"}

    # Minimal test prompt
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'ok'"},
    ]

    llm = LLMService(db)
    try:
        result = await llm.chat_completion(provider_id=provider_id, messages=messages, max_tokens=5, temperature=0)
        content = result.choices[0].message.content if result and result.choices else ""
        return {"success": True, "message": content[:200]}
    except HTTPException as he:
        # Return structured failure instead of raising 500s to client
        detail = he.detail if isinstance(he.detail, str) else str(he.detail)
        return {"success": False, "message": detail, "status": he.status_code}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/{provider_id}/usage", response_model=dict)
async def get_provider_usage(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Return counts of dependent resources using this provider (agents, crews)."""
    from ...models.agent import Agent
    from ...models.crew import Crew

    # Ensure provider exists and belongs to tenant
    service = LLMProviderService(db)
    provider = await service.get_provider(provider_id=provider_id, tenant_id=current_user["tenant_id"])
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    agent_count = db.query(Agent).filter(Agent.llm_provider_id == provider_id).count()
    crew_count = db.query(Crew).filter(Crew.manager_llm_provider_id == provider_id).count()

    return {
        "provider_id": provider_id,
        "agent_count": agent_count,
        "crew_count": crew_count,
    }


@router.post("/{provider_id}/reassign", response_model=dict)
async def reassign_dependents(
    provider_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Bulk reassign dependents (agents, crews) from one provider to another.

    Body:
      - target_provider_id: int (required)
      - scope: 'agents' | 'crews' | 'all' (default: 'all')

    Returns counts updated.
    """
    # Admin-only operation
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Only admins can reassign dependents")

    target_provider_id = payload.get("target_provider_id")
    scope = (payload.get("scope") or "all").lower()
    if not target_provider_id:
        raise HTTPException(status_code=400, detail="target_provider_id is required")
    if target_provider_id == provider_id:
        raise HTTPException(status_code=400, detail="Target provider must be different from source provider")

    # Validate providers belong to tenant
    from ...models.llm_provider import LLMProvider
    source = db.query(LLMProvider).filter(
        LLMProvider.id == provider_id,
        LLMProvider.tenant_id == current_user["tenant_id"],
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source provider not found")

    target = db.query(LLMProvider).filter(
        LLMProvider.id == target_provider_id,
        LLMProvider.tenant_id == current_user["tenant_id"],
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target provider not found")
    if not target.is_active:
        raise HTTPException(status_code=400, detail="Target provider is inactive")

    from ...models.agent import Agent
    from ...models.crew import Crew

    agents_updated = 0
    crews_updated = 0

    try:
        if scope in ("agents", "all"):
            agents_updated = (
                db.query(Agent)
                .filter(Agent.llm_provider_id == provider_id)
                .update({Agent.llm_provider_id: target_provider_id}, synchronize_session=False)
            )
        if scope in ("crews", "all"):
            crews_updated = (
                db.query(Crew)
                .filter(Crew.manager_llm_provider_id == provider_id)
                .update({Crew.manager_llm_provider_id: target_provider_id}, synchronize_session=False)
            )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Reassign failed: {str(e)}")

    return {
        "source_provider_id": provider_id,
        "target_provider_id": target_provider_id,
        "agents_reassigned": agents_updated,
        "crews_reassigned": crews_updated,
        "scope": scope,
    }


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
