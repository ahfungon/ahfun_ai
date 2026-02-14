"""Tests for structured logging configuration."""
import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest

from utils.logging_config import (
    JSONFormatter,
    setup_logging,
    log_llm_call,
    log_retry_attempt,
    log_error_with_context
)


class TestJSONFormatter:
    """Test JSON formatter for structured logging."""
    
    def test_json_formatter_basic_message(self):
        """Test that basic log messages are formatted as JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Test message"
        assert "timestamp" in data
    
    def test_json_formatter_with_extra_fields(self):
        """Test that extra fields are included in JSON output."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        # Add extra fields
        record.job_id = "test-job-123"
        record.topic_id = "test-topic-456"
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["job_id"] == "test-job-123"
        assert data["topic_id"] == "test-topic-456"
    
    def test_json_formatter_with_exception(self):
        """Test that exceptions are properly formatted."""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=exc_info
            )
            
            result = formatter.format(record)
            data = json.loads(result)
            
            assert "exception" in data
            assert data["exception"]["type"] == "ValueError"
            assert data["exception"]["message"] == "Test error"
            assert "traceback" in data["exception"]


class TestSetupLogging:
    """Test logging setup function."""
    
    def test_setup_logging_configures_root_logger(self):
        """Test that setup_logging configures the root logger."""
        setup_logging(log_level="DEBUG")
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        
        # Check that handler is configured
        assert len(root_logger.handlers) > 0
        handler = root_logger.handlers[0]
        assert isinstance(handler.formatter, JSONFormatter)


class TestLogLLMCall:
    """Test LLM call logging utility."""
    
    def test_log_llm_call_success(self, caplog):
        """Test logging successful LLM call."""
        logger = logging.getLogger("test")
        
        with caplog.at_level(logging.INFO):
            log_llm_call(
                logger,
                provider="DeepSeek",
                operation="generate_summary",
                request_params={"topic_id": "test-123"},
                response={"summary": "Test summary"},
                duration_ms=150.5
            )
        
        # Check that log was created
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        assert record.levelname == "INFO"
        assert "DeepSeek" in record.message
        assert "generate_summary" in record.message
        assert record.event_type == "llm_call"
        assert record.provider == "DeepSeek"
        assert record.status == "success"
        assert record.duration_ms == 150.5
    
    def test_log_llm_call_error(self, caplog):
        """Test logging failed LLM call."""
        logger = logging.getLogger("test")
        error = ValueError("API timeout")
        
        with caplog.at_level(logging.ERROR):
            log_llm_call(
                logger,
                provider="DeepSeek",
                operation="generate_summary",
                request_params={"topic_id": "test-123"},
                error=error,
                duration_ms=5000.0
            )
        
        # Check that log was created
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        assert record.levelname == "ERROR"
        assert record.status == "error"
        assert record.error == "API timeout"


class TestLogRetryAttempt:
    """Test retry attempt logging utility."""
    
    def test_log_retry_attempt_with_delay(self, caplog):
        """Test logging retry attempt with next delay."""
        logger = logging.getLogger("test")
        
        with caplog.at_level(logging.WARNING):
            log_retry_attempt(
                logger,
                job_id="job-123",
                topic_id="topic-456",
                retry_count=2,
                max_retries=3,
                error="LLM timeout",
                next_delay=4
            )
        
        # Check that log was created
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        assert record.levelname == "WARNING"
        assert record.event_type == "retry_attempt"
        assert record.job_id == "job-123"
        assert record.retry_count == 2
        assert record.next_delay_seconds == 4
    
    def test_log_retry_attempt_final_failure(self, caplog):
        """Test logging final retry failure."""
        logger = logging.getLogger("test")
        
        with caplog.at_level(logging.ERROR):
            log_retry_attempt(
                logger,
                job_id="job-123",
                topic_id="topic-456",
                retry_count=3,
                max_retries=3,
                error="LLM timeout",
                next_delay=None
            )
        
        # Check that log was created
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        assert record.levelname == "ERROR"
        assert "Final retry" in record.message


class TestLogErrorWithContext:
    """Test error logging with context utility."""
    
    def test_log_error_with_context(self, caplog):
        """Test logging error with additional context."""
        logger = logging.getLogger("test")
        error = RuntimeError("Database connection failed")
        context = {
            "job_id": "job-123",
            "topic_id": "topic-456",
            "retry_count": 2
        }
        
        with caplog.at_level(logging.ERROR):
            log_error_with_context(
                logger,
                error,
                context,
                "Failed to process job"
            )
        
        # Check that log was created
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        assert record.levelname == "ERROR"
        assert record.event_type == "error"
        assert record.error_type == "RuntimeError"
        assert record.error_message == "Database connection failed"
        assert record.job_id == "job-123"
        assert record.topic_id == "topic-456"
        assert record.retry_count == 2


class TestStructuredLoggingIntegration:
    """Integration tests for structured logging."""
    
    def test_json_output_is_parseable(self):
        """Test that JSON output can be parsed."""
        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        
        logger = logging.getLogger("test_integration")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Log a message with extra fields
        logger.info(
            "Test message",
            extra={
                "event_type": "test_event",
                "job_id": "job-123",
                "count": 42
            }
        )
        
        # Parse the output
        output = stream.getvalue()
        data = json.loads(output)
        
        assert data["message"] == "Test message"
        assert data["event_type"] == "test_event"
        assert data["job_id"] == "job-123"
        assert data["count"] == 42
        assert "timestamp" in data
        
        # Clean up
        logger.removeHandler(handler)
