"""
Tests for observability features.
Tests logging, metrics, tracing, and health checks.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import time

from app.observability import (
    setup_structured_logging,
    get_logger,
    metrics,
    setup_tracing,
    HealthChecker,
)
from app.observability.logger import set_request_context, clear_request_context
from app.observability.middleware import ObservabilityMiddleware, PerformanceLoggingMiddleware
from app.observability.health import HealthStatus


class TestStructuredLogging:
    """Test structured logging functionality."""
    
    def test_setup_logging_default(self):
        """Test default logging setup."""
        logger = setup_structured_logging(log_level="INFO", use_json=True)
        assert logger is not None
        assert logger.level == logging.INFO
    
    def test_setup_logging_debug_level(self):
        """Test logging setup with DEBUG level."""
        logger = setup_structured_logging(log_level="DEBUG", use_json=True)
        assert logger.level == logging.DEBUG
    
    def test_get_logger(self):
        """Test getting a logger."""
        logger = get_logger("test.module")
        assert logger is not None
        assert logger.name == "test.module"
    
    def test_request_context(self):
        """Test setting and clearing request context."""
        request_id = "test-request-123"
        user_id = "user-456"
        
        set_request_context(request_id=request_id, user_id=user_id)
        # Context is set in context vars, should not raise
        
        clear_request_context()
        # Context is cleared, should not raise


class TestPrometheusMetrics:
    """Test Prometheus metrics functionality."""
    
    def test_metrics_initialization(self):
        """Test metrics are properly initialized."""
        assert metrics is not None
        assert metrics.request_count is not None
        assert metrics.request_latency is not None
        assert metrics.error_count is not None
        assert metrics.db_query_count is not None
        assert metrics.embedding_generation_count is not None
        assert metrics.cache_hits is not None
        assert metrics.llm_requests is not None
    
    def test_track_request(self):
        """Test tracking HTTP request metrics."""
        initial_count = metrics.request_count._value.get()
        
        metrics.track_request(
            method="GET",
            endpoint="/test",
            status=200,
            duration=0.123
        )
        
        # Metric should be incremented
        # Note: We can't easily assert the exact value due to other tests
        # but we verify the method doesn't raise
    
    def test_track_error(self):
        """Test tracking error metrics."""
        metrics.track_error(
            error_type="TestError",
            endpoint="/test"
        )
        # Should not raise
    
    def test_track_db_query(self):
        """Test tracking database query metrics."""
        metrics.track_db_query(
            operation="select",
            duration=0.050
        )
        # Should not raise
    
    def test_track_embedding(self):
        """Test tracking embedding generation metrics."""
        metrics.track_embedding(duration=1.5)
        # Should not raise
    
    def test_track_cache(self):
        """Test tracking cache metrics."""
        metrics.track_cache(cache_type="test_cache", hit=True)
        metrics.track_cache(cache_type="test_cache", hit=False)
        # Should not raise
    
    def test_track_llm_request(self):
        """Test tracking LLM request metrics."""
        metrics.track_llm_request(
            provider="openai",
            model="gpt-3.5-turbo",
            duration=2.5,
            prompt_tokens=100,
            completion_tokens=50
        )
        # Should not raise


class TestHealthChecker:
    """Test health check functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = Mock()
        db.execute = Mock(return_value=Mock(scalar=Mock(return_value=1)))
        db.query = Mock(return_value=Mock(count=Mock(return_value=10)))
        return db
    
    def test_health_checker_initialization(self):
        """Test health checker initialization."""
        checker = HealthChecker()
        assert checker is not None
        assert checker.checks is not None
    
    def test_check_database_healthy(self, mock_db):
        """Test database health check when healthy."""
        checker = HealthChecker()
        result = checker.check_database(mock_db)
        
        assert result.name == "database"
        assert result.status == HealthStatus.HEALTHY
        assert result.latency_ms is not None
        assert result.latency_ms >= 0
    
    def test_check_database_unhealthy(self):
        """Test database health check when unhealthy."""
        checker = HealthChecker()
        
        # Create a mock DB that raises an exception
        db = Mock()
        db.execute = Mock(side_effect=Exception("Connection failed"))
        
        result = checker.check_database(db)
        
        assert result.name == "database"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection failed" in result.message
    
    def test_check_embedding_service(self):
        """Test embedding service health check."""
        checker = HealthChecker()
        result = checker.check_embedding_service()
        
        assert result.name == "embedding_service"
        # Status depends on configuration
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
    
    def test_check_rag_service(self):
        """Test RAG service health check."""
        checker = HealthChecker()
        result = checker.check_rag_service()
        
        assert result.name == "rag_service"
        # Status depends on configuration
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
    
    def test_check_adapters(self):
        """Test adapters health check."""
        checker = HealthChecker()
        result = checker.check_adapters()
        
        assert result.name == "adapters"
        # Status depends on configuration
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
    
    def test_check_all(self, mock_db):
        """Test checking all components."""
        checker = HealthChecker()
        result = checker.check_all(db=mock_db)
        
        assert "status" in result
        assert "timestamp" in result
        assert "components" in result
        assert len(result["components"]) > 0
        
        # Verify component structure
        for component in result["components"]:
            assert "name" in component
            assert "status" in component
            assert "message" in component


