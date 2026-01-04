#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Testing FinSight AI on Local Kubernetes${NC}"
echo ""

# Detect current context
CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "none")
echo -e "${BLUE}📍 Current Kubernetes context: ${YELLOW}$CURRENT_CONTEXT${NC}"

if [ "$CURRENT_CONTEXT" = "none" ]; then
  echo -e "${RED}❌ No Kubernetes cluster found!${NC}"
  echo -e "${YELLOW}Please set up a local cluster first:${NC}"
  echo "  - Docker Desktop: Enable Kubernetes in settings"
  echo "  - Minikube: minikube start"
  echo "  - Kind: kind create cluster --name finsight-ai"
  exit 1
fi

# Build images
echo ""
echo -e "${BLUE}📦 Building Docker images...${NC}"
docker build -t finsight-backend:latest ./backend
docker build -t finsight-frontend:latest ./frontend

# Load to Kind if using Kind
if echo "$CURRENT_CONTEXT" | grep -q "kind"; then
  echo ""
  echo -e "${BLUE}📥 Loading images to Kind cluster...${NC}"
  kind load docker-image finsight-backend:latest --name finsight-ai 2>/dev/null || kind load docker-image finsight-backend:latest
  kind load docker-image finsight-frontend:latest --name finsight-ai 2>/dev/null || kind load docker-image finsight-frontend:latest
  echo -e "${GREEN}✓ Images loaded to Kind${NC}"
fi

# Deploy manifests
echo ""
echo -e "${BLUE}🔧 Deploying to Kubernetes...${NC}"

echo -e "${YELLOW}Creating namespace...${NC}"
kubectl apply -f k8s/namespace.yaml

echo -e "${YELLOW}Creating ConfigMaps and Secrets...${NC}"
kubectl apply -f k8s/configmap-secrets.yaml

echo -e "${YELLOW}Creating Persistent Volume Claims...${NC}"
kubectl apply -f k8s/persistent-volumes.yaml

echo -e "${YELLOW}Deploying Redis...${NC}"
kubectl apply -f k8s/redis-deployment.yaml

echo -e "${YELLOW}Deploying Ollama...${NC}"
kubectl apply -f k8s/ollama-deployment.yaml

echo -e "${YELLOW}Deploying Backend...${NC}"
kubectl apply -f k8s/backend-deployment.yaml

echo -e "${YELLOW}Deploying Frontend...${NC}"
kubectl apply -f k8s/frontend-deployment.yaml

# Create local ingress if doesn't exist
if [ ! -f k8s/ingress-local.yaml ]; then
  echo -e "${YELLOW}Creating local ingress configuration...${NC}"
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
      - path: /health
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
fi

kubectl apply -f k8s/ingress-local.yaml 2>/dev/null || echo -e "${YELLOW}Note: Ingress may require NGINX controller${NC}"

# Wait for deployments
echo ""
echo -e "${BLUE}⏳ Waiting for pods to be ready...${NC}"

echo -e "${YELLOW}Waiting for Redis...${NC}"
kubectl wait --for=condition=ready pod -l app=redis -n finsight-ai --timeout=120s 2>/dev/null || echo -e "${RED}Redis timeout (may still be starting)${NC}"

echo -e "${YELLOW}Waiting for Backend...${NC}"
kubectl wait --for=condition=ready pod -l app=backend -n finsight-ai --timeout=180s 2>/dev/null || echo -e "${RED}Backend timeout (may still be starting)${NC}"

echo -e "${YELLOW}Waiting for Frontend...${NC}"
kubectl wait --for=condition=ready pod -l app=frontend -n finsight-ai --timeout=120s 2>/dev/null || echo -e "${RED}Frontend timeout (may still be starting)${NC}"

# Show status
echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${BLUE}📊 Cluster Status:${NC}"
kubectl get all -n finsight-ai

echo ""
echo -e "${BLUE}💾 Storage Status:${NC}"
kubectl get pvc -n finsight-ai

# Kill any existing port forwards
echo ""
echo -e "${YELLOW}Cleaning up existing port forwards...${NC}"
pkill -f "kubectl port-forward.*finsight-ai" 2>/dev/null || true
sleep 2

# Setup port forwarding
echo -e "${BLUE}🌐 Setting up port forwarding...${NC}"
kubectl port-forward -n finsight-ai svc/frontend-service 3000:3000 > /dev/null 2>&1 &
FRONTEND_PID=$!
kubectl port-forward -n finsight-ai svc/backend-service 8000:8000 > /dev/null 2>&1 &
BACKEND_PID=$!

# Wait a moment for port forwards to establish
sleep 3

# Test connectivity
echo ""
echo -e "${BLUE}🧪 Testing connectivity...${NC}"
if curl -s http://localhost:8000/health > /dev/null; then
  echo -e "${GREEN}✓ Backend is responding${NC}"
else
  echo -e "${RED}✗ Backend not responding yet (may still be starting)${NC}"
fi

if curl -s http://localhost:3000 > /dev/null; then
  echo -e "${GREEN}✓ Frontend is responding${NC}"
else
  echo -e "${RED}✗ Frontend not responding yet (may still be starting)${NC}"
fi

echo ""
echo -e "${GREEN}🎉 FinSight AI is ready for testing!${NC}"
echo ""
echo -e "${BLUE}Access URLs:${NC}"
echo -e "  ${GREEN}Frontend:${NC}     http://localhost:3000"
echo -e "  ${GREEN}Backend API:${NC}  http://localhost:8000"
echo -e "  ${GREEN}API Docs:${NC}     http://localhost:8000/docs"
echo -e "  ${GREEN}Health:${NC}       http://localhost:8000/health"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo -e "  View logs:        ${YELLOW}kubectl logs -n finsight-ai -l app=backend --tail=50 -f${NC}"
echo -e "  Check pods:       ${YELLOW}kubectl get pods -n finsight-ai${NC}"
echo -e "  Check services:   ${YELLOW}kubectl get svc -n finsight-ai${NC}"
echo -e "  Restart backend:  ${YELLOW}kubectl rollout restart deployment backend -n finsight-ai${NC}"
echo -e "  Scale backend:    ${YELLOW}kubectl scale deployment backend -n finsight-ai --replicas=5${NC}"
echo ""
echo -e "${BLUE}To stop:${NC}"
echo -e "  Port forwarding:  ${YELLOW}pkill -f 'kubectl port-forward'${NC}"
echo -e "  Delete deployment: ${YELLOW}kubectl delete namespace finsight-ai${NC}"
echo ""
echo -e "${YELLOW}Port forwarding is running in background (PIDs: $FRONTEND_PID, $BACKEND_PID)${NC}"
echo -e "${YELLOW}Press Ctrl+C or close terminal to stop${NC}"
echo ""

# Keep script running to maintain port forwards
wait
