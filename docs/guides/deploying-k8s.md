# Kubernetes Deployment Guide

## Overview

This guide covers deploying the Dynamic CrewAI Orchestration Platform to Kubernetes for production use.

## Prerequisites

- Kubernetes cluster (1.28+)
- kubectl configured
- Helm 3.x
- Container registry access (Docker Hub, GHCR, etc.)
- Domain name with DNS access
- SSL certificate (or cert-manager for Let's Encrypt)

## Architecture

```
┌─────────────────────────────────────────────────┐
│             Ingress (NGINX)                     │
│  • TLS termination                              │
│  • Load balancing                               │
└─────────────────────────────────────────────────┘
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
┌───────────────┐       ┌───────────────┐
│   Frontend    │       │    Backend    │
│  (3 replicas) │       │  (3 replicas) │
└───────────────┘       └───────────────┘
        │                        │
        └───────────┬────────────┘
                    ▼
        ┌───────────────────────┐
        │    PostgreSQL         │
        │    MongoDB            │
        │    Redis              │
        └───────────────────────┘
```

## Quick Start

### 1. Build Docker Images

```bash
# Build backend
docker build -f infra/docker/backend.Dockerfile -t your-registry/crewai-backend:v1.0.0 .
docker push your-registry/crewai-backend:v1.0.0

# Build frontend
docker build -f infra/docker/frontend.Dockerfile -t your-registry/crewai-frontend:v1.0.0 .
docker push your-registry/crewai-frontend:v1.0.0
```

### 2. Create Namespace

```bash
kubectl create namespace crewai-prod
kubectl config set-context --current --namespace=crewai-prod
```

### 3. Configure Secrets

```bash
# Create secrets from environment files
kubectl create secret generic crewai-secrets \
  --from-literal=jwt-secret=$(openssl rand -base64 32) \
  --from-literal=encryption-key=$(openssl rand -base64 32) \
  --from-literal=database-password=$(openssl rand -base64 24) \
  --from-literal=mongodb-password=$(openssl rand -base64 24) \
  --from-literal=redis-password=$(openssl rand -base64 24)

# TLS certificate (or use cert-manager)
kubectl create secret tls crewai-tls-cert \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key
```

### 4. Deploy with Kustomize

```bash
# Deploy to production
kubectl apply -k infra/kubernetes/overlays/prod

# Verify deployment
kubectl get pods
kubectl get services
kubectl get ingress
```

### 5. Initialize Database

```bash
# Run migrations
kubectl exec -it deployment/backend -- alembic upgrade head

# Create initial tenant
kubectl exec -it deployment/backend -- python scripts/create_initial_tenant.py
```

## Detailed Configuration

### PostgreSQL StatefulSet

**infra/kubernetes/base/postgres-statefulset.yaml:**

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: crewai
        - name: POSTGRES_USER
          value: crewai
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: crewai-secrets
              key: database-password
        ports:
        - containerPort: 5432
          name: postgres
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2
            memory: 4Gi
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi
```

### Backend Deployment

**infra/kubernetes/base/backend-deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crewai-backend
  template:
    metadata:
      labels:
        app: crewai-backend
    spec:
      containers:
      - name: backend
        image: your-registry/crewai-backend:v1.0.0
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: DATABASE_URL
          value: postgresql://crewai:$(DATABASE_PASSWORD)@postgres:5432/crewai
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: crewai-secrets
              key: database-password
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: crewai-secrets
              key: jwt-secret
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: http
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2
            memory: 4Gi
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Ingress with TLS

**infra/kubernetes/base/services.yaml:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: crewai-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  ingressClassName: nginx
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
  - host: app.crewai-platform.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
```

## Environment-Specific Overlays

### Production Overlay

**infra/kubernetes/overlays/prod/kustomization.yaml:**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: crewai-prod

resources:
- ../../base

images:
- name: crewai-backend
  newName: your-registry/crewai-backend
  newTag: v1.0.0
- name: crewai-frontend
  newName: your-registry/crewai-frontend
  newTag: v1.0.0

replicas:
- name: backend
  count: 5
- name: frontend
  count: 3

configMapGenerator:
- name: app-config
  literals:
  - ENVIRONMENT=production
  - LOG_LEVEL=INFO
  - OTEL_ENABLED=true

patchesStrategicMerge:
- backend-resources.yaml
```

### Staging Overlay

**infra/kubernetes/overlays/staging/kustomization.yaml:**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: crewai-staging

resources:
- ../../base

images:
- name: crewai-backend
  newTag: staging-latest

replicas:
- name: backend
  count: 2
- name: frontend
  count: 1

configMapGenerator:
- name: app-config
  literals:
  - ENVIRONMENT=staging
  - LOG_LEVEL=DEBUG
```

## Monitoring & Observability

### Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: crewai-backend
spec:
  selector:
    matchLabels:
      app: crewai-backend
  endpoints:
  - port: metrics
    interval: 30s
```

### Grafana Dashboard

Import dashboard from `infra/observability/grafana/dashboards/platform-overview.json`

## Backup & Restore

### Database Backup

```bash
# Create backup
kubectl exec -it postgres-0 -- pg_dump -U crewai -F c -b -v -f /tmp/backup.dump

# Copy backup to local
kubectl cp postgres-0:/tmp/backup.dump ./backup-$(date +%Y%m%d).dump

# Upload to S3
aws s3 cp ./backup-$(date +%Y%m%d).dump s3://your-bucket/backups/
```

### Restore from Backup

```bash
# Download from S3
aws s3 cp s3://your-bucket/backups/backup-20241201.dump ./restore.dump

# Copy to pod
kubectl cp ./restore.dump postgres-0:/tmp/restore.dump

# Restore
kubectl exec -it postgres-0 -- pg_restore -U crewai -d crewai -v /tmp/restore.dump
```

## Scaling

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment backend --replicas=10

# Scale workers
kubectl scale deployment celery-workers --replicas=20
```

### Auto-Scaling

HPA configuration is included in deployment manifests.

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods

# View pod logs
kubectl logs -f pod-name

# Describe pod for events
kubectl describe pod pod-name
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
kubectl run -it --rm psql --image=postgres:15-alpine --restart=Never -- \
  psql -h postgres -U crewai -d crewai

# Check service endpoints
kubectl get endpoints postgres
```

### Ingress Not Working

```bash
# Check ingress
kubectl describe ingress crewai-ingress

# Check NGINX controller logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

## Rolling Updates

```bash
# Update backend image
kubectl set image deployment/backend backend=your-registry/crewai-backend:v1.1.0

# Monitor rollout
kubectl rollout status deployment/backend

# Rollback if needed
kubectl rollout undo deployment/backend
```

## Health Checks

### Backend Health Endpoint

```bash
# Check health
curl https://api.crewai-platform.com/health

# Check readiness
curl https://api.crewai-platform.com/health/ready
```

## Production Checklist

- [ ] SSL certificates configured
- [ ] Secrets stored securely (not in Git)
- [ ] Resource limits set on all pods
- [ ] HPA configured for auto-scaling
- [ ] PodDisruptionBudget configured
- [ ] NetworkPolicies applied
- [ ] Monitoring and alerting configured
- [ ] Backup automation set up
- [ ] Log aggregation configured
- [ ] Disaster recovery plan documented

## Next Steps

- [Local Development Setup](./local-development.md)
- [Create Flows](./creating-flows.md)
- [Review Architecture](../architecture/system-overview.md)
