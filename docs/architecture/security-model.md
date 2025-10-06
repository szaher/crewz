# Security Model

## Overview

The Dynamic CrewAI Orchestration Platform implements defense-in-depth security principles across all layers of the application. This document details the security architecture, authentication mechanisms, authorization controls, and best practices.

## Security Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Users and services have minimum necessary permissions
3. **Zero Trust**: Verify every request, never trust by default
4. **Data Isolation**: Strong tenant boundaries prevent cross-tenant data access
5. **Encryption**: Data encrypted at rest and in transit
6. **Auditability**: All actions logged for compliance and forensics

## Threat Model

### Assets to Protect
- **User Credentials**: Passwords, API keys, OAuth tokens
- **Tenant Data**: Agents, flows, executions, chat history
- **LLM API Keys**: Third-party service credentials
- **Execution Outputs**: Potentially sensitive AI-generated content
- **System Infrastructure**: Kubernetes cluster, databases, Docker

### Threat Actors
- **External Attackers**: Internet-based threats, automated scanners
- **Malicious Users**: Authenticated users attempting privilege escalation
- **Compromised Accounts**: Legitimate accounts taken over by attackers
- **Insider Threats**: Malicious administrators or developers

### Attack Vectors
- **SQL Injection**: Exploiting database queries
- **XSS**: Injecting malicious scripts into frontend
- **CSRF**: Forcing authenticated users to perform unwanted actions
- **Credential Stuffing**: Using leaked credentials from other breaches
- **Container Escape**: Breaking out of Docker isolation
- **API Abuse**: Excessive requests, resource exhaustion

## Authentication

### User Authentication Flow

```
┌──────────────────────────────────────────────────────────┐
│                    1. Registration                       │
│  User provides: email, password, tenant_slug             │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│              2. Password Hashing (bcrypt)                │
│  password_hash = bcrypt.hashpw(password, salt)           │
│  • Cost factor: 12 rounds                                │
│  • Salt: Unique per user                                 │
│  • Stored in public.users table                          │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                   3. Account Created                     │
│  Database: INSERT INTO users (email, password_hash, ...) │
└──────────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────────┐
│                      4. Login                            │
│  User provides: email, password                          │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│              5. Password Verification                    │
│  stored_hash = get_user_by_email(email).password_hash    │
│  valid = bcrypt.checkpw(password, stored_hash)           │
│  • Timing-safe comparison                                │
│  • Rate limiting: 5 attempts per 15 minutes              │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│               6. JWT Token Generation                    │
│  Header:  {"alg": "HS256", "typ": "JWT"}                 │
│  Payload: {                                              │
│    "user_id": "uuid",                                    │
│    "tenant_id": "uuid",                                  │
│    "role": "admin",                                      │
│    "exp": timestamp + 24h,                               │
│    "iat": timestamp                                      │
│  }                                                       │
│  Signature: HMAC-SHA256(header.payload, JWT_SECRET)      │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│          7. Token Delivery (HttpOnly Cookie)             │
│  Set-Cookie: access_token={jwt};                         │
│              HttpOnly;                                   │
│              Secure;                                     │
│              SameSite=Strict;                            │
│              Max-Age=86400                               │
└──────────────────────────────────────────────────────────┘
```

### Implementation

