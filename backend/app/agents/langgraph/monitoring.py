"""
LangGraph Monitoring and Tracing Integration (Phase 8.4).

Provides:
1. LangSmith tracing for agent execution visualization (optional)
2. MLflow metrics integration for graph execution tracking
3. Performance monitoring for multi-agent patterns

Usage:
    # Enable LangSmith tracing (optional)
    from app.agents.langgraph.monitoring import enable_langsmith_tracing
    enable_langsmith_tracing()

    # Log metrics to MLflow
    from app.agents.langgraph.monitoring import log_graph_metrics
    await log_graph_metrics(pattern_name, execution_time, state)
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)


# ============================================================================
# LangSmith Tracing (Phase 8.4 - Optional)
# ============================================================================


def enable_langsmith_tracing(api_key: Optional[str] = None, project: str = "finsight-ai"):
    """
    Enable LangSmith tracing for LangGraph execution visualization.

    LangSmith provides:
    - Visual execution traces of agent graphs
    - Node execution timing
    - State transitions
    - Error tracking

    Args:
        api_key: LangSmith API key (or set LANGCHAIN_API_KEY env var)
        project: Project name for organizing traces

    Note:
        This is optional but recommended for development.
        Free tier: 1,000 traces/month
        Get API key: https://smith.langchain.com/
    """
    try:
        # Check if API key is provided or in environment
        api_key = api_key or os.getenv("LANGCHAIN_API_KEY")

        if not api_key:
            logger.warning(
                "⚠️  LangSmith API key not found. Tracing disabled.\n"
                "   To enable: Set LANGCHAIN_API_KEY env var or pass api_key parameter.\n"
                "   Get free API key: https://smith.langchain.com/"
            )
            return False

        # Enable tracing
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGCHAIN_PROJECT"] = project

        logger.info(f"✅ LangSmith tracing enabled (project: {project})")
        logger.info(f"   View traces at: https://smith.langchain.com/")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to enable LangSmith tracing: {e}")
        return False


def disable_langsmith_tracing():
    """Disable LangSmith tracing."""
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    logger.info("🔴 LangSmith tracing disabled")


# ============================================================================
# MLflow Metrics Integration (Phase 8.4)
# ============================================================================


async def log_graph_metrics(
    pattern_name: str,
    execution_time: float,
    state: Dict[str, Any],
    mlflow_run_name: Optional[str] = None,
):
    """
    Log LangGraph execution metrics to MLflow.

    Metrics logged:
    - Node execution time
    - Total graph execution time
    - State size (memory usage)
    - Number of agents involved
    - Consensus metrics (agreement level, confidence)

    Args:
        pattern_name: Name of multi-agent pattern
        execution_time: Total execution time in seconds
        state: Final graph state
        mlflow_run_name: Optional MLflow run name
    """
    try:
        import mlflow

        # Start or use existing MLflow run
        active_run = mlflow.active_run()
        if active_run is None and mlflow_run_name:
            mlflow.start_run(run_name=mlflow_run_name)

        # Log pattern metadata
        mlflow.log_param("pattern_name", pattern_name)
        mlflow.log_param("transaction_id", state.get('transaction_id', 'unknown'))

        # Log execution metrics
        mlflow.log_metric("graph_execution_time", execution_time)
        mlflow.log_metric("risk_score", state.get('risk_score', 0.0))
        mlflow.log_metric("confidence", state.get('confidence', 0.0))
        mlflow.log_metric("agreement_level", state.get('agreement_level', 0.0))

        # Log pattern-specific metrics
        if 'num_workers' in state:
            mlflow.log_metric("num_workers", state['num_workers'])
        if 'swarm_size' in state:
            mlflow.log_metric("swarm_size", state['swarm_size'])
        if 'fraud_votes' in state:
            mlflow.log_metric("fraud_votes", state['fraud_votes'])
        if 'disagreement_score' in state:
            mlflow.log_metric("disagreement_score", state['disagreement_score'])

        # Log state size (memory usage indicator)
        state_size = len(str(state))
        mlflow.log_metric("state_size_bytes", state_size)

        # Log result
        mlflow.log_metric("is_fraud", 1.0 if state.get('is_fraud') else 0.0)

        logger.debug(f"📊 Logged MLflow metrics for {pattern_name}")

        # Close run if we started it
        if active_run is None and mlflow_run_name:
            mlflow.end_run()

    except ImportError:
        logger.warning("⚠️  MLflow not available - metrics logging skipped")
    except Exception as e:
        logger.error(f"❌ Failed to log MLflow metrics: {e}")


# ============================================================================
# Performance Monitoring
# ============================================================================


class GraphExecutionTimer:
    """Context manager for timing graph execution."""

    def __init__(self, pattern_name: str):
        """Initialize timer."""
        self.pattern_name = pattern_name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        """Start timer."""
        self.start_time = time.time()
        logger.debug(f"⏱️  Starting {self.pattern_name} execution")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and log duration."""
        self.end_time = time.time()
        duration = self.end_time - self.start_time

        if exc_type is None:
            logger.info(f"✅ {self.pattern_name} completed in {duration:.2f}s")
        else:
            logger.error(f"❌ {self.pattern_name} failed after {duration:.2f}s: {exc_val}")

        return False  # Don't suppress exceptions

    @property
    def duration(self) -> float:
        """Get execution duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


def log_node_execution(node_name: str, execution_time: float):
    """
    Log individual node execution time.

    Args:
        node_name: Name of the graph node
        execution_time: Execution time in seconds
    """
    logger.debug(f"  ├─ {node_name}: {execution_time*1000:.1f}ms")


# ============================================================================
# Memory Usage Tracking (M4 Pro Optimization)
# ============================================================================


def get_memory_usage() -> Dict[str, float]:
    """
    Get current memory usage.

    Returns:
        Dictionary with memory metrics in MB
    """
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()

        return {
            'rss_mb': mem_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': mem_info.vms / 1024 / 1024,  # Virtual Memory Size
        }
    except ImportError:
        return {'rss_mb': 0.0, 'vms_mb': 0.0}


def log_memory_usage(context: str = ""):
    """Log current memory usage."""
    mem = get_memory_usage()
    if mem['rss_mb'] > 0:
        logger.debug(f"💾 Memory usage {context}: {mem['rss_mb']:.1f} MB (RSS)")


# ============================================================================
# Tracing Decorator
# ============================================================================


def trace_graph_execution(pattern_name: str):
    """
    Decorator to trace graph execution with metrics.

    Usage:
        @trace_graph_execution("manager_worker")
        async def analyze(...):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with GraphExecutionTimer(pattern_name):
                log_memory_usage(f"[{pattern_name}] Start")
                result = await func(*args, **kwargs)
                log_memory_usage(f"[{pattern_name}] End")
                return result
        return wrapper
    return decorator


# ============================================================================
# Configuration
# ============================================================================


def setup_monitoring(
    enable_langsmith: bool = False,
    langsmith_api_key: Optional[str] = None,
    langsmith_project: str = "finsight-ai",
):
    """
    Setup all monitoring integrations.

    Args:
        enable_langsmith: Whether to enable LangSmith tracing
        langsmith_api_key: LangSmith API key (optional)
        langsmith_project: LangSmith project name

    Returns:
        Dictionary with enabled features
    """
    enabled_features = {
        'langsmith': False,
        'mlflow': False,
    }

    # LangSmith tracing
    if enable_langsmith:
        enabled_features['langsmith'] = enable_langsmith_tracing(
            api_key=langsmith_api_key,
            project=langsmith_project,
        )

    # Check MLflow availability
    try:
        import mlflow
        enabled_features['mlflow'] = True
        logger.info("✅ MLflow metrics enabled")
    except ImportError:
        logger.warning("⚠️  MLflow not available")

    return enabled_features
