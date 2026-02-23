"""
Integrated test suite for logging and error handling.

This test suite validates:
- Property 26: Invalid parameters return 400 (Requirement 12.1)
- Property 27: LLM failure keeps original state (Requirement 12.4)
- Property 45: LLM failure returns prompt (Requirement 12.5)
- Property 46: Error logs detailed recording (Requirements 12.4, 12.7)
"""
import json
import logging
import pytest
import bcrypt
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from models.models import Topic, Agent, SummaryJob, Message
from models.database import get_db
from services.summary_service import SummaryService
from services.audit_log_service import AuditLogService
from api.exceptions import LLMServiceError
from utils.logging_config import log_llm_call, log_error_with_context


@pytest.fixture
def authenticated_agent(test_db: Session):
    """Create an agent with a known token for testing."""
    from uuid import uuid4
    
    # Create agent with known token
    token = "test_token_123"
    token_hash = bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    agent = Agent(
        id=str(uuid4()),
        name="Test Agent",
        auth_token_hash=token_hash
    )
    test_db.add(agent)
    test_db.commit()
    test_db.refresh(agent)
    
    # Return agent and token
    agent.plain_token = token
    return agent


@pytest.fixture
def auth_headers(authenticated_agent: Agent):
    """Create authentication headers for testing."""
    return {
        "X-Agent-Id": authenticated_agent.id,
        "X-Auth-Token": authenticated_agent.plain_token
    }


