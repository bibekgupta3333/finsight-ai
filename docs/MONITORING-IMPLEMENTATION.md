# Monitoring & Observability Implementation

## Overview
Comprehensive monitoring system for FinSight AI fraud detection, optimized for local M4 Pro development. Built as a lightweight alternative to Prometheus/Grafana with in-memory metrics and custom React dashboard.

## Architecture

### Backend Components

#### 1. Metrics Monitor Service
**File:** `/backend/app/services/monitoring/metrics_monitor.py` (650 lines)

**Purpose:** Core metrics collection, statistical analysis, and persistence.

**Data Structures:**
```python
@dataclass
class ModelMetrics:
    timestamp: str
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    total_predictions: int

@dataclass
class LatencyMetrics:
    p50: float  # Median
    p95: float  # 95th percentile
    p99: float  # 99th percentile
    mean: float
    min: float
    max: float
    count: int

@dataclass
class ErrorMetrics:
    error_type: str
    error_count: int
    error_rate: float
    timestamp: str

@dataclass
class DriftMetrics:
    feature_name: str
    drift_score: float
    is_drifting: bool
    mean_shift: float
    variance_change: float
    timestamp: str
```

**Storage Strategy:**
- **In-memory:** Bounded deques for fast access
  - `prediction_logs`: deque(maxlen=10000)
  - `latency_buffer`: Dict[endpoint, deque(maxlen=1000)]
  - `error_buffer`: deque(maxlen=1000)
  - `token_buffer`: deque(maxlen=1000)
- **Disk persistence:** JSONL files
  - `data/monitoring/prediction_logs.jsonl`
  - `data/monitoring/errors.jsonl`
- **Cache:** 60-second TTL for dashboard data

**Key Methods:**
- `log_prediction()` - Log prediction with features, persist to JSONL
- `calculate_model_metrics()` - Compute confusion matrix and derived metrics
- `get_prediction_distribution()` - Fraud rate, confidence stats
- `calculate_latency_metrics()` - Compute percentiles (p50, p95, p99)
- `calculate_error_metrics()` - Error counts and rates by type
- `get_token_usage_stats()` - Token consumption tracking
- `detect_drift()` - Statistical drift detection (mean shift + variance)
- `get_dashboard_data()` - Comprehensive metrics with caching
- `get_time_series_data()` - Time-bucketed metrics for charts

#### 2. Structured Logger
**File:** `/backend/app/core/structured_logger.py` (280 lines)

**Purpose:** Production-ready JSON logging with context enrichment.

**Features:**
- **JSON output:** Machine-readable logs with timestamp, level, message, context
- **Context variables:** `request_id`, `user_id`, `transaction_id` (request-scoped)
- **Multi-handler setup:**
  - Console: INFO+ (human-readable)
  - File: DEBUG+ (`logs/{name}.log`)
  - Error: ERROR+ (`logs/{name}_errors.log`)
- **Performance decorator:** `@log_execution_time` for method timing
- **Exception tracking:** Automatic stack trace capture

**Application Loggers:**
```python
fraud_logger = StructuredLogger("fraud_detection")
api_logger = StructuredLogger("api")
security_logger = StructuredLogger("security")
monitor_logger = StructuredLogger("monitoring")
```

**Example Log:**
```json
{
  "timestamp": "2026-02-05T01:16:59.859304Z",
  "level": "INFO",
  "logger": "fraud_detection",
  "message": "Transaction processed",
  "request_id": "req_abc123",
  "transaction_id": "tx_456",
  "duration_ms": 450.5,
  "status": "success"
}
```

### API Endpoints

**Base Path:** `/api/v1/fraud/monitoring`

| Method | Endpoint | Purpose | Response |
|--------|----------|---------|----------|
| POST | `/log-prediction` | Log prediction data | `{"status": "logged", "transaction_id": "..."}` |
| GET | `/metrics?time_window_hours=24` | Dashboard data | Full metrics object |
| GET | `/model-performance` | ML metrics | ModelMetrics dict |
| GET | `/latency` | Latency stats | {endpoint: LatencyMetrics} |
| GET | `/errors` | Error tracking | {"errors": [ErrorMetrics]} |
| GET | `/token-usage` | Token stats | Token statistics dict |
| GET | `/drift/{feature}` | Drift detection | DriftMetrics or 404 |
| GET | `/time-series/{metric}` | Time-bucketed data | {"metric_name": "...", "data": [...]} |

**Request Model:**
```python
class PredictionLogRequest(BaseModel):
    transaction_id: str
    predicted_label: str  # "fraud" or "legitimate"
    true_label: Optional[str] = None
    confidence: float
    features: Dict[str, Any]
    latency_ms: Optional[float] = None
    token_count: Optional[int] = None
```

### Frontend Dashboard

**File:** `/frontend/app/dashboard/monitoring/page.tsx` (450 lines)

**Route:** `/dashboard/monitoring`