```python
# backend/src/services/auth_service.py

import bcrypt
import jwt
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.jwt_secret = os.getenv("JWT_SECRET")
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = 24

    async def create_user(
        self,
        tenant_id: UUID,
        email: str,
        password: str,
        role: str = "member"
    ) -> User:
        """Create a new user with hashed password."""

        # Hash password with bcrypt (cost factor 12)
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')

        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=True
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def authenticate_user(
        self,
        email: str,
        password: str
    ) -> Optional[User]:
        """Authenticate user with email and password."""

        # Rate limiting check (Redis)
        if await self._is_rate_limited(email):
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Try again later."
            )

        # Get user from database
        result = await self.db.execute(
            select(User).where(User.email == email, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Log failed attempt
            await self._record_failed_login(email)
            return None

        # Verify password (timing-safe)
        valid = bcrypt.checkpw(
            password.encode('utf-8'),
            user.password_hash.encode('utf-8')
        )

        if not valid:
            await self._record_failed_login(email)
            return None

        # Clear failed attempts on successful login
        await self._clear_failed_attempts(email)

        return user

    def create_access_token(
        self,
        user_id: str,
        tenant_id: str,
        role: str
    ) -> str:
        """Generate JWT access token."""

        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours),
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())  # Unique token ID for revocation
        }

        token = jwt.encode(
            payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm
        )

        return token

    def verify_token(self, token: str) -> dict:
        """Verify and decode JWT token."""

        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )

            # Check if token is revoked (Redis check)
            if await self._is_token_revoked(payload["jti"]):
                raise HTTPException(status_code=401, detail="Token has been revoked")

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    async def _is_rate_limited(self, email: str) -> bool:
        """Check if user is rate limited based on failed login attempts."""
        from src.db.redis import get_redis_client

        redis = get_redis_client()
        key = f"login_attempts:{email}"
        attempts = await redis.get(key)

        if attempts and int(attempts) >= 5:
            return True

        return False

    async def _record_failed_login(self, email: str):
        """Record failed login attempt."""
        from src.db.redis import get_redis_client

        redis = get_redis_client()
        key = f"login_attempts:{email}"

        await redis.incr(key)
        await redis.expire(key, 900)  # 15 minutes TTL

    async def _clear_failed_attempts(self, email: str):
        """Clear failed login attempts after successful login."""
        from src.db.redis import get_redis_client

        redis = get_redis_client()
        key = f"login_attempts:{email}"
        await redis.delete(key)
```

### Password Security Requirements

**Password Policy:**
- Minimum length: 12 characters
- Must contain: uppercase, lowercase, number, special character
- Cannot be common password (check against leaked password database)
- Cannot be same as previous 3 passwords

**Implementation:**
```python
import re
from passlib.pwd import genword

class PasswordValidator:
    def __init__(self):
        # Load common passwords from file
        with open("common_passwords.txt") as f:
            self.common_passwords = set(f.read().splitlines())

    def validate(self, password: str) -> tuple[bool, str]:
        """Validate password strength."""

        if len(password) < 12:
            return False, "Password must be at least 12 characters"

        if not re.search(r"[A-Z]", password):
            return False, "Password must contain uppercase letter"

        if not re.search(r"[a-z]", password):
            return False, "Password must contain lowercase letter"

        if not re.search(r"\d", password):
            return False, "Password must contain number"

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain special character"

        if password.lower() in self.common_passwords:
            return False, "Password is too common"

        return True, "Password is valid"
```

## Authorization (RBAC)

### Role Hierarchy

```
┌─────────────────────────────────────────────────┐
│                 Tenant Admin                    │
│  • Full control over tenant resources           │
│  • User management (invite, remove, change role)│
│  • Billing and subscription                     │
│  • Audit log access                             │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│                   Member                        │
│  • Create/read/update/delete own resources      │
│  • Execute flows                                │
│  • View execution logs                          │
│  • Collaborate on shared resources              │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│                   Viewer                        │
│  • Read-only access to resources                │
│  • View execution results                       │
│  • Cannot create or modify                      │
└─────────────────────────────────────────────────┘
```

### Permission Matrix

| Resource | Action | Admin | Member | Viewer |
|----------|--------|-------|--------|--------|
| **Agents** | create | ✅ | ✅ | ❌ |
| | read | ✅ | ✅ | ✅ |
| | update | ✅ | ✅ (own) | ❌ |
| | delete | ✅ | ✅ (own) | ❌ |
| **Flows** | create | ✅ | ✅ | ❌ |
| | read | ✅ | ✅ | ✅ |
| | update | ✅ | ✅ (own) | ❌ |
| | delete | ✅ | ✅ (own) | ❌ |
| | execute | ✅ | ✅ | ❌ |
| **Executions** | read | ✅ | ✅ | ✅ |
| | cancel | ✅ | ✅ (own) | ❌ |
| **Users** | invite | ✅ | ❌ | ❌ |
| | remove | ✅ | ❌ | ❌ |
| | change_role | ✅ | ❌ | ❌ |
| **Billing** | view | ✅ | ❌ | ❌ |
| | update | ✅ | ❌ | ❌ |