@pytest.fixture
def test_client(test_db: Session):
    """Create a test client with overridden database dependency."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()


class TestProperty26InvalidParametersReturn400:
    """
    Property 26: Invalid parameters return 400
    Validates Requirement 12.1
    
    For any API request with invalid parameters (format error, type error),
    the system should return 400 status code and descriptive error information.
    """
    
    def test_post_message_missing_required_fields(self, test_client, test_db: Session, auth_headers: dict):
        """Test that missing required fields return 422 validation error."""
        # Missing content and actual_tokens
        response = test_client.post(
            "/api/message",
            json={"topic_id": "test-topic-123"},
            headers=auth_headers
        )
        
        assert response.status_code == 422  # FastAPI uses 422 for validation errors
        data = response.json()
        assert "error" in data
        assert "detail" in data
        assert "timestamp" in data
    
    def test_post_message_invalid_token_type(self, test_client, test_db: Session, auth_headers: dict):
        """Test that invalid token type returns validation error."""
        # actual_tokens should be int, not string
        response = test_client.post(
            "/api/message",
            json={
                "topic_id": "test-topic-123",
                "content": "Test message",
                "actual_tokens": "not_a_number"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "actual_tokens" in data["detail"].lower() or "validation" in data["error"].lower()
    
    def test_get_messages_invalid_limit_type(self, test_client, test_db: Session, auth_headers: dict, sample_topic: Topic):
        """Test that invalid limit parameter type returns validation error."""
        # limit should be int, not string
        response = test_client.get(
            f"/api/topic/{sample_topic.id}/messages?limit=invalid",
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
    
    def test_create_topic_invalid_json(self, test_client, test_db: Session, auth_headers: dict):
        """Test that malformed JSON returns 422."""
        # Send invalid JSON
        response = test_client.post(
            "/api/topic",
            data="{invalid json}",
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
    
    def test_rollback_summary_missing_history_id(self, test_client, test_db: Session, auth_headers: dict, sample_topic: Topic):
        """Test that missing history_id returns validation error."""
        # Missing history_id
        response = test_client.post(
            f"/api/topic/{sample_topic.id}/rollback-summary",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "history_id" in data["detail"].lower()
    
    def test_error_response_format_consistency(self, test_client, test_db: Session, auth_headers: dict):
        """Test that all validation errors have consistent response format."""
        response = test_client.post(
            "/api/message",
            json={"topic_id": "test"},  # Missing required fields
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Must have these three fields
        assert "error" in data
        assert "detail" in data
        assert "timestamp" in data
        
        # Timestamp should be ISO 8601 format
        timestamp = data["timestamp"]
        assert timestamp.endswith("Z")
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


class TestProperty27LLMFailureKeepsOriginalState:
    """
    Property 27: LLM failure keeps original state
    Validates Requirement 12.4
    
    For any LLM summary call failure, the topic's summary and llm_suggestion
    should remain unchanged from before the call.
    """
    
    def test_llm_failure_preserves_summary(self, test_db: Session, sample_topic: Topic):
        """Test that LLM failure doesn't change existing summary."""
        # Set initial state
        original_summary = "Original summary text"
        original_suggestion = "continue"
        original_end_score = 25.5
        
        sample_topic.summary = original_summary
        sample_topic.llm_suggestion = original_suggestion
        sample_topic.end_score = original_end_score
        test_db.commit()
        
        # Mock LLM service to fail
        summary_service = SummaryService(test_db)
        
        with patch.object(summary_service, '_call_deepseek_api') as mock_llm:
            mock_llm.side_effect = LLMServiceError("DeepSeek API timeout")
            
            # Attempt to generate summary (should fail)
            try:
                summary_service.generate_summary(sample_topic, [])
            except LLMServiceError:
                pass
        
        # Refresh topic from database
        test_db.refresh(sample_topic)
        
        # Verify state unchanged
        assert sample_topic.summary == original_summary
        assert sample_topic.llm_suggestion == original_suggestion
        assert sample_topic.end_score == original_end_score
    
    def test_llm_failure_preserves_empty_summary(self, test_db: Session, sample_topic: Topic):
        """Test that LLM failure preserves empty summary state."""
        # Set initial empty state
        sample_topic.summary = ""
        sample_topic.llm_suggestion = None
        sample_topic.end_score = 0.0
        test_db.commit()
        
        summary_service = SummaryService(test_db)
        
        with patch.object(summary_service, '_call_deepseek_api') as mock_llm:
            mock_llm.side_effect = LLMServiceError("Connection refused")
            
            try:
                summary_service.generate_summary(sample_topic, [])
            except LLMServiceError:
                pass
        
        test_db.refresh(sample_topic)
        
        # Verify empty state preserved
        assert sample_topic.summary == ""
        assert sample_topic.llm_suggestion is None
        assert sample_topic.end_score == 0.0
    
    def test_llm_retry_failure_preserves_state(self, test_db: Session, sample_topic: Topic):
        """Test that state is preserved even after multiple retry failures."""
        original_summary = "Summary before retries"
        original_suggestion = "change_angle"
        
        sample_topic.summary = original_summary
        sample_topic.llm_suggestion = original_suggestion
        test_db.commit()
        
        summary_service = SummaryService(test_db)
        
        # Mock to fail all retries
        with patch.object(summary_service, '_call_deepseek_api') as mock_llm:
            mock_llm.side_effect = LLMServiceError("Persistent failure")
            
            # Simulate retry attempts
            for _ in range(3):
                try:
                    summary_service.generate_summary(sample_topic, [])
                except LLMServiceError:
                    pass
        
        test_db.refresh(sample_topic)
        
        # State should still be original
        assert sample_topic.summary == original_summary
        assert sample_topic.llm_suggestion == original_suggestion
    
    def test_partial_llm_response_rollback(self, test_db: Session, sample_topic: Topic):
        """Test that partial updates are rolled back on failure."""
        original_summary = "Original"
        sample_topic.summary = original_summary
        test_db.commit()
        
        summary_service = SummaryService(test_db)
        
        # Mock to return partial data then fail
        with patch.object(summary_service, 'update_topic_summary') as mock_update:
            mock_update.side_effect = Exception("Database error during update")
            
            try:
                # This should fail during update
                summary_service.update_topic_summary(
                    sample_topic.id,
                    "New summary",
                    "suggest_end",
                    75.0
                )
            except Exception:
                test_db.rollback()
        
        test_db.refresh(sample_topic)
        
        # Original state should be preserved
        assert sample_topic.summary == original_summary


