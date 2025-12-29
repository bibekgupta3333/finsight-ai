# Deployment Guide - FinSight AI

## Table of Contents
1. [Local Development Setup](#local-development-setup)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [AWS Deployment with Terraform](#aws-deployment-with-terraform)
5. [Render Deployment (Free Tier)](#render-deployment-free-tier)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **CPU:** 4+ cores (8+ recommended)
- **RAM:** 8GB minimum (16GB+ recommended for Ollama)
- **Storage:** 20GB+ free space
- **OS:** Linux, macOS, or Windows with WSL2

### Required Software
- Docker Desktop (latest version)
- Node.js 18+ and npm/pnpm
- Python 3.11+
- Git
- kubectl (for Kubernetes)
- Terraform (for AWS deployment)
- Helm (for Kubernetes package management)
- AWS CLI (for AWS deployment)

---

## Local Development Setup

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/finsight-ai.git
cd finsight-ai

# Check the structure
tree -L 2
```

Expected structure:
```
finsight-ai/
├── backend/
├── frontend/
├── docker/
├── kubernetes/
├── terraform/
├── docs/
├── package.json (root)
├── turbo.json
└── docker-compose.yml
```

### Step 2: Install Dependencies

#### Install Root Dependencies (Turborepo)
```bash
# Using pnpm (recommended)
npm install -g pnpm
pnpm install

# Or using npm
npm install
```

#### Install Backend Dependencies
```bash
cd backend
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

cd ..
```

#### Install Frontend Dependencies
```bash
cd frontend
pnpm install
cd ..
```

### Step 3: Setup Environment Variables

#### Backend `.env`
```bash
cd backend
cp .env.example .env
```

Edit `backend/.env`:
```env
# Application
APP_NAME=FinSight AI
APP_ENV=development
DEBUG=True
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2:7b
OLLAMA_TIMEOUT=120

# Vector Store
CHROMA_PERSIST_DIR=./data/chromadb
CHROMA_COLLECTION_PREFIX=finsight_

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# File Upload
UPLOAD_DIR=./data/uploads
MAX_FILE_SIZE_MB=10
ALLOWED_FILE_TYPES=pdf,png,jpg,jpeg

# Security
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

#### Frontend `.env.local`
```bash
cd ../frontend
cp .env.example .env.local
```

Edit `frontend/.env.local`:
```env
# API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Environment
NEXT_PUBLIC_ENV=development

# Features
NEXT_PUBLIC_ENABLE_ANALYTICS=false
```

### Step 4: Setup Ollama

#### Install Ollama
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download from https://ollama.com/download
```

#### Start Ollama Service
```bash
# Start Ollama server
ollama serve

# In another terminal, pull the model
ollama pull llama2:7b

# Or use a smaller model for testing
ollama pull mistral:7b
```

#### Verify Ollama
```bash
# Test the model
ollama run llama2:7b "Hello, how are you?"
```

### Step 5: Initialize Vector Store

```bash
cd backend

# Run initialization script
python scripts/init_vector_store.py

# Seed default categories
python scripts/seed_categories.py
```

### Step 6: Start Development Servers

#### Option 1: Using Turborepo (Recommended)
```bash
# From root directory
pnpm dev
```

This starts both backend and frontend concurrently.

#### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
pnpm dev
```

**Terminal 3 - Ollama (if not running):**
```bash
ollama serve
```

### Step 7: Verify Setup

1. **Backend API:** http://localhost:8000/docs
2. **Frontend:** http://localhost:3000
3. **Ollama:** http://localhost:11434

Test endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Ollama status
curl http://localhost:11434/api/version
```

---

## Docker Deployment

### Step 1: Build Docker Images

#### Backend Dockerfile
Create `backend/Dockerfile`:
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /app/data/chromadb /app/data/uploads

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Frontend Dockerfile
Create `frontend/Dockerfile`:
```dockerfile
# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY pnpm-lock.yaml ./

# Install dependencies
RUN npm install -g pnpm
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build application
RUN pnpm build

# Production stage
FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV production

# Copy built application
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
```

### Step 2: Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  # Ollama Service
  ollama:
    image: ollama/ollama:latest
    container_name: finsight-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/version"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Backend Service
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: finsight-backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - backend_data:/app/data
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - CHROMA_PERSIST_DIR=/app/data/chromadb
      - UPLOAD_DIR=/app/data/uploads
    depends_on:
      - ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Frontend Service
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: finsight-frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  ollama_data:
  backend_data:
```

### Step 3: Run with Docker Compose

```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Step 4: Initialize Ollama Model

```bash
# Pull model into Ollama container
docker exec -it finsight-ollama ollama pull llama2:7b

# Verify
docker exec -it finsight-ollama ollama list
```

---

## Kubernetes Deployment

### Step 1: Setup Kubernetes Cluster

#### Local (Minikube)
```bash
# Install minikube
brew install minikube

# Start cluster
minikube start --cpus=4 --memory=8192 --disk-size=30g

# Enable addons
minikube addons enable ingress
minikube addons enable metrics-server
```

#### Production (AWS EKS - see Terraform section)

### Step 2: Create Namespace

```bash
kubectl create namespace finsight-ai
kubectl config set-context --current --namespace=finsight-ai
```

### Step 3: Create Kubernetes Manifests

#### ConfigMap
Create `kubernetes/configmap.yaml`:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: finsight-config
  namespace: finsight-ai
data:
  OLLAMA_BASE_URL: "http://ollama-service:11434"
  OLLAMA_MODEL: "llama2:7b"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  NEXT_PUBLIC_API_URL: "http://backend-service:8000"
```

#### Secrets
Create `kubernetes/secrets.yaml`:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: finsight-secrets
  namespace: finsight-ai
type: Opaque
stringData:
  SECRET_KEY: "your-secret-key-change-in-production"
  # Add other secrets
```

#### Persistent Volumes
Create `kubernetes/pvc.yaml`:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ollama-data-pvc
  namespace: finsight-ai
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: backend-data-pvc
  namespace: finsight-ai
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

#### Ollama Deployment
Create `kubernetes/ollama-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
  namespace: finsight-ai
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama
  template:
    metadata:
      labels:
        app: ollama
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        env:
        - name: OLLAMA_HOST
          value: "0.0.0.0:11434"
        volumeMounts:
        - name: ollama-data
          mountPath: /root/.ollama
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
      volumes:
      - name: ollama-data
        persistentVolumeClaim:
          claimName: ollama-data-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: ollama-service
  namespace: finsight-ai
spec:
  selector:
    app: ollama
  ports:
  - port: 11434
    targetPort: 11434
  type: ClusterIP
```

#### Backend Deployment
Create `kubernetes/backend-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: finsight-ai
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/finsight-backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: finsight-config
        - secretRef:
            name: finsight-secrets
        volumeMounts:
        - name: backend-data
          mountPath: /app/data
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: backend-data
        persistentVolumeClaim:
          claimName: backend-data-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: finsight-ai
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

#### Frontend Deployment
Create `kubernetes/frontend-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: finsight-ai
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: your-registry/finsight-frontend:latest
        ports:
        - containerPort: 3000
        envFrom:
        - configMapRef:
            name: finsight-config
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: finsight-ai
spec:
  selector:
    app: frontend
  ports:
  - port: 3000
    targetPort: 3000
  type: LoadBalancer
```

#### Ingress
Create `kubernetes/ingress.yaml`:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: finsight-ingress
  namespace: finsight-ai
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - finsight.yourdomain.com
    secretName: finsight-tls
  rules:
  - host: finsight.yourdomain.com
    http:
      paths:
      - path: /api
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
```

### Step 4: Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f kubernetes/

# Check deployment status
kubectl get pods -n finsight-ai
kubectl get services -n finsight-ai

# View logs
kubectl logs -f deployment/backend -n finsight-ai
kubectl logs -f deployment/frontend -n finsight-ai

# Initialize Ollama model
kubectl exec -it deployment/ollama -n finsight-ai -- ollama pull llama2:7b
```

### Step 5: Helm Chart (Optional)

Create Helm chart for easier management:

```bash
# Create Helm chart
helm create finsight-ai-chart

# Package chart
helm package finsight-ai-chart

# Install chart
helm install finsight ./finsight-ai-chart \
  --namespace finsight-ai \
  --create-namespace \
  --values values.yaml

# Upgrade
helm upgrade finsight ./finsight-ai-chart --namespace finsight-ai

# Uninstall
helm uninstall finsight --namespace finsight-ai
```

---

## AWS Deployment with Terraform

### Step 1: Setup AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Verify credentials
aws sts get-caller-identity
```

### Step 2: Terraform Structure

```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── provider.tf
├── modules/
│   ├── vpc/
│   ├── eks/
│   ├── rds/
│   └── s3/
└── environments/
    ├── dev/
    └── prod/
```

### Step 3: Main Terraform Configuration

Create `terraform/main.tf`:
```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }

  backend "s3" {
    bucket = "finsight-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
    dynamodb_table = "terraform-state-lock"
  }
}

