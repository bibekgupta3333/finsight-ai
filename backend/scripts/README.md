# Data Pipeline - Complete Automation

This directory contains scripts to prepare all data for the FinSight AI fraud detection system, from raw data to vector database population.

## 🚀 Quick Start

### One-Command Pipeline

Run the entire pipeline with a single command:

```bash
cd backend
python scripts/prepare_data_pipeline.py
```

This will execute all 8 steps in order:
1. **Data Cleaning** - Process raw data, engineer features
2. **Dataset Splitting** - Create train/val/test splits
3. **Data Augmentation** - Balance dataset with SMOTE
4. **Weak Supervision** - Generate labels and RLHF pairs
5. **Fraud Explanations** - Create LLM-generated explanations
6. **Bias Analysis** - Audit fairness and demographic parity
7. **Data Lineage** - Track data provenance
8. **Vectorization** - Populate ChromaDB for RAG inference

## 📋 Prerequisites

1. **Raw Data**: Place PaySim dataset in `data/raw/`
   ```bash
   # Download from Kaggle:
   # https://www.kaggle.com/datasets/ealaxi/paysim1
   ```

2. **ChromaDB**: Start ChromaDB service
   ```bash
   docker-compose up -d chromadb
   ```

3. **Python Environment**:
   ```bash
   cd backend
   poetry install
   ```

## ⚙️ Usage Options

### Quick Mode (Skip Augmentation)
For faster execution during development:
```bash
python scripts/prepare_data_pipeline.py --quick
```

### Skip Specific Steps
If you already have some outputs:
```bash
python scripts/prepare_data_pipeline.py --skip-steps cleaning,splitting
```

### Limit Samples
Process fewer samples for testing:
```bash
python scripts/prepare_data_pipeline.py --limit-fraud 50 --limit-vector 200
```

### Generate Execution Report
Save detailed execution metrics:
```bash
python scripts/prepare_data_pipeline.py --generate-report
```

### Combine Options
```bash
python scripts/prepare_data_pipeline.py \
  --quick \
  --skip-steps bias_analysis \
  --limit-fraud 50 \
  --generate-report
```

## 📁 Output Structure

After running the pipeline, your `data/` directory will contain:

```
data/
├── raw/
│   └── PS_20174392719_1491204439457_log.csv
├── processed/
│   ├── paysim_cleaned.csv
│   ├── cleaning_statistics.json
│   └── cleaned_metadata.json
├── splits/
│   ├── stratified/
│   │   ├── train.csv
│   │   ├── val.csv
│   │   └── test.csv
│   ├── temporal/
│   │   ├── train.csv
│   │   ├── val.csv
│   │   └── test.csv
│   └── split_metadata.json
├── balanced/
│   ├── train_balanced_smote.csv
│   ├── train_balanced_combined.csv
│   ├── train_balanced_with_synthetic.csv
│   └── augmentation_metadata.json
├── annotations/
│   ├── weak_supervision_labels.json
│   ├── preference_pairs.json
│   ├── fraud_explanations.json
│   └── fraud_explanations_summary.csv
├── analysis/
│   ├── bias_audit_report.json
│   └── bias_audit_summary.txt
├── chromadb/
│   └── [ChromaDB persistent data]
└── lineage.json
```

## 🔧 Individual Scripts

You can also run scripts individually:

### 1. Data Cleaning
```bash
python scripts/data_cleaning.py
```
**Input**: `data/raw/PS_*.csv`  
**Output**: `data/processed/paysim_cleaned.csv`

### 2. Dataset Splitting
```bash
python scripts/dataset_splitting.py
```
**Input**: `data/processed/paysim_cleaned.csv`  
**Output**: `data/splits/{stratified,temporal}/*.csv`

### 3. Data Augmentation
```bash
python scripts/data_augmentation.py
```
**Input**: `data/splits/stratified/train.csv`  
**Output**: `data/balanced/*.csv`

### 4. Weak Supervision
```bash
python scripts/generate_weak_supervision.py
```
**Input**: `data/processed/paysim_cleaned.csv`  
**Output**: `data/annotations/weak_supervision_labels.json`

### 5. Fraud Explanations
```bash
python scripts/generate_explanations.py
```
**Input**: `data/processed/paysim_cleaned.csv`  
**Output**: `data/annotations/fraud_explanations.json`

### 6. Bias Analysis
```bash
python scripts/bias_fairness_analysis.py
```
**Input**: `data/processed/paysim_cleaned.csv`  
**Output**: `data/analysis/bias_audit_report.json`

### 7. Data Lineage
```bash
python scripts/data_lineage.py
```
**Output**: `data/lineage.json`

### 8. Vectorization
```bash
python scripts/vectorize_data.py
```
**Input**: Multiple (processed data, policies, explanations)  
**Output**: ChromaDB collections

## 🐳 Docker Setup

If using Docker Compose:

```bash
# Start ChromaDB
docker-compose up -d chromadb

# Run pipeline in container
docker-compose exec backend python scripts/prepare_data_pipeline.py
```

## 📊 Pipeline Execution Report

The `--generate-report` flag creates `data/pipeline_report.json`:

```json
{
  "timestamp": "2026-01-05T22:00:00",
  "execution": {
    "completed": ["cleaning", "splitting", ...],
    "skipped": [],
    "failed": []
  },
  "durations": {
    "cleaning": 51.2,
    "splitting": 234.5,
    ...
  },
  "total_duration": 428.7
}
```

## ⚡ Performance Tips

1. **Use SSD**: Store data on SSD for faster I/O
2. **Increase RAM**: Data augmentation needs ~8GB RAM
3. **Skip Steps**: Use `--skip-steps` to avoid re-running completed steps
4. **Quick Mode**: Use `--quick` for development/testing
5. **Parallel Processing**: Some scripts use multiprocessing (limited by CPU cores)

## 🔍 Verification

After pipeline completion, verify:

### 1. Check Data Files
```bash
ls -lh data/processed/
ls -lh data/splits/stratified/
ls -lh data/annotations/
```

### 2. Verify ChromaDB Collections
```bash
# Access ChromaDB UI
open http://localhost:8001

# Or via Python
python -c "
import chromadb
client = chromadb.HttpClient(host='localhost', port=8001)
print('Collections:', [c.name for c in client.list_collections()])
print('Fraud cases:', client.get_collection('fraud_cases').count())
"
```

### 3. Check Pipeline Report
```bash
cat data/pipeline_report.json | jq
```

## 🐛 Troubleshooting

### ChromaDB Connection Error
```bash
# Make sure ChromaDB is running
docker-compose ps chromadb

# Restart if needed
docker-compose restart chromadb
```

### Out of Memory
```bash
# Use quick mode or limit samples
python scripts/prepare_data_pipeline.py --quick --limit-fraud 50
```

### Missing Raw Data
```bash
# Download from Kaggle and place in data/raw/
# https://www.kaggle.com/datasets/ealaxi/paysim1
```

### Script Fails Mid-Pipeline
```bash
# Resume by skipping completed steps
python scripts/prepare_data_pipeline.py --skip-steps cleaning,splitting
```

## 📚 References

- [PaySim Dataset](https://www.kaggle.com/datasets/ealaxi/paysim1)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Data Pipeline Documentation](../../docs/data/DATA-PIPELINE.md)

## 🤝 Contributing

When adding new pipeline steps:

1. Create script in `backend/scripts/`
2. Add step configuration to `prepare_data_pipeline.py`
3. Update this README
4. Test with `--skip-steps` for other stages

---

**Last Updated**: January 5, 2026  
**Maintainer**: FinSight AI Team
