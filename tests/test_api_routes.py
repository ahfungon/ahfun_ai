"""Integration tests for API routes."""
import pytest
import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from models.database import Base, get_db
from models.models import Agent, Topic, Message


# Test database setup
@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test function."""
    # Use check_same_thread=False for SQLite to work with FastAPI TestClient
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    
    TestSessionLocal = sessionmaker(bind=engine)
    session = TestSessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_agent(test_db):
    """Create a test agent."""
    agent = Agent(
        id="agent_test",
        name="Test Agent",
        auth_token_hash=bcrypt.hashpw(b"test_token", bcrypt.gensalt()).decode()
    )
    test_db.add(agent)
    test_db.commit()
    test_db.refresh(agent)
    return agent


@pytest.fixture(scope="function")
def auth_headers(test_agent):
    """Create authentication headers."""
    return {
        "X-Agent-Id": test_agent.id,
        "X-Auth-Token": "test_token"
    }


@pytest.fixture(scope="function")
def test_topic(test_db):
    """Create a test topic."""
    topic = Topic(
        id="topic_test",
        title="Test Topic",
        status="active",
        summary="",
        token_count_since_summary=0,
        pending_summary_job=False,
        agent_a_wants_close=False,
        agent_b_wants_close=False
    )
    test_db.add(topic)
    test_db.commit()
    test_db.refresh(topic)
    return topic


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint returns OK."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestAuthenticationRequired:
    """Tests for authentication requirement."""
    
    def test_get_active_topic_requires_auth(self, client):
        """Test that getting active topic requires authentication."""
        response = client.get("/api/topic/active")
        assert response.status_code == 401
    
    def test_invalid_auth_token(self, client, test_agent):
        """Test that invalid auth token is rejected."""
        headers = {
            "X-Agent-Id": test_agent.id,
            "X-Auth-Token": "wrong_token"
        }
        response = client.get("/api/topic/active", headers=headers)
        assert response.status_code == 401


class TestTopicEndpoints:
    """Tests for topic-related endpoints."""
    
    def test_create_topic(self, client, auth_headers):
        """Test creating a new topic."""
        response = client.post(
            "/api/topic",
            json={"title": "New Topic"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "topic_id" in data
        assert data["status"] == "active"
        assert data["title"] == "New Topic"
    
    def test_create_topic_without_title(self, client, auth_headers):
        """Test creating a topic without providing title."""
        response = client.post(
            "/api/topic",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "topic_id" in data
        assert data["status"] == "active"
        # Should have a default title
        assert "Discussion Topic" in data["title"]
    
    def test_get_active_topic(self, client, auth_headers, test_topic):
        """Test getting active topic."""
        response = client.get("/api/topic/active", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["topic_id"] == test_topic.id
        assert data["status"] == "active"
    
    def test_get_active_topic_not_found(self, client, auth_headers):
        """Test getting active topic when none exists."""
        response = client.get("/api/topic/active", headers=auth_headers)
        assert response.status_code == 404


class TestMessageEndpoints:
    """Tests for message-related endpoints."""
    
    def test_post_message(self, client, auth_headers, test_topic):
        """Test posting a message to a topic."""
        response = client.post(
            "/api/message",
            json={
                "topic_id": test_topic.id,
                "content": "Test message",
                "actual_tokens": 10
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data
        assert data["token_count"] == 10
    
    def test_post_message_to_nonexistent_topic(self, client, auth_headers):
        """Test posting message to non-existent topic."""
        response = client.post(
            "/api/message",
            json={
                "topic_id": "nonexistent",
                "content": "Test message",
                "actual_tokens": 10
            },
            headers=auth_headers
        )
        assert response.status_code == 400
    
    def test_get_messages(self, client, auth_headers, test_topic, test_db):
        """Test getting messages for a topic."""
        # Create some messages
        for i in range(3):
            msg = Message(
                id=f"msg_{i}",
                topic_id=test_topic.id,
                agent_id="agent_test",
                content=f"Message {i}",
                actual_tokens=10
            )
            test_db.add(msg)
        test_db.commit()
        
        response = client.get(
            f"/api/topic/{test_topic.id}/messages",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 3
        # Messages should be sorted oldest to newest
        assert data["messages"][0]["content"] == "Message 0"
    
    def test_get_messages_with_limit(self, client, auth_headers, test_topic, test_db):
        """Test getting messages with limit parameter."""
        # Create 5 messages
        for i in range(5):
            msg = Message(
                id=f"msg_{i}",
                topic_id=test_topic.id,
                agent_id="agent_test",
                content=f"Message {i}",
                actual_tokens=10
            )
            test_db.add(msg)
        test_db.commit()
        
        response = client.get(
            f"/api/topic/{test_topic.id}/messages?limit=2",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2


class TestCloseRequestEndpoints:
    """Tests for topic close request endpoints."""
    
    def test_request_close(self, client, auth_headers, test_topic):
        """Test requesting to close a topic."""
        response = client.post(
            f"/api/topic/{test_topic.id}/request-close",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["active", "closing_pending"]
        assert "both_agreed" in data
    
    def test_cancel_close_request(self, client, auth_headers, test_topic, test_db):
        """Test canceling a close request."""
        # First request close
        test_topic.agent_a_wants_close = True
        test_topic.closing_requested_by = "agent_test"
        test_topic.status = "closing_pending"
        test_db.commit()
        
        response = client.post(
            f"/api/topic/{test_topic.id}/cancel-close",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestSummaryHistoryEndpoints:
    """Tests for summary history endpoints."""
    
    def test_get_summary_history(self, client, auth_headers, test_topic):
        """Test getting summary history for a topic."""
        response = client.get(
            f"/api/topic/{test_topic.id}/summary-history",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)
    
    def test_rollback_summary(self, client, auth_headers, test_topic, test_db):
        """Test rolling back summary to a historical version."""
        from models.models import SummaryHistory
        
        # Create a history record
        history = SummaryHistory(
            id="history_test",
            topic_id=test_topic.id,
            summary="Old summary",
            llm_suggestion="continue",
            end_score=50.0
        )
        test_db.add(history)
        test_db.commit()
        
        response = client.post(
            f"/api/topic/{test_topic.id}/rollback-summary",
            json={"history_id": "history_test"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