### Implementation

```python
# backend/src/middleware/authorization.py

from functools import wraps
from fastapi import HTTPException, Depends
from src.models import User

# Permission definitions
PERMISSIONS = {
    "admin": {
        "agents": ["create", "read", "update", "delete"],
        "flows": ["create", "read", "update", "delete", "execute"],
        "executions": ["read", "cancel"],
        "users": ["invite", "remove", "change_role"],
        "billing": ["view", "update"]
    },
    "member": {
        "agents": ["create", "read", "update_own", "delete_own"],
        "flows": ["create", "read", "update_own", "delete_own", "execute"],
        "executions": ["read", "cancel_own"]
    },
    "viewer": {
        "agents": ["read"],
        "flows": ["read"],
        "executions": ["read"]
    }
}


def require_permission(resource: str, action: str):
    """Decorator to check if user has required permission."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            # Check if user's role has permission
            user_permissions = PERMISSIONS.get(current_user.role, {})
            allowed_actions = user_permissions.get(resource, [])

            if action not in allowed_actions:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {resource}:{action}"
                )

            return await func(*args, current_user=current_user, **kwargs)

        return wrapper
    return decorator


# Usage in endpoints
@router.delete("/agents/{agent_id}")
@require_permission("agents", "delete")
async def delete_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    agent = await db.get(Agent, agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # For "delete_own" permission, verify ownership
    if current_user.role == "member" and agent.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own agents"
        )

    await db.delete(agent)
    await db.commit()

    return {"message": "Agent deleted successfully"}
```

## Data Encryption

### Encryption at Rest

**Database Encryption:**
- PostgreSQL: Transparent Data Encryption (TDE) enabled
- MongoDB: Encrypted storage engine with AES-256
- Redis: RDB/AOF files encrypted on disk

**LLM API Key Encryption:**
```python
# backend/src/services/encryption_service.py

from cryptography.fernet import Fernet
import base64
import os

class EncryptionService:
    def __init__(self):
        # Load encryption key from environment
        key = os.getenv("ENCRYPTION_KEY")  # 32-byte key
        self.cipher = Fernet(base64.urlsafe_b64encode(key.encode()))

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt sensitive data."""
        return self.cipher.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt sensitive data."""
        return self.cipher.decrypt(ciphertext).decode()


# Usage for LLM provider API keys
async def create_llm_provider(
    provider_data: LLMProviderCreate,
    db: AsyncSession
):
    encryption_service = EncryptionService()

    # Encrypt API key before storing
    encrypted_api_key = encryption_service.encrypt(provider_data.api_key)

    provider = LLMProvider(
        name=provider_data.name,
        provider_type=provider_data.provider_type,
        encrypted_credentials=encrypted_api_key,
        config=provider_data.config
    )

    db.add(provider)
    await db.commit()

    return provider
```

### Encryption in Transit

