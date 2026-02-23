"""Integration tests for API routes."""
import pytest
import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from models.database import Base, get_db
from models.models import Agent, Topic, Message


# Create a shared test engine using PostgreSQL
from config.settings import settings
TEST_ENGINE = create_engine(
    settings.database_url,
    echo=False,
    poolclass=StaticPool  # Use StaticPool to share connection across threads
)

# Create tables once
Base.metadata.create_all(TEST_ENGINE)


# Test database setup
@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test function."""
    TestSessionLocal = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)
    session = TestSessionLocal()
    
    yield session
    
    # Clean up data after test
    session.rollback()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


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
        """
        Test health check endpoint returns proper status.
        
        Feature: dual-agent-chat, Property 47: 健康检查API
        Validates Requirement 12.9
        """
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
        
        # Status should be either "ok" or "degraded"
        assert data["status"] in ["ok", "degraded"]
        
        # Check that all services are reported
        assert "database" in data["services"]
        assert "redis" in data["services"]
        assert "openclaw" in data["services"]
        assert "deepseek" in data["services"]
        
        # Each service should have status and message
        for service_name, service_info in data["services"].items():
            assert "status" in service_info
            assert "message" in service_info
            assert service_info["status"] in ["healthy", "unhealthy"]


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


# ============================================================================
# Task 11.2: API Endpoint Integration Tests
# Requirements: 2.3, 5.1, 8.1, 12.1, 12.2, 12.3
# ============================================================================


class TestCompleteMessageSubmissionFlow:
    """
    Integration tests for complete message submission flow.
    Tests the full workflow from topic creation to message posting.
    
    Validates: Requirements 5.1, 5.2, 5.3, 5.4
    """
    
    def test_complete_message_flow(self, client, auth_headers, test_db):
        """Test complete flow: create topic -> post messages -> verify state."""
        # Step 1: Create a new topic
        create_response = client.post(
            "/api/topic",
            json={"title": "Integration Test Topic"},
            headers=auth_headers
        )
        assert create_response.status_code == 200
        topic_data = create_response.json()
        topic_id = topic_data["topic_id"]
        assert topic_data["status"] == "active"
        
        # Step 2: Post first message
        msg1_response = client.post(
            "/api/message",
            json={
                "topic_id": topic_id,
                "content": "First message in the discussion",
                "actual_tokens": 50
            },
            headers=auth_headers
        )
        assert msg1_response.status_code == 200
        msg1_data = msg1_response.json()
        assert "message_id" in msg1_data
        assert msg1_data["token_count"] == 50
        
        # Step 3: Post second message
        msg2_response = client.post(
            "/api/message",
            json={
                "topic_id": topic_id,
                "content": "Second message continuing the discussion",
                "actual_tokens": 75
            },
            headers=auth_headers
        )
        assert msg2_response.status_code == 200
        msg2_data = msg2_response.json()
        assert msg2_data["token_count"] == 125  # 50 + 75
        
        # Step 4: Retrieve messages and verify order
        messages_response = client.get(
            f"/api/topic/{topic_id}/messages",
            headers=auth_headers
        )
        assert messages_response.status_code == 200
        messages_data = messages_response.json()
        assert len(messages_data["messages"]) == 2
        # Verify chronological order (oldest first)
        assert messages_data["messages"][0]["content"] == "First message in the discussion"
        assert messages_data["messages"][1]["content"] == "Second message continuing the discussion"
        
        # Step 5: Verify topic state
        topic_response = client.get("/api/topic/active", headers=auth_headers)
        assert topic_response.status_code == 200
        topic_state = topic_response.json()
        assert topic_state["topic_id"] == topic_id
        assert topic_state["token_count_since_summary"] == 125
    
    def test_message_submission_with_token_accumulation(self, client, auth_headers, test_topic):
        """Test that token counts accumulate correctly across multiple messages."""
        initial_count = test_topic.token_count_since_summary
        
        # Post multiple messages
        token_increments = [10, 25, 30, 15]
        for i, tokens in enumerate(token_increments):
            response = client.post(
                "/api/message",
                json={
                    "topic_id": test_topic.id,
                    "content": f"Message {i}",
                    "actual_tokens": tokens
                },
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            expected_count = initial_count + sum(token_increments[:i+1])
            assert data["token_count"] == expected_count
    
    def test_message_submission_to_closed_topic_fails(self, client, auth_headers, test_topic, test_db):
        """Test that messages cannot be posted to closed topics."""
        # Close the topic
        test_topic.status = "closed"
        test_db.commit()
        
        # Attempt to post message
        response = client.post(
            "/api/message",
            json={
                "topic_id": test_topic.id,
                "content": "This should fail",
                "actual_tokens": 10
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "closed" in response.json()["detail"].lower()


class TestTopicCreationAndClosingFlow:
    """
    Integration tests for topic lifecycle management.
    Tests topic creation, closing negotiation, and state transitions.
    
    Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.7, 8.8, 8.9
    """
    
    def test_complete_topic_lifecycle(self, client, test_db):
        """Test complete topic lifecycle: create -> use -> close."""
        # Create two agents
        agent_a = Agent(
            id="agent_a",
            name="Agent A",
            auth_token_hash=bcrypt.hashpw(b"token_a", bcrypt.gensalt()).decode()
        )
        agent_b = Agent(
            id="agent_b",
            name="Agent B",
            auth_token_hash=bcrypt.hashpw(b"token_b", bcrypt.gensalt()).decode()
        )
        test_db.add(agent_a)
        test_db.add(agent_b)
        test_db.commit()
        
        headers_a = {"X-Agent-Id": "agent_a", "X-Auth-Token": "token_a"}
        headers_b = {"X-Agent-Id": "agent_b", "X-Auth-Token": "token_b"}
        
        # Step 1: Agent A creates topic
        create_response = client.post(
            "/api/topic",
            json={"title": "Lifecycle Test Topic"},
            headers=headers_a
        )
        assert create_response.status_code == 200
        topic_id = create_response.json()["topic_id"]
        
        # Step 2: Both agents post messages
        client.post(
            "/api/message",
            json={"topic_id": topic_id, "content": "Message from A", "actual_tokens": 10},
            headers=headers_a
        )
        client.post(
            "/api/message",
            json={"topic_id": topic_id, "content": "Message from B", "actual_tokens": 10},
            headers=headers_b
        )
        
        # Step 3: Agent A requests close
        close_response_a = client.post(
            f"/api/topic/{topic_id}/request-close",
            headers=headers_a
        )
        assert close_response_a.status_code == 200
        close_data_a = close_response_a.json()
        assert close_data_a["both_agreed"] is False
        assert close_data_a["status"] in ["active", "closing_pending"]
        
        # Step 4: Verify topic is still active (only one agent agreed)
        topic_response = client.get("/api/topic/active", headers=headers_a)
        assert topic_response.status_code == 200
        
        # Step 5: Agent B also requests close
        close_response_b = client.post(
            f"/api/topic/{topic_id}/request-close",
            headers=headers_b
        )
        assert close_response_b.status_code == 200
        close_data_b = close_response_b.json()
        assert close_data_b["both_agreed"] is True
        
        # Step 6: Verify topic is now closed
        topic_final = client.get("/api/topic/active", headers=headers_a)
        # Should return 404 since no active topic exists
        assert topic_final.status_code == 404
    
    def test_close_request_cancellation(self, client, test_db):
        """Test that close requests can be cancelled."""
        # Setup agent and topic
        agent = Agent(
            id="agent_cancel",
            name="Cancel Agent",
            auth_token_hash=bcrypt.hashpw(b"token_cancel", bcrypt.gensalt()).decode()
        )
        test_db.add(agent)
        test_db.commit()
        
        headers = {"X-Agent-Id": "agent_cancel", "X-Auth-Token": "token_cancel"}
        
        # Create topic
        create_response = client.post("/api/topic", json={}, headers=headers)
        topic_id = create_response.json()["topic_id"]
        
        # Request close
        close_response = client.post(
            f"/api/topic/{topic_id}/request-close",
            headers=headers
        )
        assert close_response.status_code == 200
        
        # Cancel close request
        cancel_response = client.post(
            f"/api/topic/{topic_id}/cancel-close",
            headers=headers
        )
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "success"
        
        # Verify topic is still active
        topic_response = client.get("/api/topic/active", headers=headers)
        assert topic_response.status_code == 200
        assert topic_response.json()["status"] == "active"
    
    def test_topic_creation_with_and_without_title(self, client, auth_headers):
        """Test topic creation with explicit and default titles."""
        # With explicit title
        response1 = client.post(
            "/api/topic",
            json={"title": "Custom Title"},
            headers=auth_headers
        )
        assert response1.status_code == 200
        assert response1.json()["title"] == "Custom Title"
        
        # Without title (should use default)
        response2 = client.post(
            "/api/topic",
            json={},
            headers=auth_headers
        )
        assert response2.status_code == 200
        assert "Discussion Topic" in response2.json()["title"]


class TestAuthenticationOnAllEndpoints:
    """
    Integration tests for authentication requirements.
    Verifies that all protected endpoints require valid authentication.
    
    Validates: Requirements 2.3, 2.4, 12.2
    """
    
    def test_all_endpoints_require_authentication(self, client, test_topic):
        """Test that all protected endpoints reject requests without authentication."""
        endpoints = [
            ("GET", "/api/topic/active", None),
            ("GET", f"/api/topic/{test_topic.id}/messages", None),
            ("POST", "/api/message", {"topic_id": test_topic.id, "content": "test", "actual_tokens": 10}),
            ("POST", f"/api/topic/{test_topic.id}/request-close", None),
            ("POST", f"/api/topic/{test_topic.id}/cancel-close", None),
            ("POST", "/api/topic", {"title": "test"}),
            ("GET", f"/api/topic/{test_topic.id}/summary-history", None),
            ("POST", f"/api/topic/{test_topic.id}/rollback-summary", {"history_id": "test"}),
        ]
        
        for method, url, json_data in endpoints:
            if method == "GET":
                response = client.get(url)
            else:
                response = client.post(url, json=json_data)
            
            assert response.status_code == 401, f"Endpoint {method} {url} should require auth"
            assert "detail" in response.json()
    
    def test_invalid_agent_id_rejected(self, client, test_topic):
        """Test that requests with invalid agent_id are rejected."""
        headers = {
            "X-Agent-Id": "nonexistent_agent",
            "X-Auth-Token": "some_token"
        }
        
        response = client.get("/api/topic/active", headers=headers)
        assert response.status_code == 401
    
    def test_invalid_auth_token_rejected(self, client, test_agent):
        """Test that requests with invalid auth token are rejected."""
        headers = {
            "X-Agent-Id": test_agent.id,
            "X-Auth-Token": "wrong_token"
        }
        
        response = client.get("/api/topic/active", headers=headers)
        assert response.status_code == 401
    
    def test_missing_auth_headers_rejected(self, client):
        """Test that requests missing auth headers are rejected."""
        # Missing both headers
        response1 = client.get("/api/topic/active")
        assert response1.status_code == 401
        
        # Missing X-Auth-Token
        response2 = client.get("/api/topic/active", headers={"X-Agent-Id": "test"})
        assert response2.status_code == 401
        
        # Missing X-Agent-Id
        response3 = client.get("/api/topic/active", headers={"X-Auth-Token": "test"})
        assert response3.status_code == 401
    
    def test_valid_authentication_succeeds(self, client, auth_headers, test_topic):
        """Test that requests with valid authentication succeed."""
        response = client.get("/api/topic/active", headers=auth_headers)
        # Should succeed (200) or return 404 if no active topic
        assert response.status_code in [200, 404]


class TestErrorResponses:
    """
    Integration tests for error handling and HTTP status codes.
    Verifies correct error responses for various failure scenarios.
    
    Validates: Requirements 12.1, 12.2, 12.3
    """
    
    def test_400_bad_request_errors(self, client, auth_headers, test_topic, test_db):
        """Test 400 Bad Request errors for invalid parameters."""
        # Invalid topic_id in message post
        response1 = client.post(
            "/api/message",
            json={
                "topic_id": "nonexistent_topic",
                "content": "test",
                "actual_tokens": 10
            },
            headers=auth_headers
        )
        assert response1.status_code == 400
        assert "detail" in response1.json()
        
        # Post to closed topic
        test_topic.status = "closed"
        test_db.commit()
        
        response2 = client.post(
            "/api/message",
            json={
                "topic_id": test_topic.id,
                "content": "test",
                "actual_tokens": 10
            },
            headers=auth_headers
        )
        assert response2.status_code == 400
        
        # Invalid rollback history_id
        response3 = client.post(
            f"/api/topic/{test_topic.id}/rollback-summary",
            json={"history_id": "nonexistent_history"},
            headers=auth_headers
        )
        assert response3.status_code == 400
    
    def test_401_unauthorized_errors(self, client, test_topic):
        """Test 401 Unauthorized errors for authentication failures."""
        # No authentication
        response1 = client.get("/api/topic/active")
        assert response1.status_code == 401
        
        # Invalid credentials
        response2 = client.get(
            "/api/topic/active",
            headers={"X-Agent-Id": "fake", "X-Auth-Token": "fake"}
        )
        assert response2.status_code == 401
        
        # Verify error response format
        error_data = response2.json()
        assert "detail" in error_data
    
    def test_404_not_found_errors(self, client, auth_headers):
        """Test 404 Not Found errors for missing resources."""
        # No active topic exists
        response1 = client.get("/api/topic/active", headers=auth_headers)
        assert response1.status_code == 404
        assert "detail" in response1.json()
        
        # Request close on nonexistent topic
        response2 = client.post(
            "/api/topic/nonexistent_topic/request-close",
            headers=auth_headers
        )
        assert response2.status_code == 404
    
    def test_error_response_format(self, client, auth_headers):
        """Test that error responses follow consistent format."""
        # Trigger a 404 error
        response = client.get("/api/topic/active", headers=auth_headers)
        
        if response.status_code >= 400:
            error_data = response.json()
            # Should have detail field
            assert "detail" in error_data
            # Detail should be a string
            assert isinstance(error_data["detail"], str)
    
    def test_validation_errors_return_400(self, client, auth_headers, test_topic):
        """Test that validation errors return 400 with descriptive messages."""
        # Missing required field
        response1 = client.post(
            "/api/message",
            json={
                "topic_id": test_topic.id,
                "content": "test"
                # Missing actual_tokens
            },
            headers=auth_headers
        )
        assert response1.status_code == 422  # FastAPI validation error
        
        # Invalid data type
        response2 = client.post(
            "/api/message",
            json={
                "topic_id": test_topic.id,
                "content": "test",
                "actual_tokens": "not_a_number"  # Should be int
            },
            headers=auth_headers
        )
        assert response2.status_code == 422


class TestSummaryHistoryIntegration:
    """
    Integration tests for summary history functionality.
    Tests history retrieval and rollback operations.
    
    Validates: Requirements 11.1, 11.2, 11.4, 11.5
    """
    
    def test_summary_history_retrieval(self, client, auth_headers, test_topic, test_db):
        """Test retrieving summary history for a topic."""
        from models.models import SummaryHistory
        
        # Create multiple history records
        for i in range(3):
            history = SummaryHistory(
                id=f"history_{i}",
                topic_id=test_topic.id,
                summary=f"Summary version {i}",
                llm_suggestion="continue",
                end_score=float(i * 10)
            )
            test_db.add(history)
        test_db.commit()
        
        # Retrieve history
        response = client.get(
            f"/api/topic/{test_topic.id}/summary-history",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert len(data["history"]) == 3
        
        # Verify history items have required fields
        for item in data["history"]:
            assert "history_id" in item
            assert "summary" in item
            assert "llm_suggestion" in item
            assert "end_score" in item
            assert "created_at" in item
    
    def test_summary_history_with_limit(self, client, auth_headers, test_topic, test_db):
        """Test retrieving summary history with limit parameter."""
        from models.models import SummaryHistory
        
        # Create 5 history records
        for i in range(5):
            history = SummaryHistory(
                id=f"history_limit_{i}",
                topic_id=test_topic.id,
                summary=f"Summary {i}",
                llm_suggestion="continue",
                end_score=50.0
            )
            test_db.add(history)
        test_db.commit()
        
        # Retrieve with limit
        response = client.get(
            f"/api/topic/{test_topic.id}/summary-history?limit=2",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["history"]) == 2
    
    def test_summary_rollback(self, client, auth_headers, test_topic, test_db):
        """Test rolling back summary to a previous version."""
        from models.models import SummaryHistory, AuditLog
        
        # Create a history record
        history = SummaryHistory(
            id="history_rollback",
            topic_id=test_topic.id,
            summary="Previous summary version",
            llm_suggestion="change_angle",
            end_score=75.0
        )
        test_db.add(history)
        test_db.commit()
        
        # Rollback to this version
        response = client.post(
            f"/api/topic/{test_topic.id}/rollback-summary",
            json={"history_id": "history_rollback"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify topic was updated
        test_db.refresh(test_topic)
        assert test_topic.summary == "Previous summary version"
        assert test_topic.llm_suggestion == "change_angle"
        assert test_topic.end_score == 75.0
        
        # Verify audit log was recorded (Requirement 11.6)
        audit_logs = test_db.query(AuditLog).filter(
            AuditLog.operation_type == "summary_rolled_back",
            AuditLog.topic_id == test_topic.id
        ).all()
        
        assert len(audit_logs) > 0
        latest_log = audit_logs[-1]
        assert latest_log.agent_id == "agent_test"  # Fixed: correct agent_id
        assert latest_log.details is not None
        
        import json
        details = json.loads(latest_log.details)
        assert details["history_id"] == "history_rollback"


class TestConcurrentOperations:
    """
    Integration tests for concurrent operations.
    Tests system behavior under concurrent access patterns.
    
    Validates: Requirements 1.4, 6.14, 10.5
    """
    
    def test_concurrent_message_posting(self, client, test_db):
        """Test that concurrent message posts to same topic are handled correctly."""
        # Create agents
        agent_a = Agent(
            id="concurrent_a",
            name="Agent A",
            auth_token_hash=bcrypt.hashpw(b"token_a", bcrypt.gensalt()).decode()
        )
        agent_b = Agent(
            id="concurrent_b",
            name="Agent B",
            auth_token_hash=bcrypt.hashpw(b"token_b", bcrypt.gensalt()).decode()
        )
        test_db.add(agent_a)
        test_db.add(agent_b)
        test_db.commit()
        
        headers_a = {"X-Agent-Id": "concurrent_a", "X-Auth-Token": "token_a"}
        headers_b = {"X-Agent-Id": "concurrent_b", "X-Auth-Token": "token_b"}
        
        # Create topic
        create_response = client.post("/api/topic", json={}, headers=headers_a)
        topic_id = create_response.json()["topic_id"]
        
        # Post messages from both agents
        response_a = client.post(
            "/api/message",
            json={"topic_id": topic_id, "content": "Message from A", "actual_tokens": 50},
            headers=headers_a
        )
        response_b = client.post(
            "/api/message",
            json={"topic_id": topic_id, "content": "Message from B", "actual_tokens": 30},
            headers=headers_b
        )
        
        assert response_a.status_code == 200
        assert response_b.status_code == 200
        
        # Verify both messages were stored
        messages_response = client.get(
            f"/api/topic/{topic_id}/messages",
            headers=headers_a
        )
        assert messages_response.status_code == 200
        messages = messages_response.json()["messages"]
        assert len(messages) == 2
        
        # Verify token count is correct (50 + 30 = 80)
        topic_response = client.get("/api/topic/active", headers=headers_a)
        assert topic_response.status_code == 200
        assert topic_response.json()["token_count_since_summary"] == 80
    
    def test_multiple_topics_isolation(self, client, test_db):
        """Test that multiple topics maintain independent state."""
        # Create agent
        agent = Agent(
            id="multi_topic_agent",
            name="Multi Topic Agent",
            auth_token_hash=bcrypt.hashpw(b"token_multi", bcrypt.gensalt()).decode()
        )
        test_db.add(agent)
        test_db.commit()
        
        headers = {"X-Agent-Id": "multi_topic_agent", "X-Auth-Token": "token_multi"}
        
        # Create first topic and post message
        topic1_response = client.post("/api/topic", json={"title": "Topic 1"}, headers=headers)
        topic1_id = topic1_response.json()["topic_id"]
        
        client.post(
            "/api/message",
            json={"topic_id": topic1_id, "content": "Message in topic 1", "actual_tokens": 100},
            headers=headers
        )
        
        # Close first topic
        from models.models import Topic
        topic1 = test_db.query(Topic).filter_by(id=topic1_id).first()
        topic1.status = "closed"
        test_db.commit()
        
        # Create second topic and post message
        topic2_response = client.post("/api/topic", json={"title": "Topic 2"}, headers=headers)
        topic2_id = topic2_response.json()["topic_id"]
        
        client.post(
            "/api/message",
            json={"topic_id": topic2_id, "content": "Message in topic 2", "actual_tokens": 50},
            headers=headers
        )
        
        # Verify topics are independent
        topic2 = test_db.query(Topic).filter_by(id=topic2_id).first()
        assert topic2.token_count_since_summary == 50
        assert topic2.status == "active"
        
        # Verify active topic is topic 2
        active_response = client.get("/api/topic/active", headers=headers)
        assert active_response.status_code == 200
        assert active_response.json()["topic_id"] == topic2_id