# Provider configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "FinSight AI"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  vpc_name             = "${var.project_name}-vpc"
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

# EKS Cluster Module
module "eks" {
  source = "./modules/eks"

  cluster_name    = "${var.project_name}-cluster"
  cluster_version = var.eks_cluster_version
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnet_ids

  node_groups = {
    general = {
      desired_size = 2
      min_size     = 1
      max_size     = 4
      instance_types = ["t3.medium"]
    }
    compute = {
      desired_size = 1
      min_size     = 0
      max_size     = 3
      instance_types = ["t3.large"]
    }
  }
}

# S3 Bucket for file storage
module "s3" {
  source = "./modules/s3"

  bucket_name = "${var.project_name}-uploads"
  environment = var.environment
}

# RDS Database (Optional)
# module "rds" {
#   source = "./modules/rds"
#
#   db_name     = var.db_name
#   db_username = var.db_username
#   db_password = var.db_password
#   vpc_id      = module.vpc.vpc_id
#   subnet_ids  = module.vpc.private_subnet_ids
# }
```

Create `terraform/variables.tf`:
```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "finsight-ai"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "eks_cluster_version" {
  description = "EKS cluster version"
  type        = string
  default     = "1.28"
}
```

### Step 4: Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -out=tfplan

# Apply deployment
terraform apply tfplan

# Get outputs
terraform output

# Destroy (when needed)
terraform destroy
```

