"""Basic tests to verify project setup."""
import pytest
from fastapi.testclient import TestClient


def test_config_loads():
    """Test that configuration loads correctly."""
    from config.settings import settings
    
    assert settings.database_url is not None
    assert settings.redis_url is not None
    assert settings.summary_threshold == 8000
    assert settings.closing_timeout == 300
    assert settings.max_retries == 3


def test_database_connection():
    """Test that database connection can be established."""
    from models.database import engine, SessionLocal
    
    # Test engine creation
    assert engine is not None
    
    # Test session creation
    db = SessionLocal()
    assert db is not None
    db.close()


def test_celery_app_loads():
    """Test that Celery app loads correctly."""
    from workers.celery_app import celery_app
    
    assert celery_app is not None
    assert celery_app.conf.broker_url is not None
    assert celery_app.conf.result_backend is not None


def test_fastapi_app_loads():
    """Test that FastAPI app loads correctly."""
    from main import app
    
    assert app is not None
    assert app.title == "Dual Agent Chat Platform"
    assert app.version == "1.0.0"


def test_root_endpoint():
    """Test the root endpoint."""
    from main import app
    
    client = TestClient(app)
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Dual Agent Chat Platform API"
    assert data["version"] == "1.0.0"


def test_health_endpoint():
    """Test the health check endpoint."""
    from main import app
    
    client = TestClient(app)
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_redis_connection():
    """Test Redis connection."""
    from config.settings import settings
    import redis
    
    r = redis.from_url(settings.redis_url)
    assert r.ping() is True


def test_retry_delays_parsing():
    """Test that retry delays are parsed correctly."""
    from config.settings import settings
    
    delays = settings.retry_delays_list
    assert delays == [1, 2, 4]
    assert len(delays) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
