# Local Kubernetes Testing - Setup Summary

**Date:** January 3, 2026
**Purpose:** Enable local testing of Kubernetes manifests before production deployment

---

## What Was Created

### 1. Comprehensive Setup Guide
**File:** [docs/deployment/LOCAL-KUBERNETES-SETUP.md](../docs/deployment/LOCAL-KUBERNETES-SETUP.md)

**Covers 3 options:**
- **Docker Desktop** - Recommended for macOS, simplest setup (2 min)
- **Minikube** - Most features, closest to production (5 min)
- **Kind** - Lightweight, great for CI/CD (3 min)

**Includes:**
- Step-by-step installation for each option
- Testing FinSight AI manifests
- Troubleshooting common issues
- Cleanup procedures
- Best practices

### 2. Quick Start Guide
**File:** [docs/deployment/QUICKSTART-K8S.md](../docs/deployment/QUICKSTART-K8S.md)

**Focus:** Docker Desktop (fastest path)

**Covers:**
- 2-minute setup instructions
- Automated deployment script usage
- Manual deployment steps
- Useful kubectl commands
- Quick troubleshooting

### 3. Automated Test Script
**File:** [scripts/test-k8s-local.sh](../scripts/test-k8s-local.sh)

**Features:**
- ✅ Detects current Kubernetes context (Docker Desktop/Minikube/Kind)
- ✅ Builds Docker images locally
- ✅ Loads images to Kind if needed
- ✅ Deploys all Kubernetes manifests in order
- ✅ Waits for pods to be ready
- ✅ Creates local ingress configuration
- ✅ Sets up port forwarding automatically
- ✅ Tests connectivity
- ✅ Provides status and useful commands
- ✅ Colored output for better UX

**Usage:**
```bash
chmod +x scripts/test-k8s-local.sh
./scripts/test-k8s-local.sh
```

---

## Recommended Setup (Docker Desktop)

### Why Docker Desktop?
- ✅ You already have Docker installed
- ✅ Single-click Kubernetes enablement
- ✅ No additional tools needed
- ✅ Perfect for quick testing
- ✅ Good resource management

### Setup Steps

1. **Enable Kubernetes**
   - Open Docker Desktop
   - Settings → Kubernetes → Enable Kubernetes
   - Apply & Restart (wait 2-5 min)

2. **Install NGINX Ingress**
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml
   ```

3. **Install Metrics Server**
   ```bash
   kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
   kubectl patch deployment metrics-server -n kube-system --type='json' \
     -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'
   ```

4. **Run Test Script**
   ```bash
   ./scripts/test-k8s-local.sh
   ```

5. **Access Application**
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs

---

## What Gets Deployed

The test script deploys the complete FinSight AI stack:

### Services Deployed
1. **Redis** (1 pod)
   - Cache and session storage
   - 5Gi persistent volume
   - Password-protected

2. **Ollama** (1 pod)
   - Local LLM inference
   - 50Gi persistent volume for models
   - Optional GPU support

3. **Backend** (3 replicas)
   - FastAPI application
   - 20Gi persistent volume
   - Auto-scales: 2-10 replicas
   - Health checks configured

4. **Frontend** (2 replicas)
   - Next.js application
   - Auto-scales: 2-5 replicas
   - Health checks configured

### Infrastructure
- **Namespace:** finsight-ai
- **ConfigMaps:** 2 (backend-config, frontend-config)
- **Secrets:** 1 (finsight-secrets)
- **PVCs:** 3 (total 75Gi)
- **Services:** 4 (ClusterIP)
- **Ingress:** 1 (local configuration)
- **HPA:** 2 (backend, frontend)

---

## Testing Workflow

### 1. Deploy
```bash
./scripts/test-k8s-local.sh
```

### 2. Verify
```bash
kubectl get all -n finsight-ai
kubectl get pvc -n finsight-ai
kubectl top pods -n finsight-ai
```

### 3. Test Application
- Visit http://localhost:3000
- Upload a transaction file
- Check fraud detection results
- Test batch processing
- Review API docs at http://localhost:8000/docs

### 4. Test Auto-scaling
```bash
# Install load tester
brew install hey

# Generate load
hey -z 30s -c 50 http://localhost:8000/health

# Watch scaling
kubectl get hpa -n finsight-ai --watch
kubectl get pods -n finsight-ai --watch
```

### 5. Test Rolling Updates
```bash
# Make code changes
# Rebuild image
docker build -t finsight-backend:latest ./backend

# Rolling update
kubectl rollout restart deployment backend -n finsight-ai

# Watch rollout
kubectl rollout status deployment backend -n finsight-ai
```

### 6. Test Pod Recovery
```bash
# Delete a pod
kubectl delete pod -n finsight-ai -l app=backend --limit=1

# Watch automatic recreation
kubectl get pods -n finsight-ai --watch
```

### 7. View Logs
```bash
# Backend logs
kubectl logs -n finsight-ai -l app=backend --tail=50 -f

# Frontend logs
kubectl logs -n finsight-ai -l app=frontend --tail=50 -f