### Step 5: Configure kubectl for EKS

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --region us-east-1 \
  --name finsight-ai-cluster

# Verify connection
kubectl get nodes
```

### Step 6: Deploy Application to EKS

```bash
# Apply Kubernetes manifests
kubectl apply -f kubernetes/

# Or use Helm
helm install finsight ./helm/finsight-ai-chart \
  --namespace finsight-ai \
  --create-namespace
```

---

## Render Deployment (Free Tier)

### Step 1: Prepare for Render

#### Backend (Web Service)

Create `render.yaml`:
```yaml
services:
  # Backend API
  - type: web
    name: finsight-backend
    env: python
    region: oregon
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: OLLAMA_BASE_URL
        value: https://your-ollama-service.onrender.com
      - key: SECRET_KEY
        generateValue: true
      - key: CHROMA_PERSIST_DIR
        value: /opt/render/project/data/chromadb
    autoDeploy: false

  # Frontend
  - type: web
    name: finsight-frontend
    env: node
    region: oregon
    plan: free
    buildCommand: npm install && npm run build
    startCommand: npm start
    envVars:
      - key: NODE_VERSION
        value: 18.17.0
      - key: NEXT_PUBLIC_API_URL
        value: https://finsight-backend.onrender.com
    autoDeploy: false

  # Ollama Service (Requires paid plan for GPU)
  # - type: web
  #   name: finsight-ollama
  #   env: docker
  #   plan: starter
  #   dockerfilePath: ./docker/Dockerfile.ollama
```

### Step 2: Deploy to Render

```bash
# Option 1: Via Render Dashboard
# 1. Go to https://dashboard.render.com
# 2. Click "New +" -> "Blueprint"
# 3. Connect your GitHub repository
# 4. Render will detect render.yaml and deploy

