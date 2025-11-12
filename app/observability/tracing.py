"""
OpenTelemetry distributed tracing integration.
"""

import os
import logging
from typing import Optional, Callable
from functools import wraps
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

# Optional exporters
try:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    JAEGER_AVAILABLE = True
except ImportError:
    JAEGER_AVAILABLE = False

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    OTLP_AVAILABLE = True
except ImportError:
    OTLP_AVAILABLE = False

logger = logging.getLogger(__name__)


def setup_tracing(
    service_name: str = "mcp-backend",
    service_version: str = "1.0.0",
    jaeger_host: Optional[str] = None,
    jaeger_port: int = 6831,
    otlp_endpoint: Optional[str] = None,
    console_export: bool = False
) -> trace.Tracer:
    """
    Set up OpenTelemetry tracing.
    
    Args:
        service_name: Name of the service
        service_version: Version of the service
        jaeger_host: Jaeger agent host (optional)
        jaeger_port: Jaeger agent port
        otlp_endpoint: OTLP endpoint (optional)
        console_export: Export to console for debugging
        
    Returns:
        Configured tracer
    """
    # Create resource with service information
    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "environment": os.getenv("ENVIRONMENT", "development"),
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Add exporters
    exporters_configured = False
    
    # Jaeger exporter
    if jaeger_host and JAEGER_AVAILABLE:
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name=jaeger_host,
                agent_port=jaeger_port,
            )
            provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            logger.info(f"Jaeger tracing configured: {jaeger_host}:{jaeger_port}")
            exporters_configured = True
        except Exception as e:
            logger.warning(f"Failed to configure Jaeger exporter: {e}")
    elif jaeger_host and not JAEGER_AVAILABLE:
        logger.warning("Jaeger exporter not available (install opentelemetry-exporter-jaeger)")
    
    # OTLP exporter
    if otlp_endpoint and OTLP_AVAILABLE:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OTLP tracing configured: {otlp_endpoint}")
            exporters_configured = True
        except Exception as e:
            logger.warning(f"Failed to configure OTLP exporter: {e}")
    elif otlp_endpoint and not OTLP_AVAILABLE:
        logger.warning("OTLP exporter not available (install opentelemetry-exporter-otlp)")
    
    # Console exporter for debugging
    if console_export and not exporters_configured:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("Console tracing configured (debug mode)")
        exporters_configured = True
    
    if exporters_configured:
        # Set as global tracer provider
        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry tracing initialized")
    else:
        logger.info("No tracing exporters configured, tracing disabled")
    
    # Return tracer
    return trace.get_tracer(__name__)


def instrument_fastapi(app):
    """Instrument FastAPI application with tracing."""
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented with tracing")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")


def instrument_sqlalchemy(engine):
    """Instrument SQLAlchemy engine with tracing."""
    try:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy instrumented with tracing")
    except Exception as e:
        logger.warning(f"Failed to instrument SQLAlchemy: {e}")


def trace_function(name: Optional[str] = None, attributes: Optional[dict] = None):
    """
    Decorator to trace function execution.
    
    Args:
        name: Span name (defaults to function name)
        attributes: Additional span attributes
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Add function metadata
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Add function metadata
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def get_current_span():
    """Get the current active span."""
    return trace.get_current_span()


def add_span_attributes(**attributes):
    """Add attributes to the current span."""
    span = get_current_span()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
