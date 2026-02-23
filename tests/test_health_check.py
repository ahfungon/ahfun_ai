"""Tests for health check endpoint."""
import pytest
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_check_endpoint_exists(test_db):
    """
    Test that health check endpoint exists and returns valid response.
    
    **Validates: Requirement 12.9**
    Feature: dual-agent-chat, Property 47: 健康检查API
    """
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required top-level fields
    assert "status" in data
    assert "timestamp" in data
    assert "services" in data
    
    # Check that status is valid
    assert data["status"] in ["ok", "degraded"]


def test_health_check_response_format(test_db):
    """
    Test that health check response has correct format.
    
    **Validates: Requirement 12.9**
    """
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required top-level fields
    assert "status" in data
    assert "timestamp" in data
    assert "services" in data
    
    # Check that all expected services are present
    expected_services = ["database", "redis", "openclaw", "deepseek"]
    for service in expected_services:
        assert service in data["services"]
        assert "status" in data["services"][service]
        assert "message" in data["services"][service]
        assert data["services"][service]["status"] in ["healthy", "unhealthy"]


def test_health_check_database_service(test_db):
    """
    Test that health check includes database service status.
    
    **Validates: Requirement 12.9**
    """
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Database should be present in services
    assert "database" in data["services"]
    assert "status" in data["services"]["database"]
    assert "message" in data["services"]["database"]
    
    # Database status can be healthy or unhealthy depending on connection
    assert data["services"]["database"]["status"] in ["healthy", "unhealthy"]


def test_health_check_redis_service(test_db):
    """
    Test that health check includes Redis service status.
    
    **Validates: Requirement 12.9**
    """
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Redis should be present in services
    assert "redis" in data["services"]
    assert "status" in data["services"]["redis"]
    assert "message" in data["services"]["redis"]
    
    # Redis status can be healthy or unhealthy depending on whether Redis is running
    assert data["services"]["redis"]["status"] in ["healthy", "unhealthy"]


def test_health_check_llm_services(test_db):
    """
    Test that health check includes LLM service statuses.
    
    **Validates: Requirement 12.9**
    """
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # OpenClaw should be present
    assert "openclaw" in data["services"]
    assert "status" in data["services"]["openclaw"]
    assert "message" in data["services"]["openclaw"]
    assert data["services"]["openclaw"]["status"] in ["healthy", "unhealthy"]
    
    # DeepSeek should be present
    assert "deepseek" in data["services"]
    assert "status" in data["services"]["deepseek"]
    assert "message" in data["services"]["deepseek"]
    assert data["services"]["deepseek"]["status"] in ["healthy", "unhealthy"]


def test_health_check_overall_status_logic(test_db):
    """
    Test that overall status is 'degraded' if any service is unhealthy.
    
    **Validates: Requirement 12.9**
    """
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check if any service is unhealthy
    any_unhealthy = any(
        service["status"] == "unhealthy"
        for service in data["services"].values()
    )
    
    # If any service is unhealthy, overall status should be degraded
    if any_unhealthy:
        assert data["status"] == "degraded"
    else:
        assert data["status"] == "ok"


def test_health_check_timestamp_format(test_db):
    """
    Test that health check includes a valid timestamp.
    
    **Validates: Requirement 12.9**
    """
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check timestamp exists and is a string
    assert "timestamp" in data
    assert isinstance(data["timestamp"], str)
    
    # Check timestamp is in ISO format (basic validation)
    from datetime import datetime
    try:
        datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
    except ValueError:
        pytest.fail("Timestamp is not in valid ISO format")