# Option 2: Via CLI
render-cli deploy
```

### Step 3: Limitations & Workarounds

**Free Tier Limitations:**
- Services spin down after 15 minutes of inactivity
- Limited to 750 hours/month
- No GPU support (Ollama won't work well)

**Workarounds:**
1. **Use External Ollama:**
   - Deploy Ollama on a separate service with GPU
   - Use Replicate API (paid)
   - Use OpenAI API (fallback)

2. **Keep-Alive:**
   ```javascript
   // Frontend keep-alive
   setInterval(() => {
     fetch('https://your-backend.onrender.com/health');
   }, 600000); // Every 10 minutes
   ```

---

## Monitoring & Maintenance

### Prometheus & Grafana Setup

```bash
# Add Prometheus Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Default credentials: admin / prom-operator
```

### Application Monitoring

```python
# backend/app/middleware/metrics.py
from prometheus_client import Counter, Histogram
import time

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)
```

### Logging

```bash
# View logs
kubectl logs -f deployment/backend -n finsight-ai --tail=100

# Aggregate logs with Loki (optional)
helm install loki grafana/loki-stack \
  --namespace monitoring
```

---

## Troubleshooting

### Common Issues

#### 1. Ollama Model Not Loading

```bash
# Check Ollama service
kubectl exec -it deployment/ollama -n finsight-ai -- ollama list

# Pull model manually
kubectl exec -it deployment/ollama -n finsight-ai -- ollama pull llama2:7b

# Check logs
kubectl logs deployment/ollama -n finsight-ai
```

#### 2. Backend Can't Connect to Vector Store

```bash
# Check PVC
kubectl get pvc -n finsight-ai

# Check volume mounts
kubectl describe pod <backend-pod> -n finsight-ai

# Initialize vector store
kubectl exec -it <backend-pod> -n finsight-ai -- python scripts/init_vector_store.py
```

#### 3. Frontend Can't Reach Backend

```bash
# Check service
kubectl get svc -n finsight-ai

# Port forward for testing
kubectl port-forward svc/backend-service 8000:8000 -n finsight-ai

# Check environment variables
kubectl exec -it <frontend-pod> -n finsight-ai -- env | grep API
```

#### 4. High Memory Usage

```bash
# Check resource usage
kubectl top pods -n finsight-ai

# Adjust resource limits in deployment yaml
# Scale down replicas
kubectl scale deployment/backend --replicas=1 -n finsight-ai
```

### Health Checks

```bash
# Create health check script
cat > healthcheck.sh << 'EOF'
#!/bin/bash

echo "🔍 Checking FinSight AI Services..."

# Check backend
if curl -s http://localhost:8000/health | grep -q "ok"; then
    echo "✅ Backend: Healthy"
else
    echo "❌ Backend: Unhealthy"
fi

# Check Ollama
if curl -s http://localhost:11434/api/version | grep -q "version"; then
    echo "✅ Ollama: Healthy"
else
    echo "❌ Ollama: Unhealthy"
fi

# Check frontend
if curl -s http://localhost:3000 | grep -q "FinSight"; then
    echo "✅ Frontend: Healthy"
else
    echo "❌ Frontend: Unhealthy"
fi
EOF

chmod +x healthcheck.sh
./healthcheck.sh
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] All environment variables configured
- [ ] Secrets properly set
- [ ] Database/Vector store initialized
- [ ] Ollama model downloaded
- [ ] SSL certificates obtained (production)
- [ ] Domain DNS configured
- [ ] Backup strategy in place

### Post-Deployment
- [ ] Health checks passing
- [ ] Monitoring configured
- [ ] Logging working
- [ ] Alerts configured
- [ ] Load testing completed
- [ ] Security audit done
- [ ] Documentation updated

### Rollback Plan
```bash
# Kubernetes rollback
kubectl rollout undo deployment/backend -n finsight-ai

# Helm rollback
helm rollback finsight -n finsight-ai

# Terraform rollback
terraform apply -var-file=previous.tfvars
```

---

**Document Version:** 1.0
**Last Updated:** December 26, 2025
**Status:** Initial Guide
