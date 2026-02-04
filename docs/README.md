# FinSight AI Documentation

**Last Updated:** February 4, 2026  
**Version:** 2.1  
**Project Status:** 58% Complete

---

## 📚 Documentation Index

This folder contains comprehensive documentation for the FinSight AI multi-agent fraud detection system. All documentation is organized by category for easy navigation.

---

## 🚀 Quick Start

**New to the project?** Start here:
1. [Project Overview](../README.md) - Main project README
2. [Quick Start Guide](../QUICKSTART.md) - Get running in 15 minutes
3. [Work Breakdown Structure](planning/WBS.md) - See what's completed and what's planned

---

## 📖 Core Documentation

### Architecture & System Design
| Document | Description | Last Updated |
|----------|-------------|--------------|
| [ARCHITECTURE-2026.md](architecture/ARCHITECTURE-2026.md) | **Main architecture document** - Complete system design (v2.1 + v3.0 roadmap) | Jan 24, 2026 |
| [system-design.md](architecture/system-design.md) | System design patterns and decisions | Dec 2025 |
| [database-design.md](architecture/database-design.md) | PostgreSQL schema and ChromaDB collections | Dec 2025 |

### AGI & LLM Concepts
| Document | Description | Last Updated |
|----------|-------------|--------------|
| [AGI-CONCEPTS-INTEGRATION.md](AGI-CONCEPTS-INTEGRATION.md) | **How this project covers all AGI topics** (A-H evaluation) | Jan 2026 |
| [AGI-TOPICS-QUICK-REFERENCE.md](AGI-TOPICS-QUICK-REFERENCE.md) | Quick lookup for AGI topic coverage | Jan 2026 |

### API Reference
| Document | Description | Last Updated |
|----------|-------------|--------------|
| [CORE-API-REFERENCE.md](CORE-API-REFERENCE.md) | Complete API documentation for all endpoints | Jan 2026 |
| [PROMPTING-PATTERNS-API-REFERENCE.md](PROMPTING-PATTERNS-API-REFERENCE.md) | ReAct, CoT, ToT, Debate pattern APIs | Jan 2026 |

### Implementation Details
| Document | Description | Last Updated |
|----------|-------------|--------------|
| [ASYNC-BACKEND-IMPLEMENTATION.md](ASYNC-BACKEND-IMPLEMENTATION.md) | Concurrency, state management, distributed patterns | Dec 31, 2025 |
| [STATE-MANAGEMENT-IMPLEMENTATION.md](STATE-MANAGEMENT-IMPLEMENTATION.md) | Session management, checkpointing, FSM | Dec 29, 2025 |
| [TOOL-INFRASTRUCTURE-TEST-RESULTS.md](TOOL-INFRASTRUCTURE-TEST-RESULTS.md) | Tool registry, sandboxing, safety testing | Jan 6, 2026 |
| [MLOPS-IMPLEMENTATION-SUMMARY.md](MLOPS-IMPLEMENTATION-SUMMARY.md) | MLOps pipeline and model management | Jan 2026 |

---

## 🗂️ Documentation by Category

### 1️⃣ Planning & Project Management
📁 **Location:** `docs/planning/`

- **[WBS.md](planning/WBS.md)** - Complete work breakdown structure (58% done)
- **[status-tracker.md](planning/status-tracker.md)** - Sprint tracking and milestones
- **[ML-MODEL-EVALUATION-WBS.md](planning/ML-MODEL-EVALUATION-WBS.md)** - ML experimentation plan

### 2️⃣ Data Pipeline
📁 **Location:** `docs/data/`

- **[DATA-PIPELINE.md](data/DATA-PIPELINE.md)** - Complete data workflow (cleaning, versioning, splitting)
- **[LABELING-GUIDELINES.md](data/LABELING-GUIDELINES.md)** - Annotation standards for fraud cases
- **[BIAS-FAIRNESS-ANALYSIS.md](data/BIAS-FAIRNESS-ANALYSIS.md)** - Bias audit and mitigation strategies
- **[DATA-VERSIONING.md](data/DATA-VERSIONING.md)** - DVC and W&B integration
- **[PIPELINE-AUTOMATION-SUMMARY.md](data/PIPELINE-AUTOMATION-SUMMARY.md)** - Automated data prep scripts

### 3️⃣ Deployment
📁 **Location:** `docs/deployment/`

- **[deployment-guide.md](deployment/deployment-guide.md)** - **Complete deployment guide** (Docker, K8s, AWS, Render)
- **[QUICKSTART-K8S.md](deployment/QUICKSTART-K8S.md)** - Local Kubernetes testing (5 minutes)

