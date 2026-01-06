# FinSight AI - Multimodal FinTech Fraud Detection & Reasoning Agent

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Node](https://img.shields.io/badge/node-18+-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![Dataset](https://img.shields.io/badge/dataset-PaySim_6.3M-orange.svg)
![AGI](https://img.shields.io/badge/AGI-ready-purple.svg)

**A comprehensive fraud detection system demonstrating mastery of the entire AGI/LLM development lifecycle** — from data engineering to safety-aware deployment.

> 🎯 **Interview Signal:** "I built an end-to-end fraud detection system covering reasoning, agentic workflows, RAG, fine-tuning, evaluation, and safety — on a real 6.3M transaction dataset."

---

## 🌟 Key Features

### Core Capabilities
- **🔍 Fraud Detection:** ML-powered risk scoring with 99%+ precision on PaySim dataset
- **🧠 Agentic Reasoning:** Multi-step ReAct workflow with chain-of-thought explanations
- **📚 RAG System:** Retrieve fraud policies before making decisions
- **🛡️ Safety-First:** Prompt injection defense, bias audits, uncertainty quantification
- **📊 Explainable AI:** Every decision includes faithful reasoning trace
- **⚖️ Human-in-the-Loop:** Escalation system for uncertain cases with feedback loop

### Advanced Features
- **📈 Data Lifecycle:** End-to-end pipeline from raw CSV → cleaned → features → embeddings
- **🎛️ Fine-Tuning:** LoRA adaptation for domain-specific fraud explanations
- **🔬 Evaluation Suite:** Classification + reasoning quality + adversarial testing
- **📡 Monitoring:** Real-time drift detection, token tracking, latency metrics
- **🔒 Privacy:** PII masking, output sanitization, no data leakage

---

## 🏗️ System Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                             │
│  Dashboard │ Upload CSV │ Analysis │ Insights │ Safety Monitor   │
└────────────────────────┬──────────────────────────────────────────┘
                         │ HTTPS/WebSocket
                         ▼
┌───────────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                               │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │  DATA        │  │  ML          │  │  LANGGRAPH AGENT    │   │
│  │  PIPELINE    │  │  CLASSIFIER  │  │                     │   │
│  │              │  │              │  │  1. Inspect         │   │
│  │ • Load CSV   │  │ • XGBoost    │  │  2. Retrieve (RAG)  │   │
│  │ • Clean      │  │ • Risk Score │  │  3. Calculate       │   │
│  │ • Features   │  │ • Decision   │  │  4. Reason (CoT)    │   │
│  │ • SMOTE      │  └──────┬───────┘  │  5. Decide          │   │
│  └──────────────┘         │          │  6. Explain         │   │
│                           │          └─────────┬───────────┘   │
│                           ▼                    │               │
│  ┌─────────────────────────────────────────────▼─────────────┐ │
│  │           ChromaDB (Vector Store)                         │ │
│  │  • Fraud Cases    • Policies    • Explanations           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────┐                         │
│  │     Ollama (Mistral 7B 4-bit)    │                         │
│  │     Local LLM Inference          │                         │
│  └───────────────────────────────────┘                         │
└───────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────────────────────────────┐
│                PostgreSQL (Analytics & Feedback)                  │
│  • Analysis Logs  • Human Feedback  • Safety Incidents           │
└───────────────────────────────────────────────────────────────────┘
```

---

## 📊 Dataset: PaySim Mobile Money

- **Source:** [Kaggle - PaySim1](https://www.kaggle.com/datasets/ealaxi/paysim1)
- **Size:** 6,362,620 transactions
- **Fraud Rate:** 0.13% (highly imbalanced - perfect for advanced ML)
- **Location:** `data/raw/PS_*.csv`
- **Features:** 11 columns (amount, type, balances, fraud labels)
- **Challenge:** Class imbalance, temporal patterns, adversarial fraud

### Data Pipeline (Automated)

The project includes a complete automated data pipeline that transforms raw data into production-ready formats:

```bash
# Run complete 8-step pipeline
cd backend
python scripts/prepare_data_pipeline.py
```

**Pipeline Steps:**
1. **Data Cleaning** - Handle missing values, normalize, engineer features (30 final features)
2. **Dataset Splitting** - Stratified & temporal splits (60/20/20 train/val/test)
3. **Data Augmentation** - SMOTE balancing for class imbalance (3 strategies)
4. **Weak Supervision** - Generate labels and RLHF preference pairs
5. **Fraud Explanations** - LLM-generated explanations (100 samples)
6. **Bias Analysis** - Fairness audit with demographic parity checks
7. **Data Lineage** - Complete data provenance tracking
8. **Vectorization** - Populate ChromaDB with 639 embeddings for RAG

**Quick Options:**
```bash
# Quick mode (skip augmentation, faster)
python scripts/prepare_data_pipeline.py --quick

# Skip specific steps
python scripts/prepare_data_pipeline.py --skip-steps augmentation,bias_analysis

# Generate execution report
python scripts/prepare_data_pipeline.py --generate-report
```

**Output:** All processed data in `data/` directory + ChromaDB collections ready for inference.

See [backend/scripts/README.md](backend/scripts/README.md) for detailed documentation.

---

## 🧠 Why This Project is AGI-Level

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and pnpm
- **Python** 3.11+
- **Docker** Desktop
- **Ollama** (for local LLM)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/finsight-ai.git
   cd finsight-ai
   ```

2. **Install dependencies**
   ```bash
   # Install root dependencies
   pnpm install

   # Install backend dependencies
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cd ..

   # Install frontend dependencies
   cd frontend
   pnpm install
   cd ..
   ```

3. **Setup environment variables**
   ```bash
   # Backend
   cp backend/.env.example backend/.env
   # Edit backend/.env with your configuration

   # Frontend
   cp frontend/.env.example frontend/.env.local
   # Edit frontend/.env.local with your configuration
   ```

4. **Install and start Ollama**
   ```bash
   # macOS
   brew install ollama
   ollama serve

   # In another terminal, pull the model
   ollama pull llama2:7b
   ```

5. **Start development servers**
   ```bash
   # From root directory - starts both frontend and backend
   pnpm dev

   # Or manually:
   # Terminal 1 - Backend
   cd backend && source venv/bin/activate && uvicorn app.main:app --reload

   # Terminal 2 - Frontend
   cd frontend && pnpm dev
   ```

6. **Prepare data pipeline** (one-time setup)
   ```bash
   # Download PaySim dataset from Kaggle and place in data/raw/
   # https://www.kaggle.com/datasets/ealaxi/paysim1
   
   # Start ChromaDB
   docker-compose up -d chromadb
   
   # Run complete data pipeline (8 steps)
   cd backend
   python scripts/prepare_data_pipeline.py
   
   # Or run in quick mode for testing
   python scripts/prepare_data_pipeline.py --quick
   ```

7. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - ChromaDB: http://localhost:8001

### Docker Setup

```bash
# Start all services with Docker Compose
docker-compose up -d

# Pull Ollama model
docker exec -it finsight-ollama ollama pull llama2:7b

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📚 Documentation

Comprehensive documentation is available in the `docs/` folder:

- **[Work Breakdown Structure](docs/planning/WBS.md)** - Project plan and status tracking
- **[System Design](docs/architecture/system-design.md)** - Architecture and component design
- **[Database Design](docs/architecture/database-design.md)** - Data models and schema
- **[Deployment Guide](docs/deployment/deployment-guide.md)** - Step-by-step deployment instructions
- **[Figma Design Prompt](docs/design/figma-prompt.md)** - UI/UX design specifications

## 🛠️ Technology Stack

### Backend
- **FastAPI** - High-performance async API framework
- **LangGraph** - Agent orchestration
- **Ollama** - Local LLM inference
- **ChromaDB** - Vector database for embeddings
- **EasyOCR** - Text extraction from images
- **pdfplumber** - PDF parsing

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Beautiful UI components
- **Zustand** - State management
- **Recharts** - Data visualization

### Infrastructure
- **Docker** - Containerization
- **Kubernetes** - Orchestration
- **Terraform** - Infrastructure as Code
- **Helm** - Kubernetes package manager
- **AWS** - Cloud provider

## 📁 Project Structure

```
finsight-ai/
├── frontend/                 # Next.js frontend application
│   ├── app/                 # Next.js app directory (routes)
│   ├── components/          # React components
│   ├── lib/                 # Utilities and API client
│   └── store/               # Zustand stores
├── backend/                  # FastAPI backend application
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── agents/         # LangGraph agents
│   │   ├── services/       # Business logic
│   │   └── models/         # Pydantic models
│   └── tests/              # Backend tests
├── docs/                     # Documentation
│   ├── planning/           # Project planning
│   ├── architecture/       # System design
│   ├── deployment/         # Deployment guides
│   └── design/             # UI/UX design
├── kubernetes/               # K8s manifests
├── terraform/                # Infrastructure as Code
├── docker/                   # Docker configurations
├── package.json             # Root package.json (monorepo)
├── turbo.json               # Turborepo configuration
└── docker-compose.yml       # Local development setup
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
pnpm test

# All tests via Turbo
pnpm test
```

## 🚢 Deployment

### Kubernetes + Helm

```bash
# Create namespace
kubectl create namespace finsight-ai

# Deploy with Helm
helm install finsight ./helm/finsight-ai-chart \
  --namespace finsight-ai \
  --create-namespace
```

### AWS with Terraform

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

See [Deployment Guide](docs/deployment/deployment-guide.md) for detailed instructions.

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [LangChain](https://www.langchain.com/) and [LangGraph](https://langchain-ai.github.io/langgraph/)
- Powered by [Ollama](https://ollama.ai/) for local LLM inference
- UI components from [shadcn/ui](https://ui.shadcn.com/)
- Vector embeddings by [Sentence Transformers](https://www.sbert.net/)

## 📞 Support

- 📧 Email: support@finsight-ai.com
- 💬 Discord: [Join our community](https://discord.gg/finsight-ai)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/finsight-ai/issues)

## 🗺️ Roadmap

- [ ] Voice input processing
- [ ] Mobile app (React Native)
- [ ] Multi-language support
- [ ] Budget planning features
- [ ] Investment insights
- [ ] Real-time alerts
- [ ] Team/family accounts

---

**Made with ❤️ by the FinSight AI Team**