**TLS/HTTPS:**
- All API traffic over HTTPS with TLS 1.3
- Certificate management via cert-manager (Let's Encrypt)
- HSTS header enforced (Strict-Transport-Security)

```yaml
# Kubernetes Ingress with TLS
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: crewai-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - app.crewai-platform.com
    - api.crewai-platform.com
    secretName: crewai-tls-cert
  rules:
  - host: api.crewai-platform.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
```

**Database Connections:**
```python
# PostgreSQL SSL connection
DATABASE_URL = "postgresql://user:pass@host:5432/db?sslmode=require"

# MongoDB TLS
MONGODB_URL = "mongodb://user:pass@host:27017/?tls=true&tlsCertificateKeyFile=/path/to/cert.pem"
```

## Container Security

### Docker-in-Docker Isolation

```yaml
# Secure DinD deployment with Sysbox
apiVersion: apps/v1
kind: Deployment
metadata:
  name: docker-dind
spec:
  template:
    spec:
      runtimeClassName: sysbox-runc  # Sysbox for unprivileged containers
      containers:
      - name: docker
        image: docker:24-dind
        securityContext:
          privileged: false  # No privileged mode needed
          runAsNonRoot: true
          runAsUser: 1000
          capabilities:
            drop: ["ALL"]
          readOnlyRootFilesystem: true
        resources:
          limits:
            cpu: "2"
            memory: "4Gi"
          requests:
            cpu: "500m"
            memory: "1Gi"
```

### Network Policies

```yaml
# Restrict network traffic between pods
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-network-policy
spec:
  podSelector:
    matchLabels:
      app: crewai-backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: crewai-frontend
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: mongodb
    ports:
    - protocol: TCP
      port: 27017
  # Block all other egress traffic
```

### Image Scanning

```yaml
# GitHub Actions: Trivy security scan
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ghcr.io/org/repo/backend:${{ github.sha }}
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'  # Fail build on vulnerabilities

- name: Upload Trivy results to GitHub Security
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-results.sarif'
```

## API Security

### Rate Limiting

```python
# backend/src/middleware/rate_limit.py

from fastapi import Request, HTTPException
from src.db.redis import get_redis_client
import time

class RateLimiter:
    def __init__(
        self,
        requests_per_minute: int = 100,
        requests_per_hour: int = 1000
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

    async def check_rate_limit(self, request: Request):
        """Check if request should be rate limited."""
        redis = get_redis_client()

        user_id = request.state.user_id
        now = int(time.time())

        # Minute window
        minute_key = f"rate_limit:minute:{user_id}:{now // 60}"
        minute_count = await redis.incr(minute_key)
        await redis.expire(minute_key, 60)

        if minute_count > self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded: too many requests per minute"
            )

        # Hour window
        hour_key = f"rate_limit:hour:{user_id}:{now // 3600}"
        hour_count = await redis.incr(hour_key)
        await redis.expire(hour_key, 3600)

        if hour_count > self.requests_per_hour:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded: too many requests per hour"
            )

# Apply to FastAPI app
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    rate_limiter = RateLimiter()
    await rate_limiter.check_rate_limit(request)
    response = await call_next(request)
    return response
```

### Input Validation

```python
# Pydantic schemas with strict validation

from pydantic import BaseModel, Field, validator
import re

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    goal: str = Field(..., min_length=10, max_length=5000)
    backstory: str | None = Field(None, max_length=10000)

    @validator('name')
    def validate_name(cls, v):
        # Prevent XSS in names
        if re.search(r'[<>"\']', v):
            raise ValueError("Name contains invalid characters")
        return v

    @validator('goal')
    def validate_goal(cls, v):
        # Ensure goal is meaningful
        if len(v.split()) < 3:
            raise ValueError("Goal must be at least 3 words")
        return v
```

### CORS Configuration

```python
# backend/src/main.py

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.crewai-platform.com",
        "https://staging.crewai-platform.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    max_age=3600
)
```

### Content Security Policy

```python
# Add CSP headers to responses

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self' wss://api.crewai-platform.com; "
        "frame-ancestors 'none';"
    )

    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response
```

## Audit Logging

### Audit Trail

```python
# backend/src/services/audit_service.py

from src.db.mongodb import get_mongodb_client
from datetime import datetime

class AuditService:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.collection = f"audit_logs_{tenant_id}"

    async def log_action(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None
    ):
        """Log an auditable action."""

        mongo_client = get_mongodb_client()
        db = mongo_client.get_database()

        log_entry = {
            "user_id": user_id,
            "action": action,  # create, read, update, delete
            "resource_type": resource_type,
            "resource_id": resource_id,
            "changes": changes,  # {"before": {...}, "after": {...}}
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow()
        }

        await db[self.collection].insert_one(log_entry)


# Usage in endpoints
@router.put("/agents/{agent_id}")
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    agent = await db.get(Agent, agent_id)

    # Capture before state
    before = agent.dict()

    # Update agent
    for field, value in agent_data.dict(exclude_unset=True).items():
        setattr(agent, field, value)

    await db.commit()

    # Capture after state
    after = agent.dict()

    # Log audit trail
    audit_service = AuditService(str(current_user.tenant_id))
    await audit_service.log_action(
        user_id=str(current_user.id),
        action="update",
        resource_type="agent",
        resource_id=str(agent_id),
        changes={"before": before, "after": after},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    return agent
```

## Secrets Management

### Kubernetes Secrets

```yaml
# External secrets synced from cloud provider
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: crewai-secrets
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: crewai-app-secrets
  data:
  - secretKey: jwt-secret
    remoteRef:
      key: crewai/prod/jwt-secret
  - secretKey: database-password
    remoteRef:
      key: crewai/prod/database-password
  - secretKey: encryption-key
    remoteRef:
      key: crewai/prod/encryption-key
```

### Environment Variables

```python
# NEVER hardcode secrets
BAD_EXAMPLE = "sk-1234567890abcdef"  # ❌ NEVER DO THIS

# ALWAYS use environment variables
GOOD_EXAMPLE = os.getenv("OPENAI_API_KEY")  # ✅ CORRECT

# Validate that secrets are set
if not os.getenv("JWT_SECRET"):
    raise ValueError("JWT_SECRET environment variable not set")
```

## Compliance

### GDPR Compliance

**Right to Access:**
```python
@router.get("/users/me/data")
async def get_user_data(current_user: User = Depends(get_current_user)):
    """Export all user data (GDPR Article 15)."""

    data = {
        "user": current_user.dict(),
        "agents": await get_user_agents(current_user.id),
        "flows": await get_user_flows(current_user.id),
        "executions": await get_user_executions(current_user.id)
    }

    return data
```

**Right to Erasure:**
```python
@router.delete("/users/me")
async def delete_user_account(current_user: User = Depends(get_current_user)):
    """Delete user account and all associated data (GDPR Article 17)."""

    # Delete PostgreSQL data
    await delete_user_postgres_data(current_user.id)

    # Delete MongoDB logs
    await delete_user_mongodb_logs(current_user.id)

    # Anonymize audit logs (retain for compliance)
    await anonymize_audit_logs(current_user.id)

    return {"message": "Account deleted successfully"}
```

## Incident Response

### Security Event Detection

```python
# Monitor for suspicious activity

from src.utils.observability import app_metrics

# Detect brute force attacks
app_metrics.failed_logins_total.labels(email=email).inc()

# Alert on excessive failed logins
if failed_login_count > 10:
    await send_security_alert(
        severity="high",
        message=f"Potential brute force attack on account: {email}"
    )

# Detect unusual API usage
if requests_per_minute > 1000:
    await send_security_alert(
        severity="medium",
        message=f"Unusual API usage from user: {user_id}"
    )
```

## Security Checklist

### Development
- [ ] All secrets stored in environment variables
- [ ] Passwords hashed with bcrypt (cost factor 12+)
- [ ] Input validation on all endpoints
- [ ] SQL parameterized queries (no string interpolation)
- [ ] Dependency scanning enabled (Snyk, Dependabot)

### Deployment
- [ ] TLS/HTTPS enforced
- [ ] Container images scanned for vulnerabilities
- [ ] Kubernetes NetworkPolicies applied
- [ ] Database encryption at rest enabled
- [ ] Secrets stored in secret manager (not Git)

### Operations
- [ ] Rate limiting enabled
- [ ] Audit logging implemented
- [ ] Security monitoring and alerting
- [ ] Regular security audits scheduled
- [ ] Incident response plan documented

## Conclusion

Security is a continuous process requiring vigilance at all layers. Key takeaways:

1. **Authentication**: bcrypt + JWT with HttpOnly cookies
2. **Authorization**: RBAC with least privilege principle
3. **Encryption**: At rest (database) and in transit (TLS)
4. **Container Security**: Sysbox runtime, network policies, image scanning
5. **API Security**: Rate limiting, input validation, CORS, CSP
6. **Audit Logging**: All actions logged for compliance
7. **Secrets Management**: Never commit secrets, use secret managers

For additional security topics, see:
- [Multi-Tenancy Guide](./multi-tenancy.md)
- [System Architecture](./system-overview.md)
