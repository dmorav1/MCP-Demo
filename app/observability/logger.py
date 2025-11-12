"""
Structured JSON logging with contextual information.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class ContextualJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that includes contextual information."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno
        
        # Add contextual fields if available
        request_id = request_id_var.get()
        if request_id:
            log_record["request_id"] = request_id
            
        user_id = user_id_var.get()
        if user_id:
            log_record["user_id"] = user_id
        
        # Add process info
        log_record["process"] = os.getpid()
        log_record["thread"] = record.thread
        
        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)


def setup_structured_logging(
    log_level: str = "INFO",
    use_json: bool = True,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up structured logging with JSON format.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        use_json: Whether to use JSON format (False for human-readable)
        log_file: Optional file path for file logging
        
    Returns:
        Configured root logger
    """
    # Check for stdio mode (MCP protocol)
    is_stdio_mode = os.getenv('MCP_TRANSPORT') == 'stdio'
    
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    
    # Create formatters
    if use_json:
        json_formatter = ContextualJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
        formatter = json_formatter
    else:
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler (skip in stdio mode)
    if not is_stdio_mode:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter if use_json else logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        root_logger.addHandler(file_handler)
    
    # Error file handler
    if log_file:
        error_log = log_file.replace('.log', '_errors.log')
        error_handler = logging.FileHandler(error_log, mode='a', encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
    
    # Configure library loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    
    if not is_stdio_mode:
        root_logger.info(
            "Structured logging initialized",
            extra={
                "log_level": log_level,
                "use_json": use_json,
                "log_file": log_file,
            }
        )
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


def set_request_context(request_id: Optional[str] = None, user_id: Optional[str] = None) -> None:
    """Set contextual information for the current request."""
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context() -> None:
    """Clear contextual information."""
    request_id_var.set(None)
    user_id_var.set(None)