### 4️⃣ Safety & Alignment
📁 **Location:** `docs/safety/`

- **[SAFETY-ALIGNMENT.md](safety/SAFETY-ALIGNMENT.md)** - Prompt injection, hallucination detection, red-teaming

### 5️⃣ Design & UI
📁 **Location:** `docs/design/`

- **[database-diagram.md](design/database-diagram.md)** - Database schema diagrams
- **[figma-prompt.md](design/figma-prompt.md)** - UI design specifications

---

## 🎯 Documentation by User Persona

### For Developers (Backend)
1. [ARCHITECTURE-2026.md](architecture/ARCHITECTURE-2026.md) - System architecture
2. [CORE-API-REFERENCE.md](CORE-API-REFERENCE.md) - API endpoints
3. [ASYNC-BACKEND-IMPLEMENTATION.md](ASYNC-BACKEND-IMPLEMENTATION.md) - Async patterns
4. [STATE-MANAGEMENT-IMPLEMENTATION.md](STATE-MANAGEMENT-IMPLEMENTATION.md) - State handling
5. [database-design.md](architecture/database-design.md) - Database schema

### For ML Engineers
1. [DATA-PIPELINE.md](data/DATA-PIPELINE.md) - Data preparation
2. [MLOPS-IMPLEMENTATION-SUMMARY.md](MLOPS-IMPLEMENTATION-SUMMARY.md) - Model training
3. [BIAS-FAIRNESS-ANALYSIS.md](data/BIAS-FAIRNESS-ANALYSIS.md) - Fairness audits
4. [planning/ML-MODEL-EVALUATION-WBS.md](planning/ML-MODEL-EVALUATION-WBS.md) - Evaluation plan

### For Researchers (AGI/LLM)
1. [AGI-CONCEPTS-INTEGRATION.md](AGI-CONCEPTS-INTEGRATION.md) - AGI coverage
2. [PROMPTING-PATTERNS-API-REFERENCE.md](PROMPTING-PATTERNS-API-REFERENCE.md) - Advanced prompting
3. [TOOL-INFRASTRUCTURE-TEST-RESULTS.md](TOOL-INFRASTRUCTURE-TEST-RESULTS.md) - Tool use
4. [SAFETY-ALIGNMENT.md](safety/SAFETY-ALIGNMENT.md) - Safety mechanisms

### For DevOps
1. [deployment/deployment-guide.md](deployment/deployment-guide.md) - Full deployment
2. [deployment/QUICKSTART-K8S.md](deployment/QUICKSTART-K8S.md) - K8s setup
3. [ARCHITECTURE-2026.md](architecture/ARCHITECTURE-2026.md) - Infrastructure design

### For Project Managers
1. [planning/WBS.md](planning/WBS.md) - Work breakdown (58% complete)
2. [planning/status-tracker.md](planning/status-tracker.md) - Progress tracking
3. [AGI-TOPICS-QUICK-REFERENCE.md](AGI-TOPICS-QUICK-REFERENCE.md) - Topic coverage

---

## 📊 Project Statistics

- **Total Documentation Files:** 25 (down from 37 after cleanup)
- **Lines of Documentation:** ~15,000+ lines
- **Last Major Update:** February 4, 2026
- **Documentation Coverage:**
  - ✅ Architecture: 100%
  - ✅ API Reference: 100%
  - ✅ Data Pipeline: 100%
  - ✅ Deployment: 100%
  - ✅ AGI Concepts: 100%
  - 🔵 Frontend: 60% (in progress)

---

## 🔄 Recent Changes (Feb 4, 2026)

- ✅ Removed outdated summary files (UPDATE-SUMMARY.md, PROJECT-SETUP-SUMMARY.md)
- ✅ Consolidated deployment docs (merged 3 files into deployment-guide.md)
- ✅ Consolidated architecture quick references
- ✅ Consolidated data quick references
- ✅ Created master index (this file)
- ✅ Updated WBS to 58% completion

---

## 🤝 Contributing to Documentation

When adding new documentation:
1. **Place it in the correct category folder** (architecture/, data/, deployment/, etc.)
2. **Update this README.md** with a link in the appropriate section
3. **Use consistent markdown formatting** (see existing docs)
4. **Include last updated date** at the top of the document
5. **Keep it up to date** - remove outdated content promptly

---

## 📞 Need Help?

- **Can't find what you need?** Check the [Quick Start Guide](../QUICKSTART.md)
- **Want to contribute?** See [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Found an issue?** Open a GitHub issue with the `documentation` label

---

**Happy Reading! 📖✨**
