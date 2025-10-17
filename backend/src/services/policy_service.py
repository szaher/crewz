"""Policy management service for ABAC."""

from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from fastapi import HTTPException, status

from ..models import Policy
from ..models.policy import PolicyScope, Effect
from ..utils.uuid import generate_uuid_v7
from .authorization_service import AuthorizationService


class PolicyService:
    """Service for managing attribute-based access control policies."""

    def __init__(self, db: Session):
        """Initialize policy service."""
        self.db = db

    def list_policies(
        self,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        scope: Optional[str] = None,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        List policies with filtering.

        Args:
            tenant_id: Tenant ID
            user_id: Optional user ID (for user-level policies)
            scope: Filter by scope ("tenant", "user", or None for all)
            active_only: Only return active policies
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            {policies: [...], total: int}
        """
        query = self.db.query(Policy).filter(Policy.tenant_id == tenant_id)

        # Filter by scope
        if scope == "tenant":
            query = query.filter(
                Policy.scope == PolicyScope.TENANT,
                Policy.scope_id.is_(None)
            )
        elif scope == "user":
            if user_id:
                # User-level policies for specific user
                query = query.filter(
                    Policy.scope == PolicyScope.USER,
                    Policy.scope_id == user_id
                )
            else:
                # All user-level policies
                query = query.filter(Policy.scope == PolicyScope.USER)

        # Filter by active status
        if active_only:
            query = query.filter(Policy.is_active == True)

        # Order by priority descending (higher priority first)
        query = query.order_by(Policy.priority.desc(), Policy.name)

        total = query.count()

        # Pagination
        offset = (page - 1) * page_size
        policies = query.offset(offset).limit(page_size).all()

        return {
            "policies": policies,
            "total": total,
        }

    def create_policy(
        self,
        tenant_id: UUID,
        scope: str,
        name: str,
        resource_pattern: str,
        action_pattern: str,
        effect: str,
        scope_id: Optional[UUID] = None,
        description: Optional[str] = None,
        conditions: Optional[Dict] = None,
        priority: int = 100,
    ) -> Policy:
        """
        Create policy.

        Args:
            tenant_id: Tenant ID
            scope: Policy scope ("tenant" or "user")
            name: Policy name
            resource_pattern: Resource pattern (e.g., "crew:*", "flow:018e*")
            action_pattern: Action pattern (e.g., "read", "*")
            effect: Effect ("allow" or "deny")
            scope_id: Required for user-level policies
            description: Optional description
            conditions: Optional conditions dict
            priority: Policy priority (0-1000)

        Returns:
            Created policy

        Raises:
            HTTPException: If validation fails
        """
        # Validate scope_id requirement
        if scope == "user" and scope_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope_id is required for user-level policies"
            )

        if scope == "tenant" and scope_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope_id must be null for tenant-level policies"
            )

        # Create policy
        policy = Policy(
            id=generate_uuid_v7(),
            tenant_id=tenant_id,
            scope=PolicyScope(scope),
            scope_id=scope_id,
            name=name,
            description=description,
            resource_pattern=resource_pattern,
            action_pattern=action_pattern,
            effect=Effect(effect),
            conditions=conditions,
            priority=priority,
            is_active=True,
        )

        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)

        return policy

    def update_policy(
        self,
        policy_id: UUID,
        tenant_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        resource_pattern: Optional[str] = None,
        action_pattern: Optional[str] = None,
        effect: Optional[str] = None,
        conditions: Optional[Dict] = None,
        priority: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> Policy:
        """
        Update policy.

        Args:
            policy_id: Policy ID
            tenant_id: Tenant ID (for access control)
            name: Updated name
            description: Updated description
            resource_pattern: Updated resource pattern
            action_pattern: Updated action pattern
            effect: Updated effect
            conditions: Updated conditions
            priority: Updated priority
            is_active: Updated active status

        Returns:
            Updated policy

        Raises:
            HTTPException: If policy not found or access denied
        """
        # Get policy
        policy = self.db.query(Policy).filter(
            Policy.id == policy_id,
            Policy.tenant_id == tenant_id,
        ).first()

        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )

        # Update fields
        if name is not None:
            policy.name = name
        if description is not None:
            policy.description = description
        if resource_pattern is not None:
            policy.resource_pattern = resource_pattern
        if action_pattern is not None:
            policy.action_pattern = action_pattern
        if effect is not None:
            policy.effect = Effect(effect)
        if conditions is not None:
            policy.conditions = conditions
        if priority is not None:
            policy.priority = priority
        if is_active is not None:
            policy.is_active = is_active

        self.db.commit()
        self.db.refresh(policy)

        # Invalidate cache for affected users
        if policy.scope == PolicyScope.USER and policy.scope_id:
            authz_service = AuthorizationService(self.db)
            authz_service.invalidate_cache(policy.scope_id, "*")

        return policy

    def delete_policy(
        self,
        policy_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """
        Delete policy.

        Args:
            policy_id: Policy ID
            tenant_id: Tenant ID (for access control)

        Raises:
            HTTPException: If policy not found or access denied
        """
        # Get policy
        policy = self.db.query(Policy).filter(
            Policy.id == policy_id,
            Policy.tenant_id == tenant_id,
        ).first()

        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )

        # Store scope info for cache invalidation
        scope_id = policy.scope_id
        scope = policy.scope

        # Delete policy
        self.db.delete(policy)
        self.db.commit()

        # Invalidate cache for affected users
        if scope == PolicyScope.USER and scope_id:
            authz_service = AuthorizationService(self.db)
            authz_service.invalidate_cache(scope_id, "*")
