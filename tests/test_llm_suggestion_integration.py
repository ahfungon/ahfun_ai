"""
Tests for LLM suggestion integration in API responses and force_end logic.

This module tests Task 18.1 requirements:
- LLM suggestion field in API responses
- Hint messages for change_angle and suggest_end
- force_end automatic closing_pending setting
- Ignoring new LLM suggestions when in closing_pending state

Validates Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8
"""
import pytest
import uuid
import bcrypt
from datetime import datetime
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from main import app
from models.models import Topic, Message, Agent, SummaryJob
from models.database import Base, get_db
from services.summary_service import SummaryService
from services.topic_service import TopicService
from workers.tasks import process_summary_job


# Create a shared test engine using PostgreSQL
from config.settings import settings
TEST_ENGINE = create_engine(
    settings.database_url,
    echo=False,
    poolclass=StaticPool  # Use StaticPool to share connection across threads
)

# Create tables once
Base.metadata.create_all(TEST_ENGINE)


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
def test_client(test_db: Session):
    """Create test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_agent(test_db: Session):
    """Create a test agent for authentication."""
    agent = Agent(
        id="test_agent",
        name="Test Agent",
        auth_token_hash=bcrypt.hashpw(b"test_token", bcrypt.gensalt()).decode()
    )
    test_db.add(agent)
    test_db.commit()
    test_db.refresh(agent)
    return agent


@pytest.fixture(scope="function")
def auth_headers(test_agent: Agent):
    """Create authentication headers."""
    return {
        "X-Agent-Id": test_agent.id,
        "X-Auth-Token": "test_token"
    }


class TestLLMSuggestionInAPIResponse:
    """Test that LLM suggestions are included in API responses."""
    
    def test_active_topic_includes_llm_suggestion(
        self,
        test_client: TestClient,
        test_db: Session,
        test_agent: Agent,
        auth_headers: dict
    ):
        """
        Test that GET /api/topic/active includes llm_suggestion field.
        
        Validates Requirement 7.1
        """
        # Create topic with LLM suggestion
        topic = Topic(
            id=str(uuid.uuid4()),
            title="Test Topic",
            status="active",
            summary="Test summary",
            llm_suggestion="continue",
            end_score=25.0,
            token_count_since_summary=100
        )
        test_db.add(topic)
        test_db.commit()
        
        # Get active topic
        response = test_client.get("/api/topic/active", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify llm_suggestion is included
        assert "llm_suggestion" in data
        assert data["llm_suggestion"] == "continue"
        assert data["end_score"] == 25.0
    
    def test_all_suggestion_types_returned(
        self,
        test_client: TestClient,
        test_db: Session,
        test_agent: Agent,
        auth_headers: dict
    ):
        """
        Test that all LLM suggestion types are correctly returned.
        
        Validates Requirement 7.1, 7.6
        """
        suggestions = ["continue", "change_angle", "suggest_end", "force_end"]
        
        for suggestion in suggestions:
            # Create topic with specific suggestion
            topic = Topic(
                id=str(uuid.uuid4()),
                title=f"Test Topic {suggestion}",
                status="active",
                summary="Test summary",
                llm_suggestion=suggestion,
                end_score=50.0,
                token_count_since_summary=100
            )
            test_db.add(topic)
            test_db.commit()
            
            # Get active topic
            response = test_client.get("/api/topic/active", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["llm_suggestion"] == suggestion
            
            # Clean up for next iteration
            test_db.delete(topic)
            test_db.commit()


class TestLLMHintMessages:
    """Test hint messages for change_angle and suggest_end suggestions."""
    
    def test_continue_no_hint(
        self,
        test_client: TestClient,
        test_db: Session,
        test_agent: Agent,
        auth_headers: dict
    ):
        """
        Test that 'continue' suggestion has no hint message.
        
        Validates Requirement 7.2
        """
        topic = Topic(
            id=str(uuid.uuid4()),
            title="Test Topic",
            status="active",
            summary="Test summary",
            llm_suggestion="continue",
            end_score=25.0,
            token_count_since_summary=100
        )
        test_db.add(topic)
        test_db.commit()
        
        response = test_client.get("/api/topic/active", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # continue should have no hint
        assert data["llm_hint"] is None
    
    def test_change_angle_hint(
        self,
        test_client: TestClient,
        test_db: Session,
        test_agent: Agent,
        auth_headers: dict
    ):
        """
        Test that 'change_angle' suggestion includes hint message.
        
        Validates Requirement 7.3
        """
        topic = Topic(
            id=str(uuid.uuid4()),
            title="Test Topic",
            status="active",
            summary="Test summary",
            llm_suggestion="change_angle",
            end_score=50.0,
            token_count_since_summary=100
        )
        test_db.add(topic)
        test_db.commit()
        
        response = test_client.get("/api/topic/active", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # change_angle should have hint
        assert data["llm_hint"] is not None
        assert "different perspective" in data["llm_hint"].lower() or "angle" in data["llm_hint"].lower()
    
    def test_suggest_end_hint(
        self,
        test_client: TestClient,
        test_db: Session,
        test_agent: Agent,
        auth_headers: dict
    ):
        """
        Test that 'suggest_end' suggestion includes hint message.
        
        Validates Requirement 7.4
        """
        topic = Topic(
            id=str(uuid.uuid4()),
            title="Test Topic",
            status="active",
            summary="Test summary",
            llm_suggestion="suggest_end",
            end_score=75.0,
            token_count_since_summary=100
        )
        test_db.add(topic)
        test_db.commit()
        
        response = test_client.get("/api/topic/active", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # suggest_end should have hint
        assert data["llm_hint"] is not None
        assert "conclusion" in data["llm_hint"].lower() or "end" in data["llm_hint"].lower()


class TestForceEndLogic:
    """Test force_end automatic closing_pending setting."""
    
    def test_force_end_sets_closing_pending(
        self,
        test_db: Session
    ):
        """
        Test that force_end suggestion automatically sets topic to closing_pending.
        
        Validates Requirement 7.5
        """
        # Create topic
        topic = Topic(
            id=str(uuid.uuid4()),
            title="Test Topic",
            status="active",
            summary="Old summary",
            llm_suggestion="continue",
            end_score=20.0,
            token_count_since_summary=0,
            pending_summary_job=False
        )
        test_db.add(topic)
        test_db.commit()
        
        # Apply force_end suggestion
        summary_service = SummaryService(test_db)
        summary_service.apply_llm_suggestion(topic, "force_end")
        
        # Verify topic is now closing_pending
        test_db.refresh(topic)
        assert topic.status == "closing_pending"
        assert topic.closing_requested_by == "system"
        assert topic.closing_requested_at is not None
    
    def test_force_end_in_worker(
        self,
        test_db: Session
    ):
        """
        Test that Worker applies force_end suggestion correctly.
        
        Validates Requirement 7.5 (integration with Worker)
        """
        # Create topic and messages
        topic = Topic(
            id="topic-1",
            title="Test Topic",
            status="active",
            summary="Old summary",
            llm_suggestion="continue",
            end_score=20.0,
            token_count_since_summary=9000,
            pending_summary_job=True
        )
        test_db.add(topic)
        
        msg1 = Message(
            id="msg-1",
            topic_id="topic-1",
            agent_id="agent_a",
            content="Message 1",
            actual_tokens=100
        )
        msg2 = Message(
            id="msg-2",
            topic_id="topic-1",
            agent_id="agent_b",
            content="Message 2",
            actual_tokens=100
        )
        test_db.add_all([msg1, msg2])
        
        job = SummaryJob(
            id="job-1",
            topic_id="topic-1",
            start_message_id=None,
            end_message_id="msg-2",
            status="pending",
            retry_count=0
        )
        test_db.add(job)
        test_db.commit()
        
        # Mock LLM to return force_end
        with patch('services.summary_service.SummaryService._call_deepseek_api') as mock_llm:
            mock_llm.return_value = {
                "summary": "Conversation should end",
                "suggestion": "force_end",
                "end_score": 95.0
            }
            
            # Process job
            process_summary_job("job-1", db_session=test_db)
        
        # Verify topic is closing_pending
        test_db.refresh(topic)
        assert topic.status == "closing_pending"
        assert topic.llm_suggestion == "force_end"
        assert topic.closing_requested_by == "system"


class TestIgnoreSuggestionsInClosingPending:
    """Test that new LLM suggestions are ignored when in closing_pending state."""
    
    def test_no_hint_when_closing_pending(
        self,
        test_client: TestClient,
        test_db: Session,
        test_agent: Agent,
        auth_headers: dict
    ):
        """
        Test that no hint is provided when topic is in closing_pending state.
        
        Validates Requirement 7.8
        """
        topic = Topic(
            id=str(uuid.uuid4()),
            title="Test Topic",
            status="closing_pending",
            summary="Test summary",
            llm_suggestion="suggest_end",
            end_score=75.0,
            token_count_since_summary=100,
            closing_requested_by="agent_a",
            closing_requested_at=datetime.utcnow()
        )
        test_db.add(topic)
        test_db.commit()
        
        response = test_client.get("/api/topic/active", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # No hint should be provided when closing_pending
        assert data["llm_hint"] is None
        assert data["status"] == "closing_pending"
    
    def test_apply_llm_suggestion_ignores_when_closing_pending(
        self,
        test_db: Session
    ):
        """
        Test that apply_llm_suggestion ignores suggestions when in closing_pending.
        
        Validates Requirement 7.8
        """
        # Create topic in closing_pending state
        topic = Topic(
            id=str(uuid.uuid4()),
            title="Test Topic",
            status="closing_pending",
            summary="Test summary",
            llm_suggestion="suggest_end",
            end_score=75.0,
            token_count_since_summary=0,
            closing_requested_by="agent_a",
            closing_requested_at=datetime.utcnow()
        )
        test_db.add(topic)
        test_db.commit()
        
        original_status = topic.status
        original_requested_by = topic.closing_requested_by
        
        # Try to apply force_end (should be ignored)
        summary_service = SummaryService(test_db)
        summary_service.apply_llm_suggestion(topic, "force_end")
        
        # Verify status unchanged
        test_db.refresh(topic)
        assert topic.status == original_status
        assert topic.closing_requested_by == original_requested_by
    
    def test_worker_preserves_suggestion_when_closing_pending(
        self,
        test_db: Session
    ):
        """
        Test that Worker preserves old suggestion when topic is closing_pending.
        
        Validates Requirement 7.8
        """
        # Create topic in closing_pending state
        topic = Topic(
            id="topic-1",
            title="Test Topic",
            status="closing_pending",
            summary="Old summary",
            llm_suggestion="suggest_end",
            end_score=75.0,
            token_count_since_summary=9000,
            pending_summary_job=True,
            closing_requested_by="agent_a",
            closing_requested_at=datetime.utcnow()
        )
        test_db.add(topic)
        
        msg1 = Message(
            id="msg-1",
            topic_id="topic-1",
            agent_id="agent_a",
            content="Message 1",
            actual_tokens=100
        )
        test_db.add(msg1)
        
        job = SummaryJob(
            id="job-1",
            topic_id="topic-1",
            start_message_id=None,
            end_message_id="msg-1",
            status="pending",
            retry_count=0
        )
        test_db.add(job)
        test_db.commit()
        
        # Mock LLM to return different suggestion
        with patch('services.summary_service.SummaryService._call_deepseek_api') as mock_llm:
            mock_llm.return_value = {
                "summary": "New summary",
                "suggestion": "continue",  # Different from current
                "end_score": 30.0
            }
            
            # Process job
            process_summary_job("job-1", db_session=test_db)
        
        # Verify old suggestion and end_score preserved
        test_db.refresh(topic)
        assert topic.llm_suggestion == "suggest_end"  # Original preserved
        assert topic.end_score == 75.0  # Original preserved
        assert topic.summary == "New summary"  # Summary updated
        assert topic.status == "closing_pending"  # Status unchanged


class TestClosingRequestTimestamp:
    """Test that closing requests record timestamp correctly."""
    
    def test_closing_request_records_timestamp(
        self,
        test_db: Session
    ):
        """
        Test that record_close_request records closing_requested_at timestamp.
        
        Feature: dual-agent-chat, Property 38: 关闭请求记录时间
        Validates Requirement 8.2
        """
        from services.topic_service import TopicService
        
        # Create topic
        topic_service = TopicService(test_db)
        topic = topic_service.create_topic(title="Test Topic")
        
        # Record time before request
        time_before = datetime.utcnow()
        
        # Record close request
        topic_service.record_close_request(topic.id, "agent_a")
        
        # Record time after request
        time_after = datetime.utcnow()
        
        # Verify timestamp was recorded
        test_db.refresh(topic)
        assert topic.closing_requested_at is not None
        assert topic.closing_requested_by == "agent_a"
        
        # Verify timestamp is within reasonable range
        assert time_before <= topic.closing_requested_at <= time_after
    
    def test_closing_status_includes_timestamp(
        self,
        test_client: TestClient,
        test_db: Session,
        test_agent: Agent,
        auth_headers: dict
    ):
        """
        Test that closing status API includes closing_requested_at.
        
        Feature: dual-agent-chat, Property 38: 关闭请求记录时间
        Validates Requirement 8.10
        """
        from services.topic_service import TopicService
        
        # Create topic and record close request
        topic_service = TopicService(test_db)
        topic = topic_service.create_topic(title="Test Topic")
        topic_service.record_close_request(topic.id, "agent_a")
        
        # Get active topic via API
        response = test_client.get("/api/topic/active", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify closing_status includes timestamp
        assert data["status"] == "closing_pending"
        assert data["closing_status"] is not None
        assert "closing_requested_at" in data["closing_status"]
        assert data["closing_status"]["closing_requested_at"] is not None
        assert data["closing_status"]["closing_requested_by"] == "agent_a"
    
    def test_force_end_records_system_timestamp(
        self,
        test_db: Session
    ):
        """
        Test that force_end records closing_requested_at with system as requester.
        
        Feature: dual-agent-chat, Property 38: 关闭请求记录时间
        Validates Requirement 7.5, 8.2
        """
        from services.summary_service import SummaryService
        
        # Create topic
        topic = Topic(
            id=str(uuid.uuid4()),
            title="Test Topic",
            status="active",
            summary="Test summary",
            llm_suggestion="continue",
            end_score=20.0,
            token_count_since_summary=0
        )
        test_db.add(topic)
        test_db.commit()
        
        # Record time before applying force_end
        time_before = datetime.utcnow()
        
        # Apply force_end
        summary_service = SummaryService(test_db)
        summary_service.apply_llm_suggestion(topic, "force_end")
        
        # Record time after
        time_after = datetime.utcnow()
        
        # Verify timestamp was recorded
        test_db.refresh(topic)
        assert topic.closing_requested_at is not None
        assert topic.closing_requested_by == "system"
        assert time_before <= topic.closing_requested_at <= time_after


class TestCrossModuleIntegration:
    """Test integration across SummaryService, Worker, and API routes."""
    
    def test_end_to_end_force_end_flow(
        self,
        test_client: TestClient,
        test_db: Session,
        test_agent: Agent,
        auth_headers: dict
    ):
        """
        Test complete flow: LLM suggests force_end -> Worker applies -> API returns closing_pending.
        
        Validates Requirements 7.5, 7.8 (cross-module coordination)
        """
        # Create topic and messages
        topic = Topic(
            id="topic-1",
            title="Test Topic",
            status="active",
            summary="Old summary",
            llm_suggestion="continue",
            end_score=20.0,
            token_count_since_summary=9000,
            pending_summary_job=True
        )
        test_db.add(topic)
        
        msg = Message(
            id="msg-1",
            topic_id="topic-1",
            agent_id="agent_a",
            content="Final message",
            actual_tokens=100
        )
        test_db.add(msg)
        
        job = SummaryJob(
            id="job-1",
            topic_id="topic-1",
            start_message_id=None,
            end_message_id="msg-1",
            status="pending",
            retry_count=0
        )
        test_db.add(job)
        test_db.commit()
        
        # Step 1: Worker processes job with force_end
        with patch('services.summary_service.SummaryService._call_deepseek_api') as mock_llm:
            mock_llm.return_value = {
                "summary": "Conversation concluded",
                "suggestion": "force_end",
                "end_score": 95.0
            }
            
            process_summary_job("job-1", db_session=test_db)
        
        # Step 2: Verify topic is closing_pending
        test_db.refresh(topic)
        assert topic.status == "closing_pending"
        assert topic.llm_suggestion == "force_end"
        
        # Step 3: API returns closing_pending with no hint
        response = test_client.get("/api/topic/active", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closing_pending"
        assert data["llm_hint"] is None  # No hint when closing_pending
        assert data["closing_status"] is not None
        assert data["closing_status"]["closing_requested_by"] == "system"
    
    def test_subsequent_summary_ignores_new_suggestions(
        self,
        test_db: Session
    ):
        """
        Test that subsequent summaries after force_end don't change suggestion.
        
        Validates Requirement 7.8 (persistence across multiple summaries)
        """
        # Create topic in closing_pending (after force_end)
        topic = Topic(
            id="topic-1",
            title="Test Topic",
            status="closing_pending",
            summary="Summary after force_end",
            llm_suggestion="force_end",
            end_score=95.0,
            token_count_since_summary=5000,  # New messages accumulated
            pending_summary_job=True,
            closing_requested_by="system",
            closing_requested_at=datetime.utcnow()
        )
        test_db.add(topic)
        
        msg = Message(
            id="msg-1",
            topic_id="topic-1",
            agent_id="agent_a",
            content="Additional message",
            actual_tokens=100
        )
        test_db.add(msg)
        
        job = SummaryJob(
            id="job-1",
            topic_id="topic-1",
            start_message_id=None,
            end_message_id="msg-1",
            status="pending",
            retry_count=0
        )
        test_db.add(job)
        test_db.commit()
        
        # Process another summary job
        with patch('services.summary_service.SummaryService._call_deepseek_api') as mock_llm:
            mock_llm.return_value = {
                "summary": "Updated summary",
                "suggestion": "continue",  # LLM suggests continue
                "end_score": 30.0
            }
            
            process_summary_job("job-1", db_session=test_db)
        
        # Verify original force_end suggestion preserved
        test_db.refresh(topic)
        assert topic.llm_suggestion == "force_end"  # Original preserved
        assert topic.end_score == 95.0  # Original preserved
        assert topic.status == "closing_pending"  # Status unchanged
        assert topic.summary == "Updated summary"  # Summary updated
