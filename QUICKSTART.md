# Quick Start Guide - FinSight AI

Get up and running with FinSight AI in 15 minutes! ⚡

---

## 📋 Prerequisites Checklist

Before you begin, make sure you have:

- [ ] **Node.js 18+** - `node --version`
- [ ] **Python 3.11+** - `python --version`
- [ ] **pnpm** - `npm install -g pnpm`
- [ ] **Docker Desktop** - Running and accessible
- [ ] **Git** - For version control
- [ ] **8GB+ RAM** - Minimum for running Ollama

---

## 🚀 Option 1: Docker (Recommended for Quick Start)

**Fastest way to get started - everything runs in containers!**

### Step 1: Clone & Navigate
```bash
git clone https://github.com/yourusername/finsight-ai.git
cd finsight-ai
```

### Step 2: Configure Environment
```bash
# Backend environment
cp backend/.env.example backend/.env

# Frontend environment
cp frontend/.env.example frontend/.env.local
```

### Step 3: Start Everything
```bash
# Start all services
docker-compose up -d

# Pull the Ollama model (this may take a few minutes)
docker exec -it finsight-ollama ollama pull llama2:7b
```

### Step 4: Verify Services
```bash
# Check all services are running
docker-compose ps

# Expected output:
# finsight-ollama    ✓ healthy
# finsight-backend   ✓ healthy
# finsight-frontend  ✓ running
```

### Step 5: Access Applications
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

**That's it! 🎉 You're ready to go!**

---

## 💻 Option 2: Local Development (For Active Development)

**Best for making code changes and debugging**

### Step 1: Install Root Dependencies
```bash
git clone https://github.com/yourusername/finsight-ai.git
cd finsight-ai
pnpm install
```

### Step 2: Setup Backend
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize vector store
python scripts/init_vector_store.py
python scripts/seed_categories.py

cd ..
```

### Step 3: Setup Frontend
```bash
cd frontend

# Install dependencies
pnpm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your settings

cd ..
```

### Step 4: Install Ollama
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows - Download from https://ollama.com/download
```

### Step 5: Start Ollama
```bash
# Terminal 1 - Start Ollama server
ollama serve

# Terminal 2 - Pull model (one time)
ollama pull llama2:7b

# Verify it works
ollama run llama2:7b "Hello!"
```

### Step 6: Start Development Servers

**Option A: Using Turborepo (Recommended)**
```bash
# From root directory - starts both backend and frontend
pnpm dev
```

**Option B: Manual Start**
```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
pnpm dev

# Terminal 3 - Ollama (if not already running)
ollama serve
```

### Step 7: Verify Everything
Open these URLs:
- ✅ Frontend: http://localhost:3000
- ✅ Backend: http://localhost:8000/docs
- ✅ Ollama: http://localhost:11434

---

## 🧪 Quick Test

### Test Backend API
```bash
# Health check
curl http://localhost:8000/health

# Expected: {"status": "healthy"}
```

### Test Ollama
```bash
curl http://localhost:11434/api/version

# Expected: {"version": "..."}
```

### Test Upload (once backend is running)
```bash
# Create a test file
echo "Test transaction data" > test.txt

# Upload (adjust endpoint as needed)
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test.txt"
```

---

## 🛠️ Common Commands

### Development
```bash
# Start everything
pnpm dev

# Run tests
pnpm test

# Lint code
pnpm lint

# Format code
pnpm format
```

### Docker
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild containers
docker-compose up --build

# Clean everything
docker-compose down -v
```

### Backend Only
```bash
cd backend
source venv/bin/activate

# Run server
uvicorn app.main:app --reload

# Run tests
pytest

# Format code
black app/
isort app/
```

### Frontend Only
```bash
cd frontend

# Run dev server
pnpm dev

# Build for production
pnpm build

# Run tests
pnpm test
```

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
# OR
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>  # macOS/Linux
# OR
taskkill /PID <PID> /F  # Windows
```

### Ollama Not Responding
```bash
# Restart Ollama
pkill ollama
ollama serve

# Check if model is downloaded
ollama list

# Re-pull model if needed
ollama pull llama2:7b
```

### Docker Issues
```bash
# Restart Docker Desktop

# Clean Docker system
docker system prune -a

# Rebuild from scratch
docker-compose down -v
docker-compose up --build
```

### Python Virtual Environment Issues
```bash
# Delete and recreate venv
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend Dependencies Issues
```bash
# Clear cache and reinstall
rm -rf node_modules
rm pnpm-lock.yaml
pnpm install
```

---

## 📚 Next Steps

Once everything is running:

1. **Read the Documentation**
   - [System Design](docs/architecture/system-design.md)
   - [Database Design](docs/architecture/database-design.md)
   - [WBS](docs/planning/WBS.md)

2. **Explore the Code**
   - Backend: `backend/app/`
   - Frontend: `frontend/app/`

3. **Make Your First Change**
   - Follow [Contributing Guide](CONTRIBUTING.md)
   - Check [Cursor Rules](.cursorrules)

4. **Run Tests**
   ```bash
   pnpm test
   ```

5. **Deploy Locally**
   - Follow [Deployment Guide](docs/deployment/deployment-guide.md)

---

## 🎯 Development Workflow

```
1. Create feature branch
   git checkout -b feature/my-feature

2. Make changes
   - Edit code
   - Add tests
   - Update docs

3. Test locally
   pnpm dev
   pnpm test

4. Commit changes
   git add .
   git commit -m "feat: add my feature"

5. Push and create PR
   git push origin feature/my-feature
```

---

## 📞 Get Help

- **Documentation:** Check the `docs/` folder
- **Issues:** Create a GitHub issue
- **Discord:** Join our Discord server
- **Email:** support@finsight-ai.com

---

## ✅ Verification Checklist

Before you start developing:

- [ ] All services start without errors
- [ ] Frontend loads at http://localhost:3000
- [ ] Backend API docs at http://localhost:8000/docs
- [ ] Ollama responds to requests
- [ ] Tests pass (`pnpm test`)
- [ ] You can make a test API call
- [ ] Hot reload works (make a change and see it update)

---

**🎉 Congratulations! You're all set up and ready to build with FinSight AI!**

Happy coding! 🚀
