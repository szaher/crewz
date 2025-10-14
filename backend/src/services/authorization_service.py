"""Authorization service for RBAC+ABAC permission checks."""

import time
import json
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import redis

from ..models import Permission, Role, Policy, AuthorizationAuditLog, user_roles
from ..models.permission import SubjectType, Action as ActionEnum, Effect
from ..models.policy import PolicyScope
from ..models.authorization_audit_log import AuditDecision
from ..utils.uuid import generate_uuid_v7
from ..db.redis import get_redis_client


class AuthorizationService:
    """
    Service for checking permissions and managing authorization.

    Implements hybrid RBAC (Role-Based) + ABAC (Attribute-Based) access control.

    Evaluation order (first match wins):
    1. User-level explicit DENY permissions (highest priority)
    2. User-level explicit ALLOW permissions
    3. Role-level DENY permissions
    4. Role-level ALLOW permissions
    5. Tenant-level DENY policies
    6. Tenant-level ALLOW policies
    7. User-level DENY policies
    8. User-level ALLOW policies
    9. Default DENY (no permission found)

    Caching:
    - Permission checks are cached in Redis for 5 minutes
    - Cache key format: authz:{user_id}:{resource_type}:{resource_id}:{action}
    - Target: <10ms for cache hits
    """

    def __init__(self, db: Session, redis_client: Optional[redis.Redis] = None):
        """
        Initialize authorization service.

        Args:
            db: SQLAlchemy database session
            redis_client: Redis client for caching (optional, will use singleton if not provided)
        """
        self.db = db
        self.redis = redis_client or get_redis_client()
        self.cache_ttl = 300  # 5 minutes

    def check_permission(
        self,
        user_id: UUID,
        tenant_id: UUID,
        resource_type: str,
        resource_id: Optional[UUID],
        action: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check if user has permission to perform action on resource.

        Args:
            user_id: User performing the action
            tenant_id: Tenant context
            resource_type: Type of resource (e.g., 'crew', 'flow')
            resource_id: Specific resource ID (None = any resource of type)
            action: Action to perform ('read', 'write', 'execute', 'delete', '*')
            ip_address: Request IP for audit log
            user_agent: Request user agent for audit log

        Returns:
            {
                'decision': 'allow' | 'deny',
                'reason': 'user:allow' | 'role:tenant-admin' | 'policy:deny-all' | 'default:deny',
                'latency_ms': int
            }
        """
        start_time = time.time()

        # 0. Check if user has super-admin role (bypass all permission checks)
        if self._is_super_admin(user_id):
            latency_ms = int((time.time() - start_time) * 1000)
            result = {
                'decision': 'allow',
                'reason': 'role:super-admin',
                'latency_ms': latency_ms
            }
            # Audit log
            self._audit_log(
                user_id, tenant_id, resource_type, resource_id, action,
                'allow', 'role:super-admin', latency_ms, ip_address, user_agent
            )
            return result

        # Check cache first
        cache_key = self._get_cache_key(user_id, resource_type, resource_id, action)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            # Update latency for cache hit
            cached_result['latency_ms'] = int((time.time() - start_time) * 1000)
            # Still audit cache hits
            self._audit_log(
                user_id, tenant_id, resource_type, resource_id, action,
                cached_result['decision'], f"cache:{cached_result['reason']}",
                cached_result['latency_ms'], ip_address, user_agent
            )
            return cached_result

        # 1. Check user-level explicit permissions (highest priority)
        user_perm = self._check_user_permissions(user_id, tenant_id, resource_type, resource_id, action)
        if user_perm:
            decision, reason = user_perm
            latency_ms = int((time.time() - start_time) * 1000)
            result = {'decision': decision, 'reason': reason, 'latency_ms': latency_ms}
            self._set_cache(cache_key, result)
            self._audit_log(
                user_id, tenant_id, resource_type, resource_id, action,
                decision, reason, latency_ms, ip_address, user_agent
            )
            return result

        # 2. Check role-level permissions
        role_perm = self._check_role_permissions(user_id, tenant_id, resource_type, resource_id, action)
        if role_perm:
            decision, reason = role_perm
            latency_ms = int((time.time() - start_time) * 1000)
            result = {'decision': decision, 'reason': reason, 'latency_ms': latency_ms}
            self._set_cache(cache_key, result)
            self._audit_log(
                user_id, tenant_id, resource_type, resource_id, action,
                decision, reason, latency_ms, ip_address, user_agent
            )
            return result

        # 3. Check tenant-level policies
        tenant_policy = self._check_tenant_policies(tenant_id, resource_type, resource_id, action)
        if tenant_policy:
            decision, reason = tenant_policy
            latency_ms = int((time.time() - start_time) * 1000)
            result = {'decision': decision, 'reason': reason, 'latency_ms': latency_ms}
            self._set_cache(cache_key, result)
            self._audit_log(
                user_id, tenant_id, resource_type, resource_id, action,
                decision, reason, latency_ms, ip_address, user_agent
            )
            return result

        # 4. Check user-level policies
        user_policy = self._check_user_policies(user_id, tenant_id, resource_type, resource_id, action)
        if user_policy:
            decision, reason = user_policy
            latency_ms = int((time.time() - start_time) * 1000)
            result = {'decision': decision, 'reason': reason, 'latency_ms': latency_ms}
            self._set_cache(cache_key, result)
            self._audit_log(
                user_id, tenant_id, resource_type, resource_id, action,
                decision, reason, latency_ms, ip_address, user_agent
            )
            return result

        # 5. Default deny
        latency_ms = int((time.time() - start_time) * 1000)
        result = {'decision': 'deny', 'reason': 'default:deny', 'latency_ms': latency_ms}
        self._set_cache(cache_key, result)
        self._audit_log(
            user_id, tenant_id, resource_type, resource_id, action,
            'deny', 'default:deny', latency_ms, ip_address, user_agent
        )
        return result

    def _is_super_admin(self, user_id: UUID) -> bool:
        """
        Check if user has super-admin role.

        Super-admins bypass all permission checks and have full system access.

        Args:
            user_id: User ID to check

        Returns:
            True if user has super-admin role, False otherwise
        """
        from ..models.user import User

        # Query user and check if they have super-admin role
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Check if user has super-admin role assigned
        return any(role.slug == 'super-admin' for role in user.roles)

    def _check_user_permissions(
        self,
        user_id: UUID,
        tenant_id: UUID,
        resource_type: str,
        resource_id: Optional[UUID],
        action: str,
    ) -> Optional[tuple[str, str]]:
        """
        Check user-level permissions.

        Returns (decision, reason) tuple or None if no match.
        Priority: DENY > ALLOW
        """
        # Query user permissions for this resource
        query = self.db.query(Permission).filter(
            Permission.tenant_id == tenant_id,
            Permission.subject_type == SubjectType.USER,
            Permission.subject_id == user_id,
            Permission.resource_type == resource_type,
        )

        # Match resource_id (exact match or wildcard)
        if resource_id:
            query = query.filter(
                or_(
                    Permission.resource_id == resource_id,
                    Permission.resource_id.is_(None)
                )
            )
        else:
            query = query.filter(Permission.resource_id.is_(None))

        # Match action (exact match or wildcard)
        query = query.filter(
            or_(
                Permission.action == ActionEnum(action),
                Permission.action == ActionEnum.ALL
            )
        )

        permissions = query.all()

        # Check for DENY first (highest priority)
        for perm in permissions:
            if perm.effect == Effect.DENY:
                return ('deny', 'user:explicit-deny')

        # Then check for ALLOW
        for perm in permissions:
            if perm.effect == Effect.ALLOW:
                return ('allow', 'user:explicit-allow')

        return None

    def _get_cache_key(
        self,
        user_id: UUID,
        resource_type: str,
        resource_id: Optional[UUID],
        action: str,
    ) -> str:
        """Generate cache key for permission check."""
        resource_id_str = str(resource_id) if resource_id else "null"
        return f"authz:{user_id}:{resource_type}:{resource_id_str}:{action}"

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached permission result from Redis."""
        try:
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            # Don't fail on cache errors
            pass
        return None

    def _set_cache(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Store permission result in Redis cache."""
        try:
            self.redis.setex(cache_key, self.cache_ttl, json.dumps(result))
        except Exception:
            # Don't fail on cache errors
            pass

    def invalidate_cache(self, user_id: UUID, resource_pattern: str = "*") -> int:
        """
        Invalidate cached permissions for user matching pattern.

        Args:
            user_id: User whose permissions to invalidate
            resource_pattern: Pattern to match (e.g., "crew:*", "*:*")

        Returns:
            Number of cache keys deleted
        """
        try:
            pattern = f"authz:{user_id}:{resource_pattern}"
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
        except Exception:
            pass
        return 0

    def _check_role_permissions(
        self,
        user_id: UUID,
        tenant_id: UUID,
        resource_type: str,
        resource_id: Optional[UUID],
        action: str,
    ) -> Optional[tuple[str, str]]:
        """
        Check role-level permissions for user's roles.

        Returns (decision, reason) tuple or None if no match.
        Priority: DENY > ALLOW, higher priority roles checked first
        """
        # Get user's roles (ordered by priority descending)
        user_roles_query = self.db.query(Role).join(
            user_roles, Role.id == user_roles.c.role_id
        ).filter(
            user_roles.c.user_id == user_id
        ).order_by(Role.priority.desc())

        roles = user_roles_query.all()

        if not roles:
            return None

        role_ids = [role.id for role in roles]

        # Query role permissions
        query = self.db.query(Permission).filter(
            Permission.tenant_id == tenant_id,
            Permission.subject_type == SubjectType.ROLE,
            Permission.subject_id.in_(role_ids),
            Permission.resource_type == resource_type,
        )

        # Match resource_id (exact match or wildcard)
        if resource_id:
            query = query.filter(
                or_(
                    Permission.resource_id == resource_id,
                    Permission.resource_id.is_(None)
                )
            )
        else:
            query = query.filter(Permission.resource_id.is_(None))

        # Match action (exact match or wildcard)
        query = query.filter(
            or_(
                Permission.action == ActionEnum(action),
                Permission.action == ActionEnum.ALL
            )
        )

        permissions = query.all()

        # Build role priority map
        role_priority = {role.id: (role.priority, role.slug) for role in roles}

        # Check for DENY first (by role priority)
        deny_perms = [p for p in permissions if p.effect == Effect.DENY]
        if deny_perms:
            # Sort by role priority
            deny_perms.sort(key=lambda p: role_priority[p.subject_id][0], reverse=True)
            highest_role = role_priority[deny_perms[0].subject_id][1]
            return ('deny', f'role:{highest_role}:deny')

        # Then check for ALLOW (by role priority)
        allow_perms = [p for p in permissions if p.effect == Effect.ALLOW]
        if allow_perms:
            # Sort by role priority
            allow_perms.sort(key=lambda p: role_priority[p.subject_id][0], reverse=True)
            highest_role = role_priority[allow_perms[0].subject_id][1]
            return ('allow', f'role:{highest_role}')

        return None

    def _check_tenant_policies(
        self,
        tenant_id: UUID,
        resource_type: str,
        resource_id: Optional[UUID],
        action: str,
    ) -> Optional[tuple[str, str]]:
        """Check tenant-level policies with pattern matching."""
        return self._check_policies(
            tenant_id, PolicyScope.TENANT, None, resource_type, resource_id, action
        )

    def _check_user_policies(
        self,
        user_id: UUID,
        tenant_id: UUID,
        resource_type: str,
        resource_id: Optional[UUID],
        action: str,
    ) -> Optional[tuple[str, str]]:
        """Check user-level policies with pattern matching."""
        return self._check_policies(
            tenant_id, PolicyScope.USER, user_id, resource_type, resource_id, action
        )

    def _check_policies(
        self,
        tenant_id: UUID,
        scope: PolicyScope,
        scope_id: Optional[UUID],
        resource_type: str,
        resource_id: Optional[UUID],
        action: str,
    ) -> Optional[tuple[str, str]]:
        """
        Check policies with pattern matching.

        Returns (decision, reason) tuple or None if no match.
        Priority: Higher priority number = evaluated first, DENY > ALLOW
        """
        # Query policies
        query = self.db.query(Policy).filter(
            Policy.tenant_id == tenant_id,
            Policy.scope == scope,
            Policy.is_active == True,
        )

        if scope == PolicyScope.USER:
            query = query.filter(Policy.scope_id == scope_id)
        else:
            query = query.filter(Policy.scope_id.is_(None))

        # Order by priority descending (higher priority first)
        query = query.order_by(Policy.priority.desc())

        policies = query.all()

        # Evaluate policies in priority order
        for policy in policies:
            if self._matches_pattern(resource_type, resource_id, policy.resource_pattern) and \
               self._matches_action_pattern(action, policy.action_pattern):
                # Match found
                decision = 'allow' if policy.effect == Effect.ALLOW else 'deny'
                scope_str = 'tenant' if scope == PolicyScope.TENANT else 'user'
                return (decision, f'policy:{scope_str}:{policy.name}')

        return None

    def _matches_pattern(self, resource_type: str, resource_id: Optional[UUID], pattern: str) -> bool:
        """
        Check if resource matches pattern.

        Pattern format: "type:id" or "type:*" or "*:*"
        Examples:
            - "crew:*" matches all crews
            - "crew:018e1234..." matches specific crew
            - "*:*" matches everything
        """
        if pattern == "*:*":
            return True

        if ":" not in pattern:
            return False

        pattern_type, pattern_id = pattern.split(":", 1)

        # Check type match
        if pattern_type != "*" and pattern_type != resource_type:
            return False

        # Check ID match
        if pattern_id == "*":
            return True

        if resource_id is None:
            return pattern_id == "*"

        return str(resource_id).startswith(pattern_id.rstrip("*"))

    def _matches_action_pattern(self, action: str, pattern: str) -> bool:
        """
        Check if action matches pattern.

        Pattern examples:
            - "*" matches all actions
            - "read" matches only read
            - "write" matches only write
        """
        if pattern == "*":
            return True

        return action == pattern

    def _audit_log(
        self,
        user_id: UUID,
        tenant_id: UUID,
        resource_type: str,
        resource_id: Optional[UUID],
        action: str,
        decision: str,
        reason: str,
        latency_ms: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log authorization decision to audit log."""
        try:
            audit_log = AuthorizationAuditLog(
                id=generate_uuid_v7(),
                tenant_id=tenant_id,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                decision=AuditDecision.ALLOW if decision == 'allow' else AuditDecision.DENY,
                reason=reason,
                latency_ms=latency_ms,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.db.add(audit_log)
            self.db.commit()
        except Exception as e:
            # Don't fail authorization checks due to audit log errors
            self.db.rollback()
            # Log error but continue
            print(f"Failed to write audit log: {e}")

    def bulk_check_permissions(
        self,
        user_id: UUID,
        tenant_id: UUID,
        checks: List[Dict[str, Any]],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check multiple permissions in batch.

        Args:
            user_id: User performing the actions
            tenant_id: Tenant context
            checks: List of check requests [{resource_type, resource_id, action}, ...]
            ip_address: Request IP for audit log
            user_agent: Request user agent for audit log

        Returns:
            {
                'results': [{'decision': ..., 'reason': ..., 'latency_ms': ...}, ...],
                'total_latency_ms': int
            }
        """
        start_time = time.time()
        results = []

        for check in checks:
            result = self.check_permission(
                user_id=user_id,
                tenant_id=tenant_id,
                resource_type=check['resource_type'],
                resource_id=check.get('resource_id'),
                action=check['action'],
                ip_address=ip_address,
                user_agent=user_agent,
            )
            results.append(result)

        total_latency_ms = int((time.time() - start_time) * 1000)

        return {
            'results': results,
            'total_latency_ms': total_latency_ms
        }
