# Data Quality Validation Guide

**Last Updated:** February 8, 2026  
**Author:** FinSight AI Team

## Overview

The data validation pipeline ensures data quality throughout the MLOps lifecycle. It performs automated checks on raw and processed data to catch issues early and maintain data integrity.

## Features

### 1. **Schema Validation**
- Verifies column names and data types
- Ensures required columns are present
- Detects schema drift between pipeline stages

### 2. **Data Quality Checks**
- **Missing Values:** Detects and quantifies missing data
- **Duplicates:** Identifies duplicate rows
- **Outliers:** Detects statistical outliers using IQR method
- **Fraud Rate:** Validates fraud rate is within expected bounds

### 3. **Drift Detection**
- Compares current data against baseline
- Uses Kolmogorov-Smirnov (KS) test for numerical features
- Alerts when distributions change significantly

### 4. **Quality Scoring**
- Calculates overall quality score (0-100)
- Weighted scoring across all validation dimensions
- Provides actionable feedback

## Architecture

```
┌─────────────────┐
│   Raw Data      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────────┐
│  validate_data  │◄──────┤  Baseline Data   │
│     .py         │       │   (optional)     │
└────────┬────────┘       └──────────────────┘
         │
         ▼
┌─────────────────┐
│  Quality Report │
│     .json       │
└─────────────────┘
         │
         ├─ Pass ✅ → Continue Pipeline
         │
         └─ Fail ❌ → Stop Pipeline
```

## Usage

### Command Line

#### Basic Validation
```bash
# Validate raw data
python backend/scripts/validate_data.py data/raw/PS_*.csv

# Validate cleaned data
python backend/scripts/validate_data.py data/processed/paysim_cleaned.csv
```

#### Drift Detection
```bash
# Compare current data against baseline
python backend/scripts/validate_data.py \
  data/processed/paysim_cleaned.csv \
  --baseline data/raw/PS_*.csv
```

#### Strict Mode
```bash
# Fail on any warnings
python backend/scripts/validate_data.py \
  data/raw/PS_*.csv \
  --strict
```

#### Custom Output Directory
```bash
python backend/scripts/validate_data.py \
  data/raw/PS_*.csv \
  --output-dir reports/validation
```

#### Custom Report Name
```bash
# Useful when running multiple validations in same directory
python backend/scripts/validate_data.py \
  data/raw/PS_*.csv \
  --report-name raw_data_quality_report.json
```

### NPM Scripts

```bash
# Validate raw data
pnpm data:validate

# Validate cleaned data
pnpm data:validate:cleaned

# Strict mode (fail on warnings)
pnpm data:validate:strict

# Drift detection
pnpm data:validate:drift
```

### DVC Pipeline

The validation stage is automatically run in the DVC pipeline:

```bash
# Run validation stage only
dvc repro validate_raw

# Run full pipeline (includes validation)
dvc repro
```

## Quality Thresholds

Default thresholds (configurable in `validate_data.py`):

| Check | Threshold | Action |
|-------|-----------|--------|
| **Missing Values** | Max 5% | Error if exceeded |
| **Duplicates** | Max 1% | Error if exceeded |
| **Fraud Rate** | 0.01% - 50% | Error if outside range |
| **Drift (KS test)** | p-value < 0.05 | Warning if drift detected |
| **Outliers (IQR)** | ±3 IQR | Warning only |

## Validation Report

The validation report is saved as JSON (default: `data/analysis/data_quality_report.json`).

**DVC Pipeline Reports:**
- `data/analysis/raw_data_quality_report.json` - Raw data validation (before cleaning)
- `data/analysis/processed_data_quality_report.json` - Processed data quality check (after pipeline)

**Report Format:**
```json
{
  "timestamp": "2026-02-08T14:30:00",
  "data_file": "data/raw/PS_*.csv",
  "data_hash": "abc123...",
  "data_shape": [6362620, 11],
  "status": "PASSED",
  "quality_score": 95.5,
  "validations": {
    "schema": {
      "passed": true,
      "schema_type": "raw",
      "columns_count": 11,
      "issues": []
    },
    "missing_values": {
      "passed": true,
      "total_missing": 0,
      "missing_rate": 0.0,
      "threshold": 0.05
    },
    "duplicates": {
      "passed": true,
      "total_duplicates": 0,
      "duplicate_rate": 0.0
    },
    "fraud_rate": {
      "passed": true,
      "fraud_count": 8213,
      "fraud_rate": 0.001291,
      "expected_range": [0.0001, 0.5]
    },
    "outliers": {
      "passed": true,
      "columns_with_outliers": {
        "amount": {
          "count": 12345,
          "rate": 0.0019,
          "bounds": [-500, 5000]
        }
      }
    },
    "drift": {
      "passed": true,
      "columns_with_drift": 0,
      "drift_results": {}
    }
  },
  "errors": [],
  "warnings": ["Found 12345 outliers in amount column"]
}
```

