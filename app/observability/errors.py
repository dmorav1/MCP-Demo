"""
Error tracking with Sentry integration.
"""

import os
import logging
from typing import Optional, Dict, Any
from fastapi import Request

logger = logging.getLogger(__name__)

# Try to import sentry_sdk
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    logger.warning("sentry-sdk not installed, error tracking disabled")


def setup_error_tracking(
    dsn: Optional[str] = None,
    environment: str = "development",
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1
) -> bool:
    """
    Set up Sentry error tracking.
    
    Args:
        dsn: Sentry DSN
        environment: Environment name
        traces_sample_rate: Percentage of traces to capture (0.0 to 1.0)
        profiles_sample_rate: Percentage of profiles to capture (0.0 to 1.0)
        
    Returns:
        True if successfully initialized, False otherwise
    """
    if not SENTRY_AVAILABLE:
        logger.warning("Sentry SDK not available, skipping error tracking setup")
        return False
    
    if not dsn:
        dsn = os.getenv("SENTRY_DSN")
    
    if not dsn:
        logger.info("Sentry DSN not configured, error tracking disabled")
        return False
    
    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            send_default_pii=False,  # Don't send personal data by default
            attach_stacktrace=True,
            debug=False,
        )
        logger.info(f"Sentry error tracking initialized for environment: {environment}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def capture_exception(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: str = "error"
) -> Optional[str]:
    """
    Capture an exception with Sentry.
    
    Args:
        error: The exception to capture
        context: Additional context
        level: Error level (error, warning, info)
        
    Returns:
        Event ID if captured, None otherwise
    """
    if not SENTRY_AVAILABLE:
        return None
    
    try:
        with sentry_sdk.push_scope() as scope:
            # Set level
            scope.level = level
            
            # Add context
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)
            
            # Capture exception
            event_id = sentry_sdk.capture_exception(error)
            return event_id
    except Exception as e:
        logger.error(f"Failed to capture exception with Sentry: {e}")
        return None


def capture_message(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Capture a message with Sentry.
    
    Args:
        message: The message to capture
        level: Message level
        context: Additional context
        
    Returns:
        Event ID if captured, None otherwise
    """
    if not SENTRY_AVAILABLE:
        return None
    
    try:
        with sentry_sdk.push_scope() as scope:
            # Set level
            scope.level = level
            
            # Add context
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)
            
            # Capture message
            event_id = sentry_sdk.capture_message(message)
            return event_id
    except Exception as e:
        logger.error(f"Failed to capture message with Sentry: {e}")
        return None


def set_user_context(user_id: Optional[str] = None, **kwargs):
    """
    Set user context for error tracking.
    
    Args:
        user_id: User ID
        **kwargs: Additional user attributes
    """
    if not SENTRY_AVAILABLE:
        return
    
    try:
        user_data = {"id": user_id} if user_id else {}
        user_data.update(kwargs)
        sentry_sdk.set_user(user_data)
    except Exception as e:
        logger.error(f"Failed to set user context: {e}")


def set_transaction_name(name: str):
    """Set the transaction name for the current scope."""
    if not SENTRY_AVAILABLE:
        return
    
    try:
        sentry_sdk.set_transaction_name(name)
    except Exception as e:
        logger.error(f"Failed to set transaction name: {e}")


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
):
    """
    Add a breadcrumb for debugging.
    
    Args:
        message: Breadcrumb message
        category: Category of the breadcrumb
        level: Level (debug, info, warning, error)
        data: Additional data
    """
    if not SENTRY_AVAILABLE:
        return
    
    try:
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {}
        )
    except Exception as e:
        logger.error(f"Failed to add breadcrumb: {e}")
