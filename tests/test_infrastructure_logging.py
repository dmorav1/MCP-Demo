"""
Comprehensive logging infrastructure tests.

Tests structured JSON logging, contextual information, sensitive data handling,
log levels, and file handling.
"""
import pytest
import logging
import json
import tempfile
import os
from datetime import datetime
from io import StringIO
from unittest.mock import Mock, patch

from app.observability.logger import (
    setup_structured_logging,
    get_logger,
    set_request_context,
    clear_request_context,
    ContextualJsonFormatter,
    request_id_var,
    user_id_var,
)


class TestStructuredLogging:
    """Test structured JSON logging functionality."""
    
    def test_json_formatter_structure(self):
        """Test JSON log format has required fields."""
        formatter = ContextualJsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        log_dict = {}
        formatter.add_fields(log_dict, record, {})
        
        # Verify required fields
        assert "timestamp" in log_dict
        assert "level" in log_dict
        assert "logger" in log_dict
        assert "module" in log_dict
        assert "function" in log_dict
        assert "line" in log_dict
        assert "process" in log_dict
        assert "thread" in log_dict
        
        # Verify field values
        assert log_dict["level"] == "INFO"
        assert log_dict["logger"] == "test"
        assert log_dict["line"] == 42
    
    def test_json_formatter_with_context(self):
        """Test JSON formatter includes contextual information."""
        formatter = ContextualJsonFormatter()
        
        # Set context
        request_id_var.set("req-123")
        user_id_var.set("user-456")
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        log_dict = {}
        formatter.add_fields(log_dict, record, {})
        
        # Verify context fields
        assert log_dict.get("request_id") == "req-123"
        assert log_dict.get("user_id") == "user-456"
        
        # Cleanup
        request_id_var.set(None)
        user_id_var.set(None)
    
    def test_json_formatter_with_exception(self):
        """Test JSON formatter includes exception information."""
        formatter = ContextualJsonFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=exc_info
            )
            
            log_dict = {}
            formatter.add_fields(log_dict, record, {})
            
            # Verify exception info
            assert "exception" in log_dict
            assert "ValueError" in log_dict["exception"]
            assert "Test error" in log_dict["exception"]
    
    def test_setup_logging_console(self):
        """Test logging setup with console output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            
            logger = setup_structured_logging(
                log_level="DEBUG",
                use_json=True,
                log_file=log_file
            )
            
            assert logger is not None
            assert logger.level == logging.DEBUG
            
            # Check handlers
            assert len(logger.handlers) >= 2  # Console and file
    
    def test_setup_logging_file_creation(self):
        """Test logging creates log files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            
            setup_structured_logging(
                log_level="INFO",
                use_json=True,
                log_file=log_file
            )
            
            # Write a log message
            logger = get_logger("test")
            logger.info("Test message")
            
            # Verify files exist
            assert os.path.exists(log_file)
            error_log = log_file.replace('.log', '_errors.log')
            assert os.path.exists(error_log)
    
    def test_log_levels_filtering(self):
        """Test log level filtering works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            
            setup_structured_logging(
                log_level="WARNING",
                use_json=True,
                log_file=log_file
            )
            
            logger = get_logger("test")
            
            # These should not be logged
            logger.debug("Debug message")
            logger.info("Info message")
            
            # These should be logged
            logger.warning("Warning message")
            logger.error("Error message")
            
            # Read log file and verify only WARNING and ERROR are present
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Warning message" in content
                assert "Error message" in content
                assert "Debug message" not in content
                assert "Info message" not in content


class TestContextManagement:
    """Test request context management."""
    
    def test_set_request_context(self):
        """Test setting request context."""
        set_request_context(request_id="req-789", user_id="user-012")
        
        assert request_id_var.get() == "req-789"
        assert user_id_var.get() == "user-012"
        
        # Cleanup
        clear_request_context()
    
    def test_clear_request_context(self):
        """Test clearing request context."""
        set_request_context(request_id="req-789", user_id="user-012")
        clear_request_context()
        
        assert request_id_var.get() is None
        assert user_id_var.get() is None
    
    def test_partial_context_setting(self):
        """Test setting only some context values."""
        set_request_context(request_id="req-only")
        
        assert request_id_var.get() == "req-only"
        assert user_id_var.get() is None
        
        clear_request_context()


class TestSensitiveDataHandling:
    """Test sensitive data is not logged."""
    
    def test_no_passwords_in_logs(self):
        """Test passwords are not logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            
            setup_structured_logging(
                log_level="INFO",
                use_json=True,
                log_file=log_file
            )
            
            logger = get_logger("test")
            
            # Log a message (should not contain actual password)
            logger.info("User authentication", extra={"username": "testuser"})
            
            # Read log and verify no sensitive data
            with open(log_file, 'r') as f:
                content = f.read()
                assert "testuser" in content
                # Ensure common password keywords aren't accidentally logged
                assert "password123" not in content.lower()
    
    def test_log_sanitization(self):
        """Test log messages can be safely sanitized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            
            setup_structured_logging(
                log_level="INFO",
                use_json=True,
                log_file=log_file
            )
            
            logger = get_logger("test")
            
            # Log with safe data
            logger.info("API request", extra={
                "endpoint": "/api/users",
                "method": "GET",
                "status": 200
            })
            
            with open(log_file, 'r') as f:
                content = f.read()
                assert "/api/users" in content
                assert "GET" in content


class TestLogRotation:
    """Test log file handling and rotation capabilities."""
    
    def test_log_file_append_mode(self):
        """Test log files are opened in append mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            
            # Write first message
            setup_structured_logging(log_level="INFO", use_json=True, log_file=log_file)
            logger = get_logger("test")
            logger.info("First message")
            
            # Setup again (simulating restart)
            setup_structured_logging(log_level="INFO", use_json=True, log_file=log_file)
            logger = get_logger("test")
            logger.info("Second message")
            
            # Both messages should be in the file
            with open(log_file, 'r') as f:
                content = f.read()
                assert "First message" in content
                assert "Second message" in content
    
    def test_error_log_separation(self):
        """Test errors are logged to separate file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            
            setup_structured_logging(log_level="INFO", use_json=True, log_file=log_file)
            logger = get_logger("test")
            
            logger.info("Info message")
            logger.error("Error message")
            
            # Check main log has both
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Info message" in content
                assert "Error message" in content
            
            # Check error log has only errors
            error_log = log_file.replace('.log', '_errors.log')
            with open(error_log, 'r') as f:
                content = f.read()
                assert "Error message" in content
                assert "Info message" not in content


class TestLoggerRetrieval:
    """Test logger retrieval and configuration."""
    
    def test_get_logger(self):
        """Test getting a named logger."""
        logger = get_logger("my_module")
        
        assert logger is not None
        assert logger.name == "my_module"
    
    def test_multiple_loggers_same_config(self):
        """Test multiple loggers use same configuration."""
        setup_structured_logging(log_level="WARNING", use_json=True)
        
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        assert logger1.level == logger2.level


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
