# Sample Transaction Data for Testing

This directory contains sample CSV files for testing the fraud detection system.

## Files

### 1. `sample_transactions_small.csv` (25 rows)
- **Purpose:** Basic testing with mixed transaction types
- **Contains:** Mix of PAYMENT, TRANSFER, DEBIT, CASH_OUT transactions
- **Fraud:** 40% fraudulent (10 out of 25)
- **Use case:** Quick integration tests, unit tests

### 2. `sample_transactions_fraudulent.csv` (20 rows)
- **Purpose:** Testing fraud detection capabilities
- **Contains:** All fraudulent transactions (TRANSFER → CASH_OUT chains)
- **Fraud:** 100% fraudulent
- **Use case:** Testing model recall, fraud pattern recognition

### 3. `sample_transactions_normal.csv` (20 rows)
- **Purpose:** Testing normal transaction handling
- **Contains:** Legitimate PAYMENT, DEBIT, TRANSFER, CASH_OUT transactions
- **Fraud:** 0% fraudulent
- **Use case:** Testing model precision, false positive rate

### 4. `sample_transactions_edge_cases.csv` (20 rows)
- **Purpose:** Testing edge cases and boundary conditions
- **Contains:**
  - Very large amounts (>10M - flagged)
  - Very small amounts (0.01)
  - Zero amount transactions
  - Maximum value transfers
  - Chained transfers
- **Fraud:** 50% fraudulent
- **Use case:** Robustness testing, adversarial testing

## Schema

All files follow the PaySim dataset schema:

| Column | Type | Description |
|--------|------|-------------|
| `step` | int | Time step (1 hour increments) |
| `type` | string | Transaction type: PAYMENT, TRANSFER, CASH_OUT, DEBIT, CASH_IN |
| `amount` | float | Transaction amount in currency units |
| `nameOrig` | string | Customer initiating transaction |
| `oldbalanceOrg` | float | Initial balance before transaction |
| `newbalanceOrig` | float | New balance after transaction |
| `nameDest` | string | Recipient of transaction |
| `oldbalanceDest` | float | Initial recipient balance |
| `newbalanceDest` | float | New recipient balance |
| `isFraud` | int | Ground truth fraud label (0 or 1) |
| `isFlaggedFraud` | int | System flagged as fraud (>10M transfers) |

## Usage

### Load in Python
```python
import pandas as pd

# Load any sample file
df = pd.read_csv('data/samples/sample_transactions_small.csv')
print(f"Loaded {len(df)} transactions")
print(f"Fraud rate: {df['isFraud'].mean():.1%}")
```

### Quick Stats
```python
# Get transaction type distribution
print(df['type'].value_counts())

# Get fraud statistics
fraud_stats = df.groupby('isFraud').agg({
    'amount': ['count', 'mean', 'sum'],
    'type': lambda x: x.value_counts().to_dict()
})
print(fraud_stats)
```

### API Testing
```bash
# Test with curl
curl -X POST http://localhost:8000/api/analyze/transaction \
  -H "Content-Type: application/json" \
  -d '{
    "step": 1,
    "type": "TRANSFER",
    "amount": 500000,
    "nameOrig": "C1234567890",
    "oldbalanceOrg": 600000,
    "newbalanceOrig": 100000,
    "nameDest": "C9876543210",
    "oldbalanceDest": 0,
    "newbalanceDest": 500000
  }'
```

## Fraud Patterns Included

1. **Transfer-CashOut Chain:** Large transfer immediately followed by cash out (classic money laundering)
2. **Balance Inconsistencies:** Transactions where balance changes don't match amounts
3. **High-Value Transfers:** Amounts exceeding typical thresholds
4. **Round Amounts:** Suspiciously round numbers (e.g., exactly 5000000.00)
5. **Zero Balance Endpoints:** Accounts emptied completely

## Testing Recommendations

1. **Unit Tests:** Use `sample_transactions_small.csv`
2. **Model Training:** Combine all files for diverse examples
3. **Precision Testing:** Use `sample_transactions_normal.csv` (should have 0 false positives)
4. **Recall Testing:** Use `sample_transactions_fraudulent.csv` (should detect all)
5. **Robustness:** Use `sample_transactions_edge_cases.csv`

## Extending Samples

To generate more samples:

```python
import pandas as pd
import numpy as np

def generate_normal_transaction(step):
    return {
        'step': step,
        'type': np.random.choice(['PAYMENT', 'DEBIT']),
        'amount': np.random.uniform(10, 5000),
        'nameOrig': f'C{np.random.randint(1e9, 1e10)}',
        'oldbalanceOrg': np.random.uniform(1000, 10000),
        # ... calculate balances
        'isFraud': 0,
        'isFlaggedFraud': 0
    }

def generate_fraud_chain(step):
    amount = np.random.uniform(500000, 10000000)
    orig = f'C{np.random.randint(1e9, 1e10)}'
    intermediate = f'C{np.random.randint(1e9, 1e10)}'
    dest = f'C{np.random.randint(1e9, 1e10)}'
    
    transfer = {
        'step': step,
        'type': 'TRANSFER',
        'amount': amount,
        'nameOrig': orig,
        'oldbalanceOrg': amount + 100000,
        'newbalanceOrig': 100000,
        'nameDest': intermediate,
        'oldbalanceDest': 0,
        'newbalanceDest': amount,
        'isFraud': 1,
        'isFlaggedFraud': 1 if amount > 10000000 else 0
    }
    
    cashout = {
        'step': step,
        'type': 'CASH_OUT',
        'amount': amount,
        'nameOrig': intermediate,
        'oldbalanceOrg': amount,
        'newbalanceOrig': 0,
        'nameDest': dest,
        'oldbalanceDest': 1000,
        'newbalanceDest': amount + 1000,
        'isFraud': 1,
        'isFlaggedFraud': 1 if amount > 10000000 else 0
    }
    
    return [transfer, cashout]
```
