"""
Metrics Monitor Service

Lightweight monitoring system for ML model performance, latency tracking,
error monitoring, and drift detection. Optimized for local development.

Features:
- Model performance metrics (F1, precision, recall)
- Prediction distribution tracking
- Data drift detection (feature distributions)
- Token usage monitoring
- Latency percentiles (p50, p95, p99)
- Error rate tracking
- Real-time dashboards
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from pydantic import BaseModel, Field


@dataclass
class ModelMetrics:
    """Model performance metrics"""
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
    """Latency tracking metrics"""
    timestamp: str
    endpoint: str
    p50: float
    p95: float
    p99: float
    mean: float
    min: float
    max: float
    count: int


@dataclass
class ErrorMetrics:
    """Error tracking metrics"""
    timestamp: str
    error_type: str
    error_count: int
    error_rate: float
    total_requests: int


@dataclass
class DriftMetrics:
    """Data drift detection metrics"""
    timestamp: str
    feature_name: str
    reference_mean: float
    current_mean: float
    reference_std: float
    current_std: float
    drift_score: float
    is_drifting: bool


class PredictionLog(BaseModel):
    """Individual prediction log"""
    transaction_id: str
    timestamp: str
    predicted_label: str
    true_label: Optional[str] = None
    confidence: float
    features: Dict[str, Any]
    latency_ms: float
    token_count: Optional[int] = None


class MetricsMonitor:
    """
    Metrics monitoring service for fraud detection system.

    Tracks:
    - ML model performance (confusion matrix, F1, precision, recall)
    - Latency percentiles across endpoints
    - Error rates by type
    - Token usage for LLM calls
    - Data drift detection
    - Prediction distributions
    """

    def __init__(self, storage_dir: str = "data/monitoring"):
        """Initialize metrics monitor"""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # In-memory storage for real-time metrics (bounded)
        self.prediction_logs: deque = deque(maxlen=10000)  # Last 10k predictions
        self.latency_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.error_buffer: deque = deque(maxlen=1000)
        self.token_buffer: deque = deque(maxlen=1000)

        # Reference distributions for drift detection (initialized from historical data)
        self.reference_distributions: Dict[str, Dict[str, float]] = {}

        # Metrics cache (recomputed periodically)
        self.metrics_cache: Dict[str, Any] = {}
        self.cache_ttl = 60  # seconds
        self.last_cache_update = 0


    # ==================== Prediction Logging ====================

    def log_prediction(
        self,
        transaction_id: str,
        predicted_label: str,
        true_label: Optional[str],
        confidence: float,
        features: Dict[str, Any],
        latency_ms: float,
        token_count: Optional[int] = None
    ):
        """
        Log individual prediction with ground truth label.

        Args:
            transaction_id: Unique transaction ID
            predicted_label: Model prediction (fraud/legitimate)
            true_label: Ground truth label (if available)
            confidence: Prediction confidence (0-1)
            features: Transaction features
            latency_ms: Prediction latency in milliseconds
            token_count: Number of tokens used (for LLM)
        """
        log = PredictionLog(
            transaction_id=transaction_id,
            timestamp=datetime.now().isoformat(),
            predicted_label=predicted_label,
            true_label=true_label,
            confidence=confidence,
            features=features,
            latency_ms=latency_ms,
            token_count=token_count
        )

        self.prediction_logs.append(log.model_dump())

        # Persist to disk (append-only log)
        log_file = self.storage_dir / "prediction_logs.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log.model_dump()) + "\n")


    def log_latency(self, endpoint: str, latency_ms: float):
        """Log endpoint latency"""
        self.latency_buffer[endpoint].append({
            "timestamp": datetime.now().isoformat(),
            "latency_ms": latency_ms
        })


    def log_error(self, error_type: str, endpoint: str, details: str):
        """Log error occurrence"""
        self.error_buffer.append({
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "endpoint": endpoint,
            "details": details
        })

        # Persist errors
        error_file = self.storage_dir / "errors.jsonl"
        with open(error_file, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "error_type": error_type,
                "endpoint": endpoint,
                "details": details
            }) + "\n")


    def log_token_usage(self, transaction_id: str, token_count: int, model_name: str):
        """Log LLM token usage"""
        self.token_buffer.append({
            "timestamp": datetime.now().isoformat(),
            "transaction_id": transaction_id,
            "token_count": token_count,
            "model_name": model_name
        })


    # ==================== Model Performance Metrics ====================

    def calculate_model_metrics(self, time_window_hours: int = 24) -> ModelMetrics:
        """
        Calculate model performance metrics from logged predictions.

        Args:
            time_window_hours: Time window for metrics calculation

        Returns:
            ModelMetrics with confusion matrix and derived metrics
        """
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

        # Filter predictions with ground truth within time window
        labeled_predictions = [
            log for log in self.prediction_logs
            if log.get("true_label") is not None
            and datetime.fromisoformat(log["timestamp"]) > cutoff_time
        ]

        if not labeled_predictions:
            # Return zero metrics if no labeled data
            return ModelMetrics(
                timestamp=datetime.now().isoformat(),
                true_positives=0,
                true_negatives=0,
                false_positives=0,
                false_negatives=0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                accuracy=0.0,
                total_predictions=0
            )

        # Calculate confusion matrix
        tp = sum(1 for log in labeled_predictions
                if log["predicted_label"] == "fraud" and log["true_label"] == "fraud")
        tn = sum(1 for log in labeled_predictions
                if log["predicted_label"] == "legitimate" and log["true_label"] == "legitimate")
        fp = sum(1 for log in labeled_predictions
                if log["predicted_label"] == "fraud" and log["true_label"] == "legitimate")
        fn = sum(1 for log in labeled_predictions
                if log["predicted_label"] == "legitimate" and log["true_label"] == "fraud")

        total = tp + tn + fp + fn

        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / total if total > 0 else 0.0

        return ModelMetrics(
            timestamp=datetime.now().isoformat(),
            true_positives=tp,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            total_predictions=total
        )


    def get_prediction_distribution(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get prediction distribution statistics"""
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

        recent_predictions = [
            log for log in self.prediction_logs
            if datetime.fromisoformat(log["timestamp"]) > cutoff_time
        ]

        if not recent_predictions:
            return {
                "fraud_count": 0,
                "legitimate_count": 0,
                "fraud_rate": 0.0,
                "avg_confidence": 0.0,
                "confidence_distribution": {}
            }

        fraud_count = sum(1 for log in recent_predictions if log["predicted_label"] == "fraud")
        legitimate_count = len(recent_predictions) - fraud_count

        confidences = [log["confidence"] for log in recent_predictions]

        return {
            "fraud_count": fraud_count,
            "legitimate_count": legitimate_count,
            "fraud_rate": fraud_count / len(recent_predictions),
            "avg_confidence": np.mean(confidences),
            "confidence_distribution": {
                "min": float(np.min(confidences)),
                "max": float(np.max(confidences)),
                "p25": float(np.percentile(confidences, 25)),
                "p50": float(np.percentile(confidences, 50)),
                "p75": float(np.percentile(confidences, 75))
            }
        }


    # ==================== Latency Monitoring ====================

    def calculate_latency_metrics(self, endpoint: str) -> Optional[LatencyMetrics]:
        """Calculate latency percentiles for an endpoint"""
        if endpoint not in self.latency_buffer or not self.latency_buffer[endpoint]:
            return None

        latencies = [entry["latency_ms"] for entry in self.latency_buffer[endpoint]]

        return LatencyMetrics(
            timestamp=datetime.now().isoformat(),
            endpoint=endpoint,
            p50=float(np.percentile(latencies, 50)),
            p95=float(np.percentile(latencies, 95)),
            p99=float(np.percentile(latencies, 99)),
            mean=float(np.mean(latencies)),
            min=float(np.min(latencies)),
            max=float(np.max(latencies)),
            count=len(latencies)
        )


    def get_all_latency_metrics(self) -> Dict[str, LatencyMetrics]:
        """Get latency metrics for all endpoints"""
        metrics = {}
        for endpoint in self.latency_buffer.keys():
            endpoint_metrics = self.calculate_latency_metrics(endpoint)
            if endpoint_metrics:
                metrics[endpoint] = asdict(endpoint_metrics)
        return metrics


    # ==================== Error Monitoring ====================

    def calculate_error_metrics(self, time_window_hours: int = 24) -> List[ErrorMetrics]:
        """Calculate error rates by type"""
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

        recent_errors = [
            err for err in self.error_buffer
            if datetime.fromisoformat(err["timestamp"]) > cutoff_time
        ]

        # Group by error type
        error_counts = defaultdict(int)
        for err in recent_errors:
            error_counts[err["error_type"]] += 1

        # Calculate total requests (from latency logs)
        total_requests = sum(len(buffer) for buffer in self.latency_buffer.values())

        error_metrics = []
        for error_type, count in error_counts.items():
            error_rate = count / total_requests if total_requests > 0 else 0.0
            error_metrics.append(ErrorMetrics(
                timestamp=datetime.now().isoformat(),
                error_type=error_type,
                error_count=count,
                error_rate=error_rate,
                total_requests=total_requests
            ))

        return error_metrics


    # ==================== Token Usage Tracking ====================

    def get_token_usage_stats(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get token usage statistics"""
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

        recent_tokens = [
            entry for entry in self.token_buffer
            if datetime.fromisoformat(entry["timestamp"]) > cutoff_time
        ]

        if not recent_tokens:
            return {
                "total_tokens": 0,
                "avg_tokens_per_request": 0.0,
                "max_tokens": 0,
                "min_tokens": 0,
                "total_requests": 0
            }

        token_counts = [entry["token_count"] for entry in recent_tokens]

        return {
            "total_tokens": sum(token_counts),
            "avg_tokens_per_request": np.mean(token_counts),
            "max_tokens": max(token_counts),
            "min_tokens": min(token_counts),
            "total_requests": len(recent_tokens),
            "p50": float(np.percentile(token_counts, 50)),
            "p95": float(np.percentile(token_counts, 95)),
            "p99": float(np.percentile(token_counts, 99))
        }


    # ==================== Data Drift Detection ====================

    def set_reference_distribution(self, feature_name: str, values: List[float]):
        """Set reference distribution for drift detection"""
        self.reference_distributions[feature_name] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values))
        }


    def detect_drift(self, feature_name: str, time_window_hours: int = 24) -> Optional[DriftMetrics]:
        """
        Detect data drift for a feature using statistical methods.

        Uses mean shift and variance change as drift indicators.
        """
        if feature_name not in self.reference_distributions:
            return None

        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

        # Extract feature values from recent predictions
        recent_values = []
        for log in self.prediction_logs:
            if datetime.fromisoformat(log["timestamp"]) > cutoff_time:
                if feature_name in log["features"]:
                    recent_values.append(log["features"][feature_name])

        if len(recent_values) < 30:  # Need minimum samples
            return None

        ref = self.reference_distributions[feature_name]
        current_mean = float(np.mean(recent_values))
        current_std = float(np.std(recent_values))

        # Calculate drift score (normalized mean shift + variance change)
        mean_shift = abs(current_mean - ref["mean"]) / (ref["std"] + 1e-6)
        variance_change = abs(current_std - ref["std"]) / (ref["std"] + 1e-6)
        drift_score = (mean_shift + variance_change) / 2

        # Threshold for drift detection
        is_drifting = drift_score > 0.5

        return DriftMetrics(
            timestamp=datetime.now().isoformat(),
            feature_name=feature_name,
            reference_mean=ref["mean"],
            current_mean=current_mean,
            reference_std=ref["std"],
            current_std=current_std,
            drift_score=drift_score,
            is_drifting=is_drifting
        )


    # ==================== Dashboard Data ====================

    def get_dashboard_data(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data.

        Returns all metrics for visualization in frontend.
        """
        # Check cache
        now = time.time()
        if (now - self.last_cache_update) < self.cache_ttl and self.metrics_cache:
            return self.metrics_cache

        # Recalculate metrics
        model_metrics = self.calculate_model_metrics(time_window_hours)
        latency_metrics = self.get_all_latency_metrics()
        error_metrics = self.calculate_error_metrics(time_window_hours)
        token_stats = self.get_token_usage_stats(time_window_hours)
        prediction_dist = self.get_prediction_distribution(time_window_hours)

        # Detect drift for common features
        drift_metrics = {}
        for feature_name in ["amount", "oldbalanceOrg", "newbalanceOrig"]:
            drift = self.detect_drift(feature_name, time_window_hours)
            if drift:
                drift_metrics[feature_name] = asdict(drift)

        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "time_window_hours": time_window_hours,
            "model_performance": asdict(model_metrics),
            "latency": latency_metrics,
            "errors": [asdict(err) for err in error_metrics],
            "token_usage": token_stats,
            "prediction_distribution": prediction_dist,
            "drift_detection": drift_metrics,
            "system_health": {
                "total_predictions": len(self.prediction_logs),
                "endpoints_monitored": len(self.latency_buffer),
                "error_count": len(self.error_buffer)
            }
        }

        # Update cache
        self.metrics_cache = dashboard_data
        self.last_cache_update = now

        return dashboard_data


    def get_time_series_data(
        self,
        metric_name: str,
        time_window_hours: int = 24,
        granularity_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for a metric.

        Args:
            metric_name: 'fraud_rate', 'latency', 'error_rate', 'token_usage'
            time_window_hours: Time window to query
            granularity_minutes: Time bucket size

        Returns:
            List of {timestamp, value} dictionaries
        """
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

        # Create time buckets
        num_buckets = int((time_window_hours * 60) / granularity_minutes)
        buckets = defaultdict(list)

        for log in self.prediction_logs:
            log_time = datetime.fromisoformat(log["timestamp"])
            if log_time > cutoff_time:
                # Assign to bucket
                minutes_since_cutoff = (log_time - cutoff_time).total_seconds() / 60
                bucket_idx = int(minutes_since_cutoff / granularity_minutes)
                buckets[bucket_idx].append(log)

        # Calculate metric for each bucket
        time_series = []
        for i in range(num_buckets):
            bucket_time = cutoff_time + timedelta(minutes=i * granularity_minutes)
            bucket_data = buckets.get(i, [])

            if metric_name == "fraud_rate":
                if bucket_data:
                    fraud_count = sum(1 for log in bucket_data if log["predicted_label"] == "fraud")
                    value = fraud_count / len(bucket_data)
                else:
                    value = 0.0
            elif metric_name == "avg_confidence":
                if bucket_data:
                    value = np.mean([log["confidence"] for log in bucket_data])
                else:
                    value = 0.0
            else:
                value = 0.0

            time_series.append({
                "timestamp": bucket_time.isoformat(),
                "value": float(value)
            })

        return time_series


# Global instance
metrics_monitor = MetricsMonitor()
