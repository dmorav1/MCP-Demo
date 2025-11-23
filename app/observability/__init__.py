"""
Observability package for MCP Backend.
Provides logging, metrics, tracing, and error tracking.
"""

from .logger import get_logger, setup_structured_logging
from .metrics import metrics, PrometheusMetrics
from .tracing import setup_tracing, trace_function, instrument_fastapi, instrument_sqlalchemy
from .health import HealthChecker
from .errors import setup_error_tracking

__all__ = [
    "get_logger",
    "setup_structured_logging",
    "metrics",
    "PrometheusMetrics",
    "setup_tracing",
    "trace_function",
    "instrument_fastapi",
    "instrument_sqlalchemy",
    "setup_error_tracking",
    "HealthChecker",
]
