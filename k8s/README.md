# Kubernetes Deployment Guide - FinSight AI

This directory contains Kubernetes manifests for deploying FinSight AI to a Kubernetes cluster.

## 🧪 Local Testing First?

**Want to test locally before production?** See our quick guides:
- **[Quick Start (Docker Desktop)](../docs/deployment/QUICKSTART-K8S.md)** - 2-minute setup
- **[Full Local Setup Guide](../docs/deployment/LOCAL-KUBERNETES-SETUP.md)** - All options (Docker Desktop, Minikube, Kind)

Run the automated test script:
```bash
./scripts/test-k8s-local.sh
```

---

## Prerequisites

- Kubernetes cluster (v1.24+)
- `kubectl` CLI installed and configured
- NGINX Ingress Controller installed
- cert-manager (optional, for SSL/TLS)
- Storage class configured (for PVCs)

## Quick Start

### 1. Create Namespace and Secrets

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Update secrets (IMPORTANT: Change default passwords!)
kubectl apply -f configmap-secrets.yaml
```

### 2. Create Persistent Volumes

```bash
kubectl apply -f persistent-volumes.yaml
```

### 3. Deploy Services

Deploy in this order to ensure dependencies are met:

```bash
# 1. Redis (cache)
kubectl apply -f redis-deployment.yaml

# 2. Ollama (LLM)
kubectl apply -f ollama-deployment.yaml

# 3. Backend (FastAPI)
kubectl apply -f backend-deployment.yaml

# 4. Frontend (Next.js)
kubectl apply -f frontend-deployment.yaml
```

### 4. Configure Ingress

Update the domain names in `ingress.yaml`, then apply:

```bash
kubectl apply -f ingress.yaml
```

## Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n finsight-ai

# Check services
kubectl get svc -n finsight-ai

# Check ingress
kubectl get ingress -n finsight-ai

# View logs
kubectl logs -f deployment/backend -n finsight-ai
kubectl logs -f deployment/frontend -n finsight-ai
```

## Scaling

### Manual Scaling

```bash
# Scale backend replicas
kubectl scale deployment backend -n finsight-ai --replicas=5

# Scale frontend replicas
kubectl scale deployment frontend -n finsight-ai --replicas=3
```

### Auto-scaling

HorizontalPodAutoscalers (HPA) are already configured:

```bash
# Check HPA status
kubectl get hpa -n finsight-ai

# View HPA details
kubectl describe hpa backend-hpa -n finsight-ai
```

## Updating Deployments

### Update Container Images

```bash
# Update backend image
kubectl set image deployment/backend backend=finsight-backend:v2.0 -n finsight-ai

# Update frontend image
kubectl set image deployment/frontend frontend=finsight-frontend:v2.0 -n finsight-ai

# Check rollout status
kubectl rollout status deployment/backend -n finsight-ai
```

### Rollback Deployment

```bash
# Rollback to previous version
kubectl rollout undo deployment/backend -n finsight-ai

# Rollback to specific revision
kubectl rollout undo deployment/backend --to-revision=2 -n finsight-ai
```

## Configuration Updates

### Update ConfigMaps

```bash
# Edit ConfigMap
kubectl edit configmap backend-config -n finsight-ai

# Restart deployment to pick up changes
kubectl rollout restart deployment/backend -n finsight-ai
```

### Update Secrets

```bash
# Edit Secret
kubectl edit secret finsight-secrets -n finsight-ai

# Restart affected deployments
kubectl rollout restart deployment/backend -n finsight-ai
kubectl rollout restart deployment/redis -n finsight-ai
```

## Monitoring & Debugging

### View Logs

```bash
# Tail logs from all backend pods
kubectl logs -f -l app=backend -n finsight-ai

# View logs from specific pod
kubectl logs backend-7d4b5c6f9-abc12 -n finsight-ai

# View previous crashed container logs
kubectl logs backend-7d4b5c6f9-abc12 --previous -n finsight-ai
```

### Execute Commands in Pods

```bash
# Get shell access to backend pod
kubectl exec -it deployment/backend -n finsight-ai -- /bin/bash

# Run Python command
kubectl exec -it deployment/backend -n finsight-ai -- python -c "import sys; print(sys.version)"
```

### Port Forwarding (for local access)

```bash
# Forward backend port
kubectl port-forward service/backend-service 8000:8000 -n finsight-ai

# Forward frontend port
kubectl port-forward service/frontend-service 3000:3000 -n finsight-ai
```

## Resource Management

### View Resource Usage

```bash
# View pod resource usage
kubectl top pods -n finsight-ai

# View node resource usage
kubectl top nodes
```

### Update Resource Limits

Edit the deployment YAML files and update the `resources` section, then apply:

```bash
kubectl apply -f backend-deployment.yaml
```

## Persistent Data

### Backup Data

```bash
# Create backup of backend data
kubectl exec deployment/backend -n finsight-ai -- tar czf /tmp/backup.tar.gz /app/data
kubectl cp finsight-ai/$(kubectl get pod -n finsight-ai -l app=backend -o jsonpath='{.items[0].metadata.name}'):/tmp/backup.tar.gz ./backup.tar.gz
```

### Restore Data

```bash
# Copy backup to pod
kubectl cp ./backup.tar.gz finsight-ai/$(kubectl get pod -n finsight-ai -l app=backend -o jsonpath='{.items[0].metadata.name}'):/tmp/backup.tar.gz

# Extract backup
kubectl exec deployment/backend -n finsight-ai -- tar xzf /tmp/backup.tar.gz -C /
```

## SSL/TLS Configuration

### Using cert-manager

1. Install cert-manager:
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

2. Create ClusterIssuer:
```bash
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

3. Update ingress.yaml with your domain and apply.

## Production Checklist

- [ ] Update all secrets (REDIS_PASSWORD, etc.)
- [ ] Configure proper domain names in ingress.yaml
- [ ] Set up SSL/TLS certificates
- [ ] Configure resource limits based on workload
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Configure log aggregation (ELK, Loki)
- [ ] Set up backup strategy for PVCs
- [ ] Configure network policies for security
- [ ] Enable pod security policies
- [ ] Set up CI/CD pipeline for automated deployments

## Troubleshooting

### Pods Not Starting

```bash
# Describe pod to see events
kubectl describe pod <pod-name> -n finsight-ai

# Check pod events
kubectl get events -n finsight-ai --sort-by='.lastTimestamp'
```

### Service Connection Issues

```bash
# Test service connectivity from another pod
kubectl run -it --rm debug --image=nicolaka/netshoot -n finsight-ai -- /bin/bash
# Inside the pod:
curl http://backend-service:8000/health
```

### PVC Issues

```bash
# Check PVC status
kubectl get pvc -n finsight-ai

# Describe PVC for details
kubectl describe pvc backend-data-pvc -n finsight-ai
```

## Clean Up

### Delete Everything

```bash
# Delete all resources in namespace
kubectl delete namespace finsight-ai

# Or delete individually
kubectl delete -f frontend-deployment.yaml
kubectl delete -f backend-deployment.yaml
kubectl delete -f ollama-deployment.yaml
kubectl delete -f redis-deployment.yaml
kubectl delete -f persistent-volumes.yaml
kubectl delete -f configmap-secrets.yaml
kubectl delete -f namespace.yaml
```

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