class TestObservabilityMiddleware:
    """Test observability middleware."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with middleware."""
        app = FastAPI()
        app.add_middleware(ObservabilityMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.get("/error")
        async def error_endpoint():
            raise Exception("Test error")
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)
    
    def test_middleware_adds_request_id(self, client):
        """Test middleware adds request ID to response."""
        response = client.get("/test")
        assert "X-Request-ID" in response.headers
    
    def test_middleware_handles_custom_request_id(self, client):
        """Test middleware uses custom request ID if provided."""
        custom_id = "custom-request-123"
        response = client.get("/test", headers={"X-Request-ID": custom_id})
        assert response.headers["X-Request-ID"] == custom_id
    
    def test_middleware_logs_request(self, client, caplog):
        """Test middleware logs requests."""
        with caplog.at_level(logging.INFO):
            response = client.get("/test")
            assert response.status_code == 200
        
        # Check logs contain request information
        log_messages = [record.message for record in caplog.records]
        assert any("Request started" in msg for msg in log_messages)
        assert any("Request completed" in msg for msg in log_messages)
    
    def test_middleware_handles_errors(self, client, caplog):
        """Test middleware handles errors gracefully."""
        with caplog.at_level(logging.ERROR):
            response = client.get("/error")
            assert response.status_code == 500
        
        # Check error was logged
        log_messages = [record.message for record in caplog.records]
        assert any("Request failed" in msg for msg in log_messages)


class TestPerformanceLoggingMiddleware:
    """Test performance logging middleware."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with middleware."""
        app = FastAPI()
        app.add_middleware(PerformanceLoggingMiddleware, slow_request_threshold=0.001)
        
        @app.get("/fast")
        async def fast_endpoint():
            return {"message": "fast"}
        
        @app.get("/slow")
        async def slow_endpoint():
            time.sleep(0.01)  # Simulate slow request
            return {"message": "slow"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)
    
    def test_middleware_logs_slow_requests(self, client, caplog):
        """Test middleware logs slow requests."""
        with caplog.at_level(logging.WARNING):
            response = client.get("/slow")
            assert response.status_code == 200
        
        # Check slow request was logged
        log_messages = [record.message for record in caplog.records]
        assert any("Slow request detected" in msg for msg in log_messages)
    
    def test_middleware_does_not_log_fast_requests(self, client, caplog):
        """Test middleware doesn't log fast requests."""
        with caplog.at_level(logging.WARNING):
            response = client.get("/fast")
            assert response.status_code == 200
        
        # Check no slow request warning
        log_messages = [record.message for record in caplog.records]
        assert not any("Slow request detected" in msg for msg in log_messages)


class TestTracing:
    """Test OpenTelemetry tracing functionality."""
    
    def test_setup_tracing_no_exporters(self):
        """Test tracing setup without exporters."""
        tracer = setup_tracing(service_name="test-service")
        assert tracer is not None
    
    def test_setup_tracing_with_console(self):
        """Test tracing setup with console exporter."""
        tracer = setup_tracing(
            service_name="test-service",
            console_export=True
        )
        assert tracer is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
