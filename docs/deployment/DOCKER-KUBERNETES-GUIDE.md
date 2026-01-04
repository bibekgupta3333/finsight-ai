# Docker & Kubernetes Deployment Guide

## Overview

This guide covers deploying FinSight AI using Docker and Kubernetes.

## Docker Deployment

### Local Development

The existing `docker-compose.yml` is configured for local development:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Production Deployment

Use `docker-compose.prod.yml` for production:

```bash
# Set environment variables
cp .env.prod.example .env.prod
# Edit .env.prod with your values

# Build and start services
export REDIS_PASSWORD=$(grep REDIS_PASSWORD .env.prod | cut -d'=' -f2)
docker-compose -f docker-compose.prod.yml up -d --build

# View service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend frontend

# Stop services
docker-compose -f docker-compose.prod.yml down
```

### Building Individual Images

```bash
# Backend
cd backend
docker build -t finsight-backend:v1.0 .

# Frontend
cd frontend
docker build -t finsight-frontend:v1.0 .
```

### Push to Registry

```bash
# Tag images
docker tag finsight-backend:v1.0 your-registry/finsight-backend:v1.0
docker tag finsight-frontend:v1.0 your-registry/finsight-frontend:v1.0

# Push to registry
docker push your-registry/finsight-backend:v1.0
docker push your-registry/finsight-frontend:v1.0
```

## Kubernetes Deployment

See [k8s/README.md](../k8s/README.md) for detailed Kubernetes deployment instructions.

### Quick Start

```bash
# Create namespace and apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap-secrets.yaml
kubectl apply -f k8s/persistent-volumes.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/ollama-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Check status
kubectl get all -n finsight-ai
```

## Architecture

### Components

1. **Frontend (Next.js)**
   - Port: 3000
   - Replicas: 2-5 (auto-scaling)
   - Resources: 512Mi-1Gi RAM, 250m-500m CPU

2. **Backend (FastAPI)**
   - Port: 8000
   - Replicas: 2-10 (auto-scaling)
   - Resources: 1Gi-2Gi RAM, 500m-1000m CPU

3. **Redis (Cache)**
   - Port: 6379
   - Replicas: 1
   - Resources: 256Mi-512Mi RAM, 100m-500m CPU
   - Persistent Volume: 5Gi

4. **Ollama (LLM)**
   - Port: 11434
   - Replicas: 1
   - Resources: 4Gi-8Gi RAM, 2-4 CPU, 1 GPU (optional)
   - Persistent Volume: 50Gi

### Network Flow

```
Internet → Ingress → Frontend Service → Frontend Pods
                  → Backend Service → Backend Pods
                                    → Redis Service → Redis Pod
                                    → Ollama Service → Ollama Pod
```

## Health Checks

All services include health checks:

- **Backend**: `GET /health`
- **Frontend**: `GET /` (homepage)
- **Redis**: `redis-cli ping`
- **Ollama**: `GET /api/tags`

## Monitoring

### Docker

```bash
# View resource usage
docker stats

# Check container health
docker ps --filter health=unhealthy
```

### Kubernetes

```bash
# View pod resource usage
kubectl top pods -n finsight-ai

# View pod health
kubectl get pods -n finsight-ai

# View events
kubectl get events -n finsight-ai --sort-by='.lastTimestamp'
```

## Scaling

### Docker Compose

Docker Compose doesn't support auto-scaling. Use Kubernetes for production scaling.

### Kubernetes

Auto-scaling is configured via HorizontalPodAutoscaler (HPA):

- **Backend**: 2-10 replicas based on CPU/memory
- **Frontend**: 2-5 replicas based on CPU/memory

```bash
# View HPA status
kubectl get hpa -n finsight-ai

# Manual scaling
kubectl scale deployment backend --replicas=5 -n finsight-ai
```

## Backup & Recovery

### Docker Volumes

```bash
# Backup backend data
docker run --rm -v finsight-ai_backend_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/backend-data-backup.tar.gz /data

# Restore backend data
docker run --rm -v finsight-ai_backend_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/backend-data-backup.tar.gz -C /
```

### Kubernetes PVCs

```bash
# Backup backend data
kubectl exec -n finsight-ai deployment/backend -- tar czf /tmp/backup.tar.gz /app/data
kubectl cp finsight-ai/$(kubectl get pod -n finsight-ai -l app=backend -o jsonpath='{.items[0].metadata.name}'):/tmp/backup.tar.gz ./backup.tar.gz

# Restore backend data
kubectl cp ./backup.tar.gz finsight-ai/$(kubectl get pod -n finsight-ai -l app=backend -o jsonpath='{.items[0].metadata.name}'):/tmp/backup.tar.gz
kubectl exec -n finsight-ai deployment/backend -- tar xzf /tmp/backup.tar.gz -C /
```

## Security Best Practices

1. **Secrets Management**
   - Never commit secrets to git
   - Use Kubernetes Secrets or external secret managers (AWS Secrets Manager, HashiCorp Vault)
   - Rotate secrets regularly

2. **Network Security**
   - Use TLS/SSL for all external traffic
   - Implement network policies in Kubernetes
   - Use private container registries

3. **Image Security**
   - Scan images for vulnerabilities
   - Use minimal base images (alpine, distroless)
   - Run as non-root user
   - Keep dependencies updated

4. **Access Control**
   - Use RBAC in Kubernetes
   - Implement API authentication
   - Use least privilege principle

## Troubleshooting

### Common Issues

1. **Container fails to start**
   ```bash
   # Docker
   docker logs <container-name>

   # Kubernetes
   kubectl logs -n finsight-ai pod/<pod-name>
   kubectl describe pod/<pod-name> -n finsight-ai
   ```

2. **Service connection issues**
   ```bash
   # Docker
   docker network inspect finsight-network

   # Kubernetes
   kubectl get svc -n finsight-ai
   kubectl describe svc <service-name> -n finsight-ai
   ```

3. **Resource constraints**
   ```bash
   # Docker
   docker stats

   # Kubernetes
   kubectl top pods -n finsight-ai
   kubectl describe nodes
   ```

## Performance Optimization

1. **Image Optimization**
   - Use multi-stage builds
   - Minimize layers
   - Use .dockerignore files
   - Cache dependencies

2. **Resource Limits**
   - Set appropriate CPU/memory limits
   - Use resource quotas in Kubernetes
   - Monitor and adjust based on usage

3. **Caching**
   - Use Redis for session/data caching
   - Implement HTTP caching headers
   - Use CDN for static assets

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Deploy to Kubernetes

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Backend
        run: docker build -t registry/backend:${{ github.sha }} backend/

      - name: Build Frontend
        run: docker build -t registry/frontend:${{ github.sha }} frontend/

      - name: Push Images
        run: |
          docker push registry/backend:${{ github.sha }}
          docker push registry/frontend:${{ github.sha }}

      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/backend backend=registry/backend:${{ github.sha }} -n finsight-ai
          kubectl set image deployment/frontend frontend=registry/frontend:${{ github.sha }} -n finsight-ai
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Docker Compose File Reference](https://docs.docker.com/compose/compose-file/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