## Exit Codes

- **0:** All validations passed
- **1:** Validation failed (quality gates triggered)
- **2:** Critical error (missing files, etc.)

## Quality Score Calculation

Quality score (0-100) is calculated using weighted validations:

```python
weights = {
    "schema": 20,           # 20% weight
    "missing_values": 25,   # 25% weight
    "duplicates": 20,       # 20% weight
    "fraud_rate": 15,       # 15% weight
    "outliers": 10,         # 10% weight
    "drift": 10,            # 10% weight
}
```

**Example:**
- Schema: ✅ PASS → 20 points
- Missing values: ✅ PASS → 25 points
- Duplicates: ✅ PASS → 20 points
- Fraud rate: ✅ PASS → 15 points
- Outliers: ✅ PASS → 10 points
- Drift: ⚠️ WARNING → 0 points

**Total: 90/100** → High quality

## Integration with MLOps Pipeline

### 1. **Pre-Processing Validation**
```yaml
# dvc.yaml
stages:
  validate_raw:
    cmd: python backend/scripts/validate_data.py data/raw/PS_*.csv
    deps:
      - data/raw/PS_*.csv
    metrics:
      - data/analysis/data_quality_report.json
```

### 2. **Post-Processing Validation**
```bash
# After data cleaning
python backend/scripts/validate_data.py \
  data/processed/paysim_cleaned.csv \
  --baseline data/raw/PS_*.csv
```

### 3. **Continuous Monitoring**
```bash
# Scheduled validation (cron)
0 0 * * * cd /path/to/finsight-ai && pnpm data:validate:drift
```

## Troubleshooting

### Issue: Missing Values Detected

**Error:**
```
Missing value rate 0.08% exceeds threshold 0.05%
```

**Solution:**
1. Check which columns have missing values in the report
2. Update `data_cleaning.py` to handle missing values
3. Re-run cleaning pipeline

### Issue: Duplicate Rows

**Error:**
```
Duplicate rate 0.02% exceeds threshold 0.01%
```

**Solution:**
1. Review duplicate detection logic
2. Update `data_cleaning.py` to remove duplicates earlier
3. Re-run pipeline

### Issue: Drift Detected

**Warning:**
```
Drift detected in amount: KS p-value=0.001
```

**Actions:**
1. Investigate why data distribution changed
2. Consider retraining models
3. Update baseline if drift is expected

### Issue: Fraud Rate Out of Range

**Error:**
```
Fraud rate 0.0001% outside expected range [0.01%, 50%]
```

**Solution:**
1. Verify this is the correct dataset
2. Check if fraud labeling is correct
3. Adjust thresholds if legitimate

## Best Practices

### 1. **Validate Early and Often**
- Run validation after every data transformation
- Use strict mode in CI/CD pipelines
- Monitor validation reports in production

### 2. **Track Validation History**
- Store validation reports in version control
- Compare quality scores over time
- Alert on quality degradation

### 3. **Baseline Management**
- Update baselines when data evolves legitimately
- Keep historical baselines for audit trails
- Document baseline changes

### 4. **Threshold Tuning**
- Adjust thresholds based on domain knowledge
- Monitor false positives/negatives
- Document threshold changes

### 5. **Integration Testing**
```bash
# Test validation in CI/CD
pytest tests/test_data_validation.py

# Manual validation before deployment
pnpm data:validate:strict
```

## Configuration

Edit thresholds in `backend/scripts/validate_data.py`:

```python
class DataValidator:
    # Quality thresholds
    MAX_MISSING_RATE = 0.05  # 5%
    MAX_DUPLICATE_RATE = 0.01  # 1%
    FRAUD_RATE_MIN = 0.0001  # 0.01%
    FRAUD_RATE_MAX = 0.5  # 50%
    PSI_THRESHOLD = 0.2  # Population Stability Index
    KS_PVALUE_THRESHOLD = 0.05  # KS test p-value
    OUTLIER_IQR_MULTIPLIER = 3.0  # IQR multiplier
```

## References

- [DVC Pipeline Documentation](../README.md#dvc-pipeline)
- [Data Lineage Tracking](./DATA-LINEAGE.md)
- [MLOps Best Practices](./MLOPS-WBS.md)
- [Kolmogorov-Smirnov Test](https://en.wikipedia.org/wiki/Kolmogorov%E2%80%93Smirnov_test)
- [Population Stability Index](https://en.wikipedia.org/wiki/Population_stability_index)

## Support

For issues or questions:
- Create an issue on GitHub
- Contact: FinSight AI Team
- Documentation: `docs/`

---

**Next Steps:**
- [Setup DVC Pipeline](../README.md#setup)
- [Data Lineage Guide](./DATA-LINEAGE.md)
- [MLOps Runbook](./MLOPS-RUNBOOK.md)
