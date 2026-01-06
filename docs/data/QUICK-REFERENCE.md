# Data Pipeline - Quick Reference Card

## 🚀 One-Line Commands

```bash
# Complete pipeline (recommended)
make data-pipeline

# OR using Python directly
python scripts/prepare_data_pipeline.py
```

## ⚡ Common Use Cases

### First Time Setup
```bash
# 1. Download PaySim dataset to data/raw/
# 2. Start ChromaDB
docker-compose up -d chromadb

# 3. Run pipeline
cd backend
make data-pipeline
```

### Development/Testing
```bash
# Quick mode (skip heavy augmentation)
make data-quick

# Custom limits
python scripts/prepare_data_pipeline.py --limit-fraud 50 --limit-vector 200
```

### Partial Updates
```bash
# Only vectorize (after policy changes)
make data-vector

# Only clean data
make data-clean

# Skip completed steps
python scripts/prepare_data_pipeline.py --skip-steps cleaning,splitting
```

## 📊 Expected Output

✅ **Files Created** (4.2 GB):
- `data/processed/paysim_cleaned.csv` - 6.36M rows, 30 features
- `data/splits/stratified/*.csv` - Train/val/test (60/20/20)
- `data/balanced/*.csv` - 3 augmented datasets
- `data/annotations/*.json` - Labels, explanations, RLHF pairs
- `data/analysis/*.json` - Bias audit reports
- `data/lineage.json` - Data provenance

✅ **ChromaDB Collections** (639 docs):
- `fraud_cases` - 500 known fraud examples
- `fraud_policies` - 32 detection rules
- `fraud_explanations` - 100 LLM explanations
- `transaction_patterns` - 7 statistical patterns

## ⏱️ Execution Time

- **Full Pipeline**: ~9 minutes
- **Quick Mode**: ~4 minutes
- **Vectorization Only**: ~30 seconds

## 🔍 Verification

```bash
# Check files
ls -lh data/processed/paysim_cleaned.csv
ls -lh data/splits/stratified/

# Check ChromaDB
python -c "
import chromadb
c = chromadb.HttpClient(host='localhost', port=8001)
print([col.name + ': ' + str(col.count()) for col in c.list_collections()])
"
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| ChromaDB error | `docker-compose up -d chromadb` |
| Out of memory | Use `--quick` mode |
| Missing raw data | Download from [Kaggle](https://www.kaggle.com/datasets/ealaxi/paysim1) |
| Script fails | Run individual scripts to isolate issue |

## 📚 More Info

- Full docs: [backend/scripts/README.md](../../backend/scripts/README.md)
- Implementation: [PIPELINE-AUTOMATION-SUMMARY.md](PIPELINE-AUTOMATION-SUMMARY.md)
- Data pipeline design: [DATA-PIPELINE.md](DATA-PIPELINE.md)

---

**Last Updated**: January 5, 2026
