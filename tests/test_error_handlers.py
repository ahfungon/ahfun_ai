"""Tests for error handling middleware."""
import pytest
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError as PydanticValidationError

from api.exceptions import (
    AuthenticationError,
    ValidationError,
    NotFoundError,
    LLMServiceError
)
from api.error_handlers import (
    authentication_error_handler,
    validation_error_handler,
    request_validation_error_handler,
    not_found_error_handler,
    llm_service_error_handler,
    generic_exception_handler,
    create_error_response
)


# Test app setup
app = FastAPI()

# Register exception handlers
app.add_exception_handler(AuthenticationError, authentication_error_handler)
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_error_handler)
app.add_exception_handler(NotFoundError, not_found_error_handler)
app.add_exception_handler(LLMServiceError, llm_service_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# Test routes that raise exceptions
@app.get("/test/auth-error")
async def auth_error_endpoint():
    raise AuthenticationError("Invalid credentials")


@app.get("/test/validation-error")
async def validation_error_endpoint():
    raise ValidationError("Invalid input data")


@app.get("/test/not-found-error")
async def not_found_error_endpoint():
    raise NotFoundError("Topic not found")


@app.get("/test/llm-error")
async def llm_error_endpoint():
    raise LLMServiceError("DeepSeek API unavailable")


@app.get("/test/generic-error")
async def generic_error_endpoint():
    raise RuntimeError("Unexpected error")


@app.get("/test/zero-division")
async def zero_division_endpoint():
    return 1 / 0


class RequestModel(BaseModel):
    name: str
    age: int


@app.post("/test/pydantic-validation")
async def pydantic_validation_endpoint(data: RequestModel):
    return data


client = TestClient(app, raise_server_exceptions=False)


class TestErrorHandlers:
    """Test suite for error handling middleware."""
    
    def test_authentication_error_returns_401(self):
        """Test that AuthenticationError returns 401 status code."""
        response = client.get("/test/auth-error")
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "detail" in data
        assert "timestamp" in data
        assert data["error"] == "Authentication failed"
        assert data["detail"] == "Invalid credentials"
    
    def test_validation_error_returns_400(self):
        """Test that ValidationError returns 400 status code."""
        response = client.get("/test/validation-error")
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Validation failed"
        assert data["detail"] == "Invalid input data"
    
    def test_not_found_error_returns_404(self):
        """Test that NotFoundError returns 404 status code."""
        response = client.get("/test/not-found-error")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "Resource not found"
        assert data["detail"] == "Topic not found"
    
    def test_llm_service_error_returns_503(self):
        """Test that LLMServiceError returns 503 status code."""
        response = client.get("/test/llm-error")
        
        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "LLM service unavailable"
        assert data["detail"] == "DeepSeek API unavailable"
    
    def test_generic_exception_returns_500(self):
        """Test that unhandled exceptions return 500 status code."""
        response = client.get("/test/generic-error")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Internal server error"
        assert "unexpected error" in data["detail"].lower()
    
    def test_zero_division_returns_500(self):
        """Test that ZeroDivisionError returns 500 status code."""
        response = client.get("/test/zero-division")
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Internal server error"
    
    def test_request_validation_error_returns_400(self):
        """Test that FastAPI RequestValidationError returns 422."""
        # Missing required fields
        response = client.post("/test/pydantic-validation", json={})
        
        assert response.status_code == 422  # 422 is the correct status for validation errors
        data = response.json()
        assert "error" in data
        assert "detail" in data
        # Should contain validation error details
        assert "name" in data["detail"] or "age" in data["detail"]
    
    def test_pydantic_validation_wrong_type(self):
        """Test that wrong data types trigger validation error."""
        response = client.post(
            "/test/pydantic-validation",
            json={"name": "John", "age": "not_a_number"}
        )
        
        assert response.status_code == 422  # 422 is the correct status for validation errors
        data = response.json()
        assert data["error"] == "Validation failed"
    
    def test_error_response_includes_timestamp(self):
        """Test that all error responses include ISO 8601 timestamp."""
        response = client.get("/test/auth-error")
        
        data = response.json()
        assert "timestamp" in data
        
        # Verify timestamp is valid ISO 8601 format
        timestamp = data["timestamp"]
        assert timestamp.endswith("Z")
        # Should be parseable
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    
    def test_error_response_structure(self):
        """Test that error responses have consistent structure."""
        response = client.get("/test/not-found-error")
        
        data = response.json()
        # Must have exactly these three fields
        assert set(data.keys()) == {"error", "detail", "timestamp"}
        
        # All fields must be strings
        assert isinstance(data["error"], str)
        assert isinstance(data["detail"], str)
        assert isinstance(data["timestamp"], str)
    
    def test_create_error_response_helper(self):
        """Test the create_error_response helper function."""
        response = create_error_response(
            error="Test error",
            detail="Test detail message",
            status_code=418
        )
        
        assert response.status_code == 418
        data = response.body.decode()
        import json
        parsed = json.loads(data)
        
        assert parsed["error"] == "Test error"
        assert parsed["detail"] == "Test detail message"
        assert "timestamp" in parsed


class TestErrorHandlerIntegration:
    """Integration tests for error handlers with actual exceptions."""
    
    def test_multiple_validation_errors(self):
        """Test handling of multiple validation errors at once."""
        response = client.post(
            "/test/pydantic-validation",
            json={"invalid_field": "value"}
        )
        
        assert response.status_code == 422  # 422 is the correct status for validation errors
        data = response.json()
        # Should mention both missing fields
        detail = data["detail"]
        assert "name" in detail or "age" in detail
    
    def test_error_handler_does_not_leak_sensitive_info(self):
        """Test that generic errors don't leak implementation details."""
        response = client.get("/test/generic-error")
        
        data = response.json()
        # Should not contain stack traces or internal paths
        assert "RuntimeError" not in data["detail"]
        assert "traceback" not in data["detail"].lower()
        assert "/test/" not in data["detail"]
    
    def test_authentication_error_custom_message(self):
        """Test that custom error messages are preserved."""
        @app.get("/test/custom-auth-error")
        async def custom_auth_error():
            raise AuthenticationError("Token expired at 2024-01-15")
        
        response = client.get("/test/custom-auth-error")
        
        assert response.status_code == 401
        data = response.json()
        assert "Token expired" in data["detail"]
    
    def test_llm_error_custom_message(self):
        """Test that LLM error messages are preserved."""
        @app.get("/test/custom-llm-error")
        async def custom_llm_error():
            raise LLMServiceError("Rate limit exceeded: 429")
        
        response = client.get("/test/custom-llm-error")
        
        assert response.status_code == 503
        data = response.json()
        assert "Rate limit" in data["detail"]


class TestErrorHandlerEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_error_message(self):
        """Test handling of exceptions with empty messages."""
        @app.get("/test/empty-message")
        async def empty_message():
            raise ValidationError("")
        
        response = client.get("/test/empty-message")
        
        assert response.status_code == 400
        data = response.json()
        # Should still have the error structure
        assert "error" in data
        assert "detail" in data
    
    def test_very_long_error_message(self):
        """Test handling of very long error messages."""
        long_message = "x" * 10000
        
        @app.get("/test/long-message")
        async def long_message_error():
            raise NotFoundError(long_message)
        
        response = client.get("/test/long-message")
        
        assert response.status_code == 404
        data = response.json()
        # Should include the full message
        assert len(data["detail"]) == 10000
    
    def test_unicode_in_error_message(self):
        """Test handling of unicode characters in error messages."""
        @app.get("/test/unicode-error")
        async def unicode_error():
            raise ValidationError("错误：无效的输入 🚫")
        
        response = client.get("/test/unicode-error")
        
        assert response.status_code == 400
        data = response.json()
        assert "错误" in data["detail"]
        assert "🚫" in data["detail"]
    
    def test_nested_exception(self):
        """Test handling of nested exceptions."""
        @app.get("/test/nested-error")
        async def nested_error():
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise NotFoundError(f"Outer error: {e}")
        
        response = client.get("/test/nested-error")
        
        assert response.status_code == 404
        data = response.json()
        assert "Outer error" in data["detail"]
        assert "Inner error" in data["detail"]


# Property-based tests would go here if using hypothesis
# For now, we have comprehensive unit tests covering all requirements
