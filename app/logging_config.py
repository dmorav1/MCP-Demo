import logging
import sys
from datetime import datetime
import os


def setup_logging(log_level: str = "INFO"):
    """
    Set up comprehensive logging configuration for the MCP Backend
    """

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create logs directory if it doesn't exist
    log_dir = "/app/logs" if os.path.exists("/app") else "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler with color coding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(simple_formatter)

    # File handler for all logs
    file_handler = logging.FileHandler(
        f"{log_dir}/mcp-backend.log", mode="a", encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Error file handler for errors only
    error_handler = logging.FileHandler(
        f"{log_dir}/errors.log", mode="a", encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    # Configure specific loggers
    loggers_config = {
        "app.main": numeric_level,
        "app.services": numeric_level,
        "app.crud": numeric_level,
        "app.database": numeric_level,
        "app.models": numeric_level,
        "app.schemas": numeric_level,
        "uvicorn": logging.WARNING,
        "uvicorn.access": logging.WARNING,
        "fastapi": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,  # Reduce SQL query logs
        "sqlalchemy.pool": logging.WARNING,
        "openai": logging.WARNING,
    }

    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

    # Log startup message
    startup_logger = logging.getLogger("app.startup")
    startup_logger.info("=" * 60)
    startup_logger.info("🚀 MCP Backend Logging System Initialized")
    startup_logger.info(f"📊 Log Level: {log_level}")
    startup_logger.info(f"📁 Log Directory: {log_dir}")
    startup_logger.info(
        f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    startup_logger.info("=" * 60)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name
    """
    return logging.getLogger(name)


# Custom log level for tracking embeddings and API calls
logging.addLevelName(25, "API_CALL")


def api_call(self, message, *args, **kwargs):
    if self.isEnabledFor(25):
        self._log(25, message, args, **kwargs)


logging.Logger.api_call = api_call

# Custom log level for database operations
logging.addLevelName(35, "DATABASE")


def database(self, message, *args, **kwargs):
    if self.isEnabledFor(35):
        self._log(35, message, args, **kwargs)


logging.Logger.database = database