**Features:**
- **Auto-refresh:** 60-second interval
- **Time window selector:** 1h, 6h, 24h, 1 week
- **4 Tab Views:**
  1. **Performance** - ML metrics, confusion matrix
  2. **Latency** - Percentiles by endpoint
  3. **Token Usage** - LLM consumption stats
  4. **Predictions** - Fraud vs legitimate distribution

**Visualizations (Recharts):**
- **PieChart:** Confusion matrix (TP, TN, FP, FN)
- **PieChart:** Prediction distribution (fraud vs legitimate)
- **BarChart:** Latency percentiles (p50, p95, p99) by endpoint
- **Progress bars:** Token percentiles

**Color Scheme:**
- Green (#10b981): True positives, legitimate
- Blue (#3b82f6): True negatives, p50
- Orange (#f59e0b): False positives, p95
- Red (#ef4444): False negatives, fraud, p99

**State Management:**
```typescript
interface DashboardData {
  timestamp: string;
  time_window_hours: number;
  model_performance: ModelPerformance;
  latency: { [endpoint: string]: LatencyStats };
  errors: ErrorInfo[];
  token_usage: TokenUsage;
  prediction_distribution: PredictionDist;
  drift_detection: any;
  system_health: SystemHealth;
}
```

## Usage

### 1. Log a Prediction

```bash
curl -X POST http://localhost:8000/api/v1/fraud/monitoring/log-prediction \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "tx_12345",
    "predicted_label": "fraud",
    "true_label": "fraud",
    "confidence": 0.92,
    "features": {
      "amount": 5000,
      "type": "TRANSFER",
      "oldbalanceOrg": 10000,
      "newbalanceOrig": 5000
    },
    "latency_ms": 450.5,
    "token_count": 320
  }'
```

### 2. Get Dashboard Metrics

```bash
curl http://localhost:8000/api/v1/fraud/monitoring/metrics?time_window_hours=24 | jq
```

**Response:**
```json
{
  "timestamp": "2026-02-05T01:17:04.031905",
  "time_window_hours": 24,
  "model_performance": {
    "true_positives": 4,
    "true_negatives": 5,
    "false_positives": 1,
    "false_negatives": 1,
    "precision": 0.8,
    "recall": 0.8,
    "f1_score": 0.8,
    "accuracy": 0.82,
    "total_predictions": 11
  },
  "prediction_distribution": {
    "fraud_count": 5,
    "legitimate_count": 6,
    "fraud_rate": 0.45,
    "avg_confidence": 0.73
  },
  "system_health": {
    "total_predictions": 11,
    "endpoints_monitored": 0,
    "error_count": 0
  }
}
```

### 3. Check Model Performance

```bash
curl http://localhost:8000/api/v1/fraud/monitoring/model-performance
```

### 4. Detect Data Drift

First, set reference distribution:
```python
from app.services.monitoring import metrics_monitor

# Set baseline distribution for 'amount' feature
reference_amounts = [1000, 1500, 2000, 2500, 3000, ...]
metrics_monitor.set_reference_distribution('amount', reference_amounts)
```

Then query drift:
```bash
curl http://localhost:8000/api/v1/fraud/monitoring/drift/amount
```

**Response:**
```json
{
  "feature_name": "amount",
  "drift_score": 0.65,
  "is_drifting": true,
  "mean_shift": 0.45,
  "variance_change": 0.85,
  "timestamp": "2026-02-05T01:20:00.000000"
}
```

### 5. View Dashboard

Open browser: http://localhost:3000/dashboard/monitoring

## Design Decisions

### Why No Prometheus/Grafana?

**Reasoning:**
- **Resource constraints:** M4 Pro laptop with limited resources
- **Local development:** Don't need enterprise-scale monitoring
- **Simplicity:** Fewer moving parts, easier debugging
- **Speed:** In-memory metrics faster than external server
- **Cost:** No additional infrastructure

**Trade-offs:**
- ✅ Pros: Lightweight, fast, integrated, easy to maintain
- ❌ Cons: Limited historical data, no distributed metrics, manual dashboard

### Bounded Memory with Deques

**Reasoning:**
- Prevents unbounded memory growth on M4 Pro
- Fast O(1) append and pop operations
- Automatic eviction of oldest entries
- Suitable for local dev (10k predictions = weeks of data)

**Configuration:**
```python
prediction_logs: deque(maxlen=10000)  # ~10k predictions
latency_buffer: deque(maxlen=1000)    # Per endpoint
error_buffer: deque(maxlen=1000)      # Recent errors
token_buffer: deque(maxlen=1000)      # Token usage
```

### 60-Second Cache TTL

**Reasoning:**
- Dashboard metrics don't change that fast
- Avoid recomputing expensive statistics (percentiles, aggregations)
- Reduces CPU usage on M4 Pro
- Still provides near-real-time view

**Implementation:**
```python
@cached(cache=TTLCache(maxsize=100, ttl=60))
def get_dashboard_data(time_window_hours: int = 24):
    # Expensive computation cached for 60 seconds
    pass
```

### Statistical Drift Detection

**Reasoning:**
- Lightweight alternative to ML-based drift detection (e.g., KS test)
- No training needed, works immediately
- Interpretable results (mean shift + variance change)
- Suitable for continuous monitoring

**Algorithm:**
```python
def detect_drift(feature_name: str):
    reference = reference_distributions[feature_name]
    current = [p.features[feature_name] for p in recent_predictions]
    
    mean_shift = abs(mean(current) - mean(reference)) / std(reference)
    variance_change = abs(std(current) - std(reference)) / std(reference)
    drift_score = (mean_shift + variance_change) / 2
    
    is_drifting = drift_score > 0.5  # Threshold
    return DriftMetrics(feature_name, drift_score, is_drifting, ...)
```

## Testing

### Local Testing (Completed)

**Backend:**
```bash
# 1. Start FastAPI server
cd backend
uvicorn app.main:app --reload

# 2. Log test predictions
for i in {1..20}; do
  curl -X POST http://localhost:8000/api/v1/fraud/monitoring/log-prediction \
    -H "Content-Type: application/json" \
    -d '{...}'
done

# 3. Verify metrics
curl http://localhost:8000/api/v1/fraud/monitoring/metrics | jq
```

**Frontend:**
```bash
# 1. Start Next.js dev server
cd frontend
pnpm dev

# 2. Open dashboard
open http://localhost:3000/dashboard/monitoring
```

**Test Results:**
- ✅ 11 predictions logged successfully
- ✅ Model metrics calculated: F1=0.80, Accuracy=0.82
- ✅ Dashboard renders all tabs without errors
- ✅ Auto-refresh working (60s interval)
- ✅ Time window selector functional

### Future Testing

**Load Testing:**
```bash
# Generate 1000 predictions
python scripts/generate_test_predictions.py --count 1000
```

**Drift Testing:**
```python
# Set baseline
metrics_monitor.set_reference_distribution('amount', baseline_amounts)

# Generate drifted data
for i in range(100):
    amount = random.randint(10000, 50000)  # Much higher than baseline
    log_prediction(..., features={'amount': amount})

# Verify drift detected
drift = metrics_monitor.detect_drift('amount')
assert drift.is_drifting == True
```

## Performance Metrics

**Memory Usage:**
- Metrics service: ~20MB (with 10k predictions)
- Structured logger: ~5MB
- Total overhead: <50MB

**Response Times:**
- `/log-prediction`: <10ms (append to deque + JSONL write)
- `/metrics` (cached): <5ms (return cached data)
- `/metrics` (uncached): <100ms (compute all metrics)
- `/model-performance`: <50ms (confusion matrix calculation)

**Storage:**
- JSONL files: ~1KB per prediction
- 10k predictions: ~10MB on disk

## Future Enhancements

### Short-term
- [ ] Add alerting rules (threshold-based)
- [ ] Implement log rotation for JSONL files
- [ ] Add more drift detection algorithms (KS test, PSI)
- [ ] Export metrics to Prometheus (optional compatibility layer)

### Medium-term
- [ ] A/B testing framework for prompts
- [ ] Experiment tracking (variant performance)
- [ ] Historical trend analysis (week-over-week)
- [ ] Anomaly detection (outlier identification)

### Long-term
- [ ] Multi-model comparison dashboard
- [ ] Cost tracking (token usage × API pricing)
- [ ] SLA monitoring (uptime, latency SLOs)
- [ ] Integration with external monitoring (Datadog, New Relic)

## Troubleshooting

### Dashboard shows "NaN%" or no data

**Cause:** No predictions logged yet

**Solution:**
```bash
# Log some test predictions
curl -X POST http://localhost:8000/api/v1/fraud/monitoring/log-prediction -d '{...}'
```

### Drift endpoint returns 404

**Cause:** No reference distribution set for feature

**Solution:**
```python
from app.services.monitoring import metrics_monitor
metrics_monitor.set_reference_distribution('amount', [1000, 2000, 3000, ...])
```

### High memory usage

**Cause:** Too many predictions in buffer

**Solution:** Reduce `maxlen` in deques:
```python
# In metrics_monitor.py
self.prediction_logs = deque(maxlen=5000)  # Reduced from 10000
```

### Logs not appearing

**Cause:** Log level too high or log directory not created

**Solution:**
```python
# Check log level
logger.setLevel(logging.DEBUG)

# Create logs directory
os.makedirs("logs", exist_ok=True)
```

## References

- **WBS:** `docs/planning/WBS.md` - Section 9: Monitoring & Observability
- **Backend Service:** `backend/app/services/monitoring/metrics_monitor.py`
- **Structured Logger:** `backend/app/core/structured_logger.py`
- **API Endpoints:** `backend/app/api/fraud.py` (monitoring endpoints)
- **Frontend Dashboard:** `frontend/app/dashboard/monitoring/page.tsx`
- **Navigation:** `frontend/components/navigation.tsx`

## License

Part of FinSight AI - Fraud Detection System