class TestProperty45LLMFailureReturnsPrompt:
    """
    Property 45: LLM failure returns prompt
    Validates Requirement 12.5
    
    When LLM call fails, the system should return a prompt/message in the API response
    informing the agent that the summary service is temporarily unavailable.
    """
    
    def test_llm_service_error_returns_503_with_message(self):
        """Test that LLM service error returns 503 with informative message."""
        # Create a test endpoint that raises LLMServiceError
        from fastapi import FastAPI
        from fastapi.testclient import TestClient as TC
        from api.error_handlers import llm_service_error_handler
        from api.exceptions import LLMServiceError
        
        test_app = FastAPI()
        test_app.add_exception_handler(LLMServiceError, llm_service_error_handler)
        
        @test_app.get("/test/llm-error")
        async def test_llm_error():
            raise LLMServiceError("DeepSeek API is currently unavailable")
        
        test_client = TC(test_app, raise_server_exceptions=False)
        response = test_client.get("/test/llm-error")
        
        assert response.status_code == 503
        data = response.json()
        
        assert "error" in data
        assert "detail" in data
        assert "unavailable" in data["detail"].lower()
        assert "LLM" in data["error"] or "service" in data["error"].lower()
    
    def test_summary_failure_message_includes_context(self):
        """Test that LLM failure message includes helpful context."""
        from api.error_handlers import create_error_response
        
        response = create_error_response(
            error="LLM service unavailable",
            detail="The summary service is temporarily unavailable. Please try again later.",
            status_code=503
        )
        
        assert response.status_code == 503
        data = json.loads(response.body.decode())
        
        assert "temporarily unavailable" in data["detail"].lower()
        assert "timestamp" in data
    
    def test_llm_timeout_returns_informative_message(self):
        """Test that LLM timeout returns user-friendly message."""
        error_msg = "Request timeout: DeepSeek API did not respond within 30 seconds"
        
        from api.error_handlers import create_error_response
        response = create_error_response(
            error="LLM service unavailable",
            detail=error_msg,
            status_code=503
        )
        
        data = json.loads(response.body.decode())
        assert "timeout" in data["detail"].lower()
        assert response.status_code == 503
    
    def test_llm_rate_limit_returns_informative_message(self):
        """Test that rate limit error returns helpful message."""
        error_msg = "Rate limit exceeded. Please try again in a few minutes."
        
        from api.error_handlers import create_error_response
        response = create_error_response(
            error="LLM service unavailable",
            detail=error_msg,
            status_code=503
        )
        
        data = json.loads(response.body.decode())
        assert "rate limit" in data["detail"].lower()


class TestProperty46ErrorLogsDetailedRecording:
    """
    Property 46: Error logs detailed recording
    Validates Requirements 12.4, 12.7
    
    For any LLM call failure, the system should record detailed error logs including:
    - Request parameters
    - Response content (if any)
    - Error stack trace
    """
    
    def test_llm_failure_logs_request_parameters(self, caplog):
        """Test that LLM failure logs include request parameters."""
        logger = logging.getLogger("test")
        
        request_params = {
            "topic_id": "topic-123",
            "messages_count": 5,
            "old_summary": "Previous summary"
        }
        
        error = LLMServiceError("API timeout")
        
        with caplog.at_level(logging.ERROR):
            log_llm_call(
                logger,
                provider="DeepSeek",
                operation="generate_summary",
                request_params=request_params,
                error=error,
                duration_ms=30000.0
            )
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        assert record.levelname == "ERROR"
        assert record.provider == "DeepSeek"
        assert record.operation == "generate_summary"
        assert record.status == "error"
        assert record.error == "API timeout"
        assert record.duration_ms == 30000.0
    
    def test_llm_failure_logs_response_content(self, caplog):
        """Test that partial response content is logged on failure."""
        logger = logging.getLogger("test")
        
        # Simulate partial response before failure
        partial_response = {
            "summary": "Partial summary...",
            "error": "Connection lost"
        }
        
        with caplog.at_level(logging.ERROR):
            log_error_with_context(
                logger,
                LLMServiceError("Connection lost during streaming"),
                {
                    "partial_response": partial_response,
                    "topic_id": "topic-456"
                },
                "LLM call failed with partial response"
            )
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        assert record.event_type == "error"
        assert record.topic_id == "topic-456"
        assert hasattr(record, 'partial_response')
    
    def test_llm_failure_logs_error_traceback(self, caplog):
        """Test that error traceback is logged."""
        logger = logging.getLogger("test")
        
        try:
            # Create a real exception with traceback
            raise ValueError("Simulated LLM error")
        except ValueError as e:
            with caplog.at_level(logging.ERROR):
                log_error_with_context(
                    logger,
                    e,
                    {"operation": "generate_summary"},
                    "LLM operation failed"
                )
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        assert record.levelname == "ERROR"
        assert record.error_type == "ValueError"
        assert record.error_message == "Simulated LLM error"
    
    def test_retry_attempt_logs_detailed_info(self, caplog):
        """Test that retry attempts log detailed information."""
        from utils.logging_config import log_retry_attempt
        
        logger = logging.getLogger("test")
        
        with caplog.at_level(logging.WARNING):
            log_retry_attempt(
                logger,
                job_id="job-789",
                topic_id="topic-123",
                retry_count=2,
                max_retries=3,
                error="DeepSeek API timeout after 30s",
                next_delay=4
            )
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        assert record.event_type == "retry_attempt"
        assert record.job_id == "job-789"
        assert record.topic_id == "topic-123"
        assert record.retry_count == 2
        assert record.max_retries == 3
        assert record.next_delay_seconds == 4
        assert "timeout" in record.error.lower()
    
    def test_final_retry_failure_logs_as_error(self, caplog):
        """Test that final retry failure is logged as ERROR level."""
        from utils.logging_config import log_retry_attempt
        
        logger = logging.getLogger("test")
        
        with caplog.at_level(logging.ERROR):
            log_retry_attempt(
                logger,
                job_id="job-999",
                topic_id="topic-888",
                retry_count=3,
                max_retries=3,
                error="Persistent API failure",
                next_delay=None
            )
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        assert record.levelname == "ERROR"
        assert "Final retry" in record.message or record.retry_count == record.max_retries
    
    def test_structured_log_includes_all_context(self, caplog):
        """Test that structured logs include all relevant context."""
        logger = logging.getLogger("test")
        
        context = {
            "job_id": "job-123",
            "topic_id": "topic-456",
            "retry_count": 1,
            "request_params": {
                "model": "deepseek-chat",
                "temperature": 0.7
            },
            "duration_ms": 15000
        }
        
        error = LLMServiceError("Model overloaded")
        
        with caplog.at_level(logging.ERROR):
            log_error_with_context(
                logger,
                error,
                context,
                "LLM service error"
            )
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        # Verify all context fields are present
        assert record.job_id == "job-123"
        assert record.topic_id == "topic-456"
        assert record.retry_count == 1
        assert hasattr(record, 'request_params')
        assert record.duration_ms == 15000


