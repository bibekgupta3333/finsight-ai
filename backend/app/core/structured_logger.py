"""
Structured JSON Logger

Production-ready structured logging with context enrichment.
Optimized for observability and log aggregation.

Features:
- JSON-formatted logs for machine parsing
- Contextual information (request_id, user_id, etc.)
- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Automatic timestamps and metadata
- Exception tracking with stack traces
- Performance timing decorators
"""

import json
import logging
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextvars import ContextVar
from pathlib import Path


# Context variables for request-scoped data
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
transaction_id_var: ContextVar[str] = ContextVar("transaction_id", default="")


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add context variables
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id

        transaction_id = transaction_id_var.get()
        if transaction_id:
            log_data["transaction_id"] = transaction_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # Add custom fields from extra
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger:
    """
    Structured logger with context management.

    Usage:
        logger = StructuredLogger("fraud_detection")
        logger.info("Processing transaction", extra={"amount": 1000})

        with logger.context(transaction_id="tx_123"):
            logger.info("Transaction validated")
    """

    def __init__(self, name: str, log_dir: str = "logs"):
        """Initialize structured logger"""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Create log directory
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Console handler (JSON)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(JSONFormatter())

        # File handler (JSON)
        file_handler = logging.FileHandler(log_path / f"{name}.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())

        # Error file handler (separate errors)
        error_handler = logging.FileHandler(log_path / f"{name}_errors.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)

    def _log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """Internal log method with extra fields"""
        log_record = self.logger.makeRecord(
            self.logger.name,
            getattr(logging, level.upper()),
            "(unknown file)",
            0,
            message,
            (),
            None
        )
        if extra:
            log_record.extra_fields = extra
        self.logger.handle(log_record)

    def debug(self, message: str, **extra):
        """Log debug message"""
        self._log("debug", message, extra)

    def info(self, message: str, **extra):
        """Log info message"""
        self._log("info", message, extra)

    def warning(self, message: str, **extra):
        """Log warning message"""
        self._log("warning", message, extra)

    def error(self, message: str, **extra):
        """Log error message"""
        self._log("error", message, extra)

    def critical(self, message: str, **extra):
        """Log critical message"""
        self._log("critical", message, extra)

    def exception(self, message: str, exc_info=True, **extra):
        """Log exception with traceback"""
        log_record = self.logger.makeRecord(
            self.logger.name,
            logging.ERROR,
            "(unknown file)",
            0,
            message,
            (),
            exc_info if exc_info is True else None
        )
        if extra:
            log_record.extra_fields = extra
        self.logger.handle(log_record)

    def context(self, **kwargs):
        """Context manager for scoped logging context"""
        return LoggingContext(**kwargs)


class LoggingContext:
    """Context manager for request-scoped logging context"""

    def __init__(self, **kwargs):
        self.context = kwargs
        self.tokens = {}

    def __enter__(self):
        # Set context variables
        if "request_id" in self.context:
            self.tokens["request_id"] = request_id_var.set(self.context["request_id"])
        if "user_id" in self.context:
            self.tokens["user_id"] = user_id_var.set(self.context["user_id"])
        if "transaction_id" in self.context:
            self.tokens["transaction_id"] = transaction_id_var.set(self.context["transaction_id"])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Reset context variables
        for var_name, token in self.tokens.items():
            if var_name == "request_id":
                request_id_var.reset(token)
            elif var_name == "user_id":
                user_id_var.reset(token)
            elif var_name == "transaction_id":
                transaction_id_var.reset(token)


def log_execution_time(logger: StructuredLogger, operation_name: str):
    """
    Decorator to log execution time of a function.

    Usage:
        @log_execution_time(logger, "fraud_detection")
        def detect_fraud(transaction):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"{operation_name} completed",
                    operation=operation_name,
                    duration_ms=elapsed_ms,
                    status="success"
                )
                return result
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"{operation_name} failed",
                    operation=operation_name,
                    duration_ms=elapsed_ms,
                    status="error",
                    error=str(e)
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"{operation_name} completed",
                    operation=operation_name,
                    duration_ms=elapsed_ms,
                    status="success"
                )
                return result
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"{operation_name} failed",
                    operation=operation_name,
                    duration_ms=elapsed_ms,
                    status="error",
                    error=str(e)
                )
                raise

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Application loggers
fraud_logger = StructuredLogger("fraud_detection")
api_logger = StructuredLogger("api")
security_logger = StructuredLogger("security")
monitor_logger = StructuredLogger("monitoring")