# All logs
kubectl logs -n finsight-ai --all-containers=true --tail=20
```

---

## Common Testing Scenarios

### Test 1: Basic Functionality
```bash
# Deploy
./scripts/test-k8s-local.sh

# Access frontend
open http://localhost:3000

# Test API
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
```

### Test 2: Configuration Changes
```bash
# Edit ConfigMap
kubectl edit configmap backend-config -n finsight-ai

# Restart to pick up changes
kubectl rollout restart deployment backend -n finsight-ai
```

### Test 3: Scaling Behavior
```bash
# Manual scale up
kubectl scale deployment backend -n finsight-ai --replicas=5

# Check status
kubectl get pods -n finsight-ai

# Scale down
kubectl scale deployment backend -n finsight-ai --replicas=2
```

### Test 4: Persistent Storage
```bash
# Check PVCs
kubectl get pvc -n finsight-ai

# Exec into backend pod
kubectl exec -it -n finsight-ai deployment/backend -- /bin/bash

# Check mounted volumes
ls -la /app/data
```

### Test 5: Network Connectivity
```bash
# Test internal DNS
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n finsight-ai \
  -- curl http://backend-service:8000/health

# Test Redis connection
kubectl run -it --rm debug --image=redis:7-alpine --restart=Never -n finsight-ai \
  -- redis-cli -h redis-service ping
```

---

## Cleanup

### Quick Cleanup
```bash
# Delete namespace (removes everything)
kubectl delete namespace finsight-ai

# Stop port forwards
pkill -f "kubectl port-forward"
```

### Keep Cluster, Remove App
```bash
# Delete deployments only
kubectl delete -f k8s/frontend-deployment.yaml
kubectl delete -f k8s/backend-deployment.yaml
kubectl delete -f k8s/ollama-deployment.yaml
kubectl delete -f k8s/redis-deployment.yaml

# PVCs will persist for data retention
```

### Full Reset
```bash
# Delete everything including PVCs
kubectl delete namespace finsight-ai

# Or disable Kubernetes in Docker Desktop
# Settings → Kubernetes → Disable Kubernetes
```

---

## Resource Requirements

### Development Testing
- **CPU:** 2 cores
- **Memory:** 4GB
- **Disk:** 20GB

### Full Testing (with Ollama)
- **CPU:** 4 cores
- **Memory:** 8GB
- **Disk:** 50GB

**Configure in Docker Desktop:**
Settings → Resources → Advanced

---

## Troubleshooting Quick Reference

### Pods Not Starting
```bash
kubectl get pods -n finsight-ai
kubectl describe pod -n finsight-ai <pod-name>
kubectl logs -n finsight-ai <pod-name>
```

### Port Forward Issues
```bash
pkill -f "kubectl port-forward"
kubectl port-forward -n finsight-ai svc/frontend-service 3000:3000 &
kubectl port-forward -n finsight-ai svc/backend-service 8000:8000 &
```

### Metrics Not Available
```bash
kubectl get pods -n kube-system | grep metrics
kubectl rollout restart deployment metrics-server -n kube-system
sleep 30 && kubectl top nodes
```

### Image Pull Errors
```bash
# Rebuild images
docker build -t finsight-backend:latest ./backend
docker build -t finsight-frontend:latest ./frontend

# For Kind, reload images
kind load docker-image finsight-backend:latest
kind load docker-image finsight-frontend:latest
```

---

## Next Steps

After successful local testing:

1. ✅ **Validate All Features**
   - Test all API endpoints
   - Test frontend functionality
   - Verify file uploads
   - Check fraud detection results

2. ✅ **Performance Testing**
   - Load test with `hey` or `k6`
   - Monitor resource usage
   - Test auto-scaling behavior
   - Verify response times

3. ✅ **Reliability Testing**
   - Test pod recovery (delete pods)
   - Test rolling updates
   - Test rollback scenarios
   - Test configuration changes

4. ✅ **Document Findings**
   - Note any issues found
   - Document required resource limits
   - Record scaling thresholds
   - Update deployment guides

5. 🚀 **Production Deployment**
   - Deploy to staging cluster
   - Run full test suite
   - Deploy to production
   - Monitor and iterate

---

## Additional Resources

### Documentation
- [Full Local Setup Guide](../docs/deployment/LOCAL-KUBERNETES-SETUP.md)
- [Quick Start Guide](../docs/deployment/QUICKSTART-K8S.md)
- [Docker & Kubernetes Guide](../docs/deployment/DOCKER-KUBERNETES-GUIDE.md)
- [Kubernetes README](../k8s/README.md)

### External Resources
- [Docker Desktop Kubernetes](https://docs.docker.com/desktop/kubernetes/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)

---

## Summary

You now have:
- ✅ 3 local Kubernetes setup options documented
- ✅ Automated deployment script
- ✅ Quick start guide for fastest path
- ✅ Comprehensive testing procedures
- ✅ Troubleshooting guides
- ✅ Cleanup procedures

**Ready to test?**
```bash
./scripts/test-k8s-local.sh
```