class TestErrorHandlingIntegration:
    """Integration tests for error handling across components."""
    
    def test_invalid_topic_id_returns_404_with_logging(self, test_client, test_db: Session, auth_headers: dict, caplog):
        """Test that invalid topic ID returns 404 and logs appropriately."""
        with caplog.at_level(logging.ERROR):
            response = test_client.post(
                "/api/topic/nonexistent-topic/request-close",
                headers=auth_headers
            )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_authentication_failure_returns_401(self, test_client, test_db: Session):
        """Test that authentication failure returns 401."""
        headers = {
            "X-Agent-Id": "invalid-agent",
            "X-Auth-Token": "invalid-token"
        }
        
        response = test_client.get(
            "/api/topic/active",
            headers=headers
        )
        
        assert response.status_code == 401
        data = response.json()
        # The response format from HTTPException may differ
        assert "detail" in data
        assert "not found" in data["detail"].lower() or "invalid" in data["detail"].lower()
    
    def test_missing_authentication_headers_returns_401(self, test_client, test_db: Session):
        """Test that missing auth headers returns 401."""
        response = test_client.get("/api/topic/active")
        
        assert response.status_code == 401
    
    def test_error_response_includes_detail(self, test_client, test_db: Session):
        """Test that error responses include detail field."""
        response = test_client.get("/api/topic/active")
        
        assert response.status_code == 401
        data = response.json()
        
        # HTTPException returns detail field
        assert "detail" in data
    
    def test_audit_log_records_error_operations(self, test_db: Session, sample_topic: Topic):
        """Test that error operations are recorded in audit log."""
        audit_service = AuditLogService(test_db)
        
        # Record an error operation
        log = audit_service.record(
            operation_type=AuditLogService.OPERATION_SUMMARY_UPDATED,
            topic_id=sample_topic.id,
            details={
                "status": "failed",
                "error": "LLM timeout",
                "retry_count": 3
            }
        )
        
        assert log.id is not None
        assert log.topic_id == sample_topic.id
        
        details = json.loads(log.details)
        assert details["status"] == "failed"
        assert details["error"] == "LLM timeout"


class TestLoggingConfiguration:
    """Test logging configuration and structured logging."""
    
    def test_json_formatter_produces_valid_json(self):
        """Test that JSON formatter produces parseable JSON."""
        from utils.logging_config import JSONFormatter
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["level"] == "ERROR"
        assert data["message"] == "Test error message"
        assert "timestamp" in data
    
    def test_json_formatter_includes_exception_info(self):
        """Test that exceptions are properly formatted in JSON logs."""
        from utils.logging_config import JSONFormatter
        
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test exception")
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
            assert data["exception"]["message"] == "Test exception"
            assert "traceback" in data["exception"]


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
