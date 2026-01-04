# Quick Start: Docker Desktop Kubernetes

**Fastest way to test Kubernetes manifests on macOS**

---

## Setup (2 minutes)

### 1. Enable Kubernetes in Docker Desktop

```bash
# Open Docker Desktop
# Click Settings (⚙️) → Kubernetes → Enable Kubernetes → Apply & Restart
```

**Wait 2-5 minutes** for Kubernetes to initialize.

### 2. Verify Installation

```bash
kubectl version --client
kubectl get nodes
```

Expected output:
```
NAME             STATUS   ROLES           AGE   VERSION
docker-desktop   Ready    control-plane   2m    v1.28.2
```

### 3. Install NGINX Ingress Controller

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml

# Wait for ready
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```

### 4. Install Metrics Server (for auto-scaling)

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Patch for local development
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'

# Verify (wait 30 seconds)
kubectl top nodes
```

---

## Deploy FinSight AI

### Option A: Automated Script (Recommended)

```bash
# Run the test script
./scripts/test-k8s-local.sh
```

This will:
- ✅ Build Docker images
- ✅ Deploy all Kubernetes manifests
- ✅ Wait for pods to be ready
- ✅ Setup port forwarding
- ✅ Display access URLs

### Option B: Manual Deployment

```bash
# 1. Build images
docker build -t finsight-backend:latest ./backend
docker build -t finsight-frontend:latest ./frontend

# 2. Deploy Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap-secrets.yaml
kubectl apply -f k8s/persistent-volumes.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/ollama-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

# 3. Wait for pods
kubectl get pods -n finsight-ai --watch

# 4. Setup port forwarding
kubectl port-forward -n finsight-ai svc/frontend-service 3000:3000 &
kubectl port-forward -n finsight-ai svc/backend-service 8000:8000 &
```

---

## Access Application

### URLs

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

## Useful Commands

### Check Status

```bash
# All resources
kubectl get all -n finsight-ai

# Pods with details
kubectl get pods -n finsight-ai -o wide

# Services
kubectl get svc -n finsight-ai

# Persistent volumes
kubectl get pvc -n finsight-ai
```

### View Logs

```bash
# Backend logs (live)
kubectl logs -n finsight-ai -l app=backend --tail=50 -f

# Frontend logs (live)
kubectl logs -n finsight-ai -l app=frontend --tail=50 -f

# Specific pod
kubectl logs -n finsight-ai <pod-name>
```

### Test Auto-scaling

```bash
# Install load testing tool
brew install hey

# Generate load
hey -z 30s -c 50 http://localhost:8000/health

# Watch pods scale up
kubectl get pods -n finsight-ai --watch

# Check HPA status
kubectl get hpa -n finsight-ai
```

### Update Deployment

```bash
# Rebuild and update backend
docker build -t finsight-backend:latest ./backend
kubectl rollout restart deployment backend -n finsight-ai

# Watch rollout
kubectl rollout status deployment backend -n finsight-ai
```

### Scale Manually

```bash
# Scale backend to 5 replicas
kubectl scale deployment backend -n finsight-ai --replicas=5

# Scale frontend to 3 replicas
kubectl scale deployment frontend -n finsight-ai --replicas=3

# Check scaling
kubectl get pods -n finsight-ai
```

---

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n finsight-ai

# View pod details
kubectl describe pod -n finsight-ai <pod-name>

# Check logs
kubectl logs -n finsight-ai <pod-name>

# Common issues:
# - Image pull errors: Rebuild images locally
# - Resource limits: Check Docker Desktop resource allocation
# - Config errors: Verify ConfigMaps and Secrets
```

### Port Forward Not Working

```bash
# Kill existing port forwards
pkill -f "kubectl port-forward"

# Re-establish
kubectl port-forward -n finsight-ai svc/frontend-service 3000:3000 &
kubectl port-forward -n finsight-ai svc/backend-service 8000:8000 &

# Verify
lsof -i :3000
lsof -i :8000
```

### Metrics Server Not Working

```bash
# Check metrics server
kubectl get pods -n kube-system | grep metrics

# Restart metrics server
kubectl rollout restart deployment metrics-server -n kube-system

# Wait and test
sleep 30
kubectl top nodes
kubectl top pods -n finsight-ai
```

---

## Cleanup

### Remove Deployment

```bash
# Delete everything in namespace
kubectl delete namespace finsight-ai

# Stop port forwards
pkill -f "kubectl port-forward"
```

### Keep Cluster, Remove App Only

```bash
# Delete manifests individually
kubectl delete -f k8s/frontend-deployment.yaml
kubectl delete -f k8s/backend-deployment.yaml
kubectl delete -f k8s/ollama-deployment.yaml
kubectl delete -f k8s/redis-deployment.yaml
kubectl delete -f k8s/persistent-volumes.yaml
kubectl delete -f k8s/configmap-secrets.yaml
kubectl delete -f k8s/namespace.yaml
```

### Disable Kubernetes

```bash
# Docker Desktop → Settings → Kubernetes → Disable Kubernetes
```

---

## Resource Requirements

### Minimum (for testing)

- **CPU:** 2 cores available
- **Memory:** 4GB available
- **Disk:** 20GB free

### Recommended (with Ollama)

- **CPU:** 4 cores available
- **Memory:** 8GB available
- **Disk:** 50GB free

**Configure in Docker Desktop:**
Settings → Resources → Advanced

---

## Next Steps

After successful local testing:

1. ✅ Test all API endpoints via http://localhost:8000/docs
2. ✅ Test frontend functionality via http://localhost:3000
3. ✅ Test auto-scaling with load
4. ✅ Test pod recovery (delete a pod and watch it recreate)
5. ✅ Test rolling updates
6. 📝 Document any issues found
7. 🚀 Ready for staging/production deployment

---

## Quick Reference

### Start Everything

```bash
./scripts/test-k8s-local.sh
```

### Stop Port Forwards

```bash
pkill -f "kubectl port-forward"
```

### Restart Backend

```bash
kubectl rollout restart deployment backend -n finsight-ai
```

### View All Logs

```bash
kubectl logs -n finsight-ai --all-containers=true --tail=20
```

### Delete Everything

```bash
kubectl delete namespace finsight-ai
```

---

**Need more control?** See the full guide: [LOCAL-KUBERNETES-SETUP.md](./LOCAL-KUBERNETES-SETUP.md)
