# Local Kubernetes Setup Guide

**Purpose:** Test Kubernetes manifests locally before deploying to production
**Date:** January 3, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Option 1: Docker Desktop (Recommended for macOS)](#option-1-docker-desktop-recommended-for-macos)
3. [Option 2: Minikube (Most Features)](#option-2-minikube-most-features)
4. [Option 3: Kind (Lightweight)](#option-3-kind-lightweight)
5. [Testing FinSight AI Manifests](#testing-finsight-ai-manifests)
6. [Troubleshooting](#troubleshooting)

---

## Overview

### Comparison of Local Kubernetes Options

| Feature | Docker Desktop | Minikube | Kind |
|---------|---------------|----------|------|
| Setup Time | 2 min | 5 min | 3 min |
| Resource Usage | Medium | Medium-High | Low |
| Production Similarity | Good | Excellent | Good |
| Multi-node Support | No | Yes | Yes |
| Add-ons | Limited | Extensive | Limited |
| **Recommended For** | **Quick testing** | **Full features** | **CI/CD** |

### Prerequisites

- macOS (as per your setup)
- Docker Desktop installed ✓
- 8GB RAM minimum
- 20GB free disk space

---

## Option 1: Docker Desktop (Recommended for macOS)

### Why Docker Desktop?
✅ Already installed
✅ Single-click setup
✅ No additional tools needed
✅ Good for quick testing

### Setup Steps

#### 1. Enable Kubernetes

```bash
# Open Docker Desktop settings
# Settings → Kubernetes → Enable Kubernetes → Apply & Restart
```

**Via GUI:**
1. Open Docker Desktop
2. Click Settings (⚙️ icon)
3. Go to "Kubernetes" tab
4. Check "Enable Kubernetes"
5. Click "Apply & Restart"
6. Wait 2-5 minutes for initialization

#### 2. Verify Installation

```bash
# Check kubectl is configured
kubectl version --client

# Check cluster info
kubectl cluster-info

# Check nodes
kubectl get nodes

# Expected output:
# NAME             STATUS   ROLES           AGE   VERSION
# docker-desktop   Ready    control-plane   1m    v1.28.2
```

#### 3. Install NGINX Ingress Controller

```bash
# Apply NGINX ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml

# Wait for deployment
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

# Verify
kubectl get pods -n ingress-nginx
```

#### 4. Install Metrics Server (for HPA)

```bash
# Download and modify metrics-server manifest
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Patch for local development (skip TLS verification)
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'

# Verify (wait 30 seconds)
kubectl top nodes
```

### Configuration for FinSight AI

```bash
# Update /etc/hosts for local DNS
sudo bash -c 'echo "127.0.0.1 finsight-ai.local api.finsight-ai.local" >> /etc/hosts'
```

---

## Option 2: Minikube (Most Features)

### Why Minikube?
✅ Most similar to production
✅ Extensive add-ons
✅ Multi-node support
✅ Multiple driver options

### Setup Steps

#### 1. Install Minikube

```bash
# Install via Homebrew
brew install minikube

# Or download directly
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-darwin-arm64
sudo install minikube-darwin-arm64 /usr/local/bin/minikube
```

#### 2. Start Minikube

```bash
# Start with Docker driver (recommended)
minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=50g

# Or with more resources for Ollama
minikube start --driver=docker --cpus=6 --memory=12288 --disk-size=100g

# Verify
kubectl get nodes
minikube status
```

#### 3. Enable Add-ons

```bash
# Enable essential add-ons
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable storage-provisioner
minikube addons enable dashboard

# Verify
minikube addons list
```

#### 4. Configure Docker Environment

```bash
# Use Minikube's Docker daemon (optional, for building images directly)
eval $(minikube docker-env)

# Now docker commands use Minikube's Docker
docker ps
```

#### 5. Get Minikube IP

```bash
# Get IP for accessing services
minikube ip

# Example output: 192.168.49.2
# Add to /etc/hosts
sudo bash -c 'echo "$(minikube ip) finsight-ai.local api.finsight-ai.local" >> /etc/hosts'
```

### Useful Minikube Commands

```bash
# Dashboard
minikube dashboard

# SSH into node
minikube ssh

# Stop cluster
minikube stop

# Delete cluster
minikube delete

# View logs
minikube logs

# Tunnel (for LoadBalancer services)
minikube tunnel
```

---

## Option 3: Kind (Lightweight)

### Why Kind?
✅ Very lightweight
✅ Fast startup
✅ Multi-node clusters
✅ Great for CI/CD

### Setup Steps

#### 1. Install Kind

```bash
# Install via Homebrew
brew install kind

# Or download binary
[ $(uname -m) = arm64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-darwin-arm64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
```

#### 2. Create Cluster

```bash
# Simple single-node cluster
kind create cluster --name finsight-ai

# Or multi-node cluster with config
cat <<EOF | kind create cluster --name finsight-ai --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
- role: worker
- role: worker
EOF

# Verify
kubectl cluster-info --context kind-finsight-ai
kubectl get nodes
```

#### 3. Install NGINX Ingress

```bash
# Install ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Wait for ready
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
```

#### 4. Load Docker Images (Important for Kind)

```bash
# Build images
docker build -t finsight-backend:latest ./backend
docker build -t finsight-frontend:latest ./frontend

# Load images into Kind cluster
kind load docker-image finsight-backend:latest --name finsight-ai
kind load docker-image finsight-frontend:latest --name finsight-ai

# Verify
docker exec -it finsight-ai-control-plane crictl images | grep finsight
```

### Useful Kind Commands

```bash
# List clusters
kind get clusters

# Delete cluster
kind delete cluster --name finsight-ai

# Export kubeconfig
kind export kubeconfig --name finsight-ai
```

---

## Testing FinSight AI Manifests

### Step 1: Build Docker Images

```bash
# Navigate to project root
cd /Users/bibekgupta/Documents/personal/bibek-portfolio/finsight-ai

# Build backend
docker build -t finsight-backend:latest ./backend

# Build frontend
docker build -t finsight-frontend:latest ./frontend

# Verify images
docker images | grep finsight
```

### Step 2: Load Images (Kind only)

```bash
# If using Kind, load images
kind load docker-image finsight-backend:latest --name finsight-ai
kind load docker-image finsight-frontend:latest --name finsight-ai

# For Docker Desktop/Minikube with eval $(minikube docker-env), rebuild images
```

### Step 3: Create Secrets

```bash
# Create production secret with actual password
kubectl create secret generic finsight-secrets \
  --from-literal=REDIS_PASSWORD=local-dev-password-123 \
  -n finsight-ai --dry-run=client -o yaml | kubectl apply -f -

# Or update existing secret in configmap-secrets.yaml
# Then apply: kubectl apply -f k8s/configmap-secrets.yaml
```

### Step 4: Deploy All Components

```bash
# Apply manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap-secrets.yaml
kubectl apply -f k8s/persistent-volumes.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/ollama-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=redis -n finsight-ai --timeout=120s
kubectl wait --for=condition=ready pod -l app=backend -n finsight-ai --timeout=180s
kubectl wait --for=condition=ready pod -l app=frontend -n finsight-ai --timeout=120s
```

### Step 5: Setup Local Ingress

```bash
# For local testing, modify ingress.yaml or create local version
cat > k8s/ingress-local.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: finsight-ingress
  namespace: finsight-ai
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: finsight-ai.local
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000
      - path: /docs
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 3000
EOF

# Apply local ingress
kubectl apply -f k8s/ingress-local.yaml
```

### Step 6: Verify Deployment

```bash
# Check all resources
kubectl get all -n finsight-ai

# Check pods status
kubectl get pods -n finsight-ai -o wide

# Check services
kubectl get svc -n finsight-ai

# Check ingress
kubectl get ingress -n finsight-ai

# Check PVCs
kubectl get pvc -n finsight-ai

# Check HPA (after metrics-server is running)
kubectl get hpa -n finsight-ai
```

### Step 7: Access Application

#### Option A: Via Ingress (Docker Desktop/Kind)

```bash
# Ensure /etc/hosts is configured
cat /etc/hosts | grep finsight-ai.local

# Access application
open http://finsight-ai.local
open http://finsight-ai.local/api/docs
```

#### Option B: Via Minikube Tunnel

```bash
# Start tunnel (keep this running in separate terminal)
minikube tunnel

# Access application
open http://finsight-ai.local
```

#### Option C: Port Forwarding (Quickest)

```bash
# Forward frontend
kubectl port-forward -n finsight-ai svc/frontend-service 3000:3000 &

# Forward backend
kubectl port-forward -n finsight-ai svc/backend-service 8000:8000 &

# Access
open http://localhost:3000
open http://localhost:8000/docs

# Stop forwarding
jobs  # List background jobs
kill %1 %2  # Kill jobs
```

### Step 8: Test Auto-scaling

```bash
# Generate load (install hey or apache bench)
brew install hey

# Load test backend
hey -z 30s -c 50 http://finsight-ai.local/api/health

# Watch HPA scale
kubectl get hpa -n finsight-ai --watch

# Watch pods scaling
kubectl get pods -n finsight-ai --watch
```

### Step 9: Check Logs

```bash
# Backend logs
kubectl logs -n finsight-ai -l app=backend --tail=50 -f

# Frontend logs
kubectl logs -n finsight-ai -l app=frontend --tail=50 -f

# Redis logs
kubectl logs -n finsight-ai -l app=redis --tail=50 -f

# All pods logs
kubectl logs -n finsight-ai --all-containers=true --tail=20
```

---

## Quick Test Script

Create a test script for automation:

```bash
# Create file: scripts/test-k8s-local.sh
cat > scripts/test-k8s-local.sh <<'EOF'
#!/bin/bash
set -e

echo "🚀 Testing FinSight AI on Local Kubernetes"

# Build images
echo "📦 Building Docker images..."
docker build -t finsight-backend:latest ./backend
docker build -t finsight-frontend:latest ./frontend

# Load to Kind if using Kind
if kubectl config current-context | grep -q "kind"; then
  echo "📥 Loading images to Kind..."
  kind load docker-image finsight-backend:latest
  kind load docker-image finsight-frontend:latest
fi

# Deploy
echo "🔧 Deploying to Kubernetes..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap-secrets.yaml
kubectl apply -f k8s/persistent-volumes.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/ollama-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

# Wait for deployments
echo "⏳ Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=redis -n finsight-ai --timeout=120s
kubectl wait --for=condition=ready pod -l app=backend -n finsight-ai --timeout=180s
kubectl wait --for=condition=ready pod -l app=frontend -n finsight-ai --timeout=120s

# Show status
echo "✅ Deployment complete!"
kubectl get all -n finsight-ai

# Setup port forwarding
echo "🌐 Setting up port forwarding..."
kubectl port-forward -n finsight-ai svc/frontend-service 3000:3000 &
kubectl port-forward -n finsight-ai svc/backend-service 8000:8000 &

echo ""
echo "🎉 FinSight AI is ready!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000/docs"
echo ""
echo "To stop port forwarding, run: pkill -f 'kubectl port-forward'"
EOF

chmod +x scripts/test-k8s-local.sh

# Run the script
./scripts/test-k8s-local.sh
```

---

## Troubleshooting

### Issue: Pods in CrashLoopBackOff

```bash
# Check pod logs
kubectl logs -n finsight-ai <pod-name>

# Describe pod for events
kubectl describe pod -n finsight-ai <pod-name>

# Common causes:
# 1. Image pull errors → Check image name and availability
# 2. Configuration errors → Check ConfigMaps and Secrets
# 3. Resource limits → Increase limits or reduce requests
```

### Issue: ImagePullBackOff (Kind)

```bash
# Kind doesn't have access to local Docker images
# Solution: Load images explicitly
kind load docker-image finsight-backend:latest --name finsight-ai
kind load docker-image finsight-frontend:latest --name finsight-ai

# Update deployment to use imagePullPolicy: IfNotPresent
kubectl patch deployment backend -n finsight-ai -p '{"spec":{"template":{"spec":{"containers":[{"name":"backend","imagePullPolicy":"IfNotPresent"}]}}}}'
```

### Issue: Ingress Not Working

```bash
# Check ingress controller is running
kubectl get pods -n ingress-nginx

# Check ingress resource
kubectl describe ingress -n finsight-ai

# Check service endpoints
kubectl get endpoints -n finsight-ai

# For Minikube, ensure tunnel is running
minikube tunnel
```

### Issue: HPA Not Scaling

```bash
# Check metrics-server
kubectl get deployment metrics-server -n kube-system

# Check if metrics are available
kubectl top nodes
kubectl top pods -n finsight-ai

# If metrics unavailable, restart metrics-server
kubectl rollout restart deployment metrics-server -n kube-system
```

### Issue: PVC Pending

```bash
# Check PVC status
kubectl get pvc -n finsight-ai

# Check storage classes
kubectl get storageclass

# For Docker Desktop/Minikube, default storage class should exist
# For Kind, may need to manually provision or use hostPath
```

### Issue: Services Not Accessible

```bash
# Check service endpoints
kubectl get endpoints -n finsight-ai

# Check if pods are ready
kubectl get pods -n finsight-ai

# Test internal connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n finsight-ai -- curl http://backend-service:8000/health
```

---

## Cleanup

### Remove All Resources

```bash
# Delete namespace (removes everything)
kubectl delete namespace finsight-ai

# Or delete individually
kubectl delete -f k8s/ingress-local.yaml
kubectl delete -f k8s/frontend-deployment.yaml
kubectl delete -f k8s/backend-deployment.yaml
kubectl delete -f k8s/ollama-deployment.yaml
kubectl delete -f k8s/redis-deployment.yaml
kubectl delete -f k8s/persistent-volumes.yaml
kubectl delete -f k8s/configmap-secrets.yaml
kubectl delete -f k8s/namespace.yaml
```

### Stop/Delete Cluster

```bash
# Docker Desktop
# Settings → Kubernetes → Disable Kubernetes

# Minikube
minikube stop
minikube delete

# Kind
kind delete cluster --name finsight-ai
```

---

## Best Practices for Local Testing

1. **Resource Management**
   - Start with minimal resources
   - Scale up if needed for Ollama testing
   - Monitor Docker Desktop resource usage

2. **Image Management**
   - Tag images with version numbers for testing different builds
   - Use `imagePullPolicy: IfNotPresent` for local development
   - Clean up unused images regularly

3. **Configuration**
   - Use separate ConfigMaps for local vs production
   - Test with realistic data volumes
   - Simulate production scenarios

4. **Workflow**
   - Test individual components first
   - Then test integration
   - Finally test scaling and failure scenarios

5. **Persistence**
   - Be aware local PVCs persist between deployments
   - Clean up data when testing migrations
   - Backup important test data

---

## Next Steps

After successful local testing:

1. ✅ Validate all manifests work locally
2. 🔄 Test deployment updates and rollbacks
3. 🔄 Test auto-scaling behavior
4. 🔄 Test failure scenarios (pod crashes, node failures)
5. 📝 Document any environment-specific configurations
6. 🚀 Deploy to staging/production cluster

---

## Additional Resources

- [Docker Desktop Kubernetes](https://docs.docker.com/desktop/kubernetes/)
- [Minikube Documentation](https://minikube.sigs.k8s.io/docs/)
- [Kind Quick Start](https://kind.sigs.k8s.io/docs/user/quick-start/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
