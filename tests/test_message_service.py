"""Tests for MessageService."""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import Topic, Message, SummaryJob
from services.message_service import MessageService
from config.settings import settings


@pytest.fixture
def test_db():
    """Create a test database session using PostgreSQL."""
    from sqlalchemy import text
    
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    
    # Clean up
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE messages, summary_history, summary_jobs, audit_logs, topics, agents RESTART IDENTITY CASCADE"))
        conn.commit()


@pytest.fixture
def sample_topic(test_db):
    """Create a sample topic for testing."""
    topic = Topic(
        id="test-topic-1",
        title="Test Topic",
        status="active",
        summary="",
        token_count_since_summary=0,
        pending_summary_job=False,
        agent_a_wants_close=False,
        agent_b_wants_close=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_db.add(topic)
    test_db.commit()
    return topic


def test_create_message_basic(test_db, sample_topic):
    """Test basic message creation."""
    service = MessageService(test_db)
    
    message = service.create_message(
        topic_id=sample_topic.id,
        agent_id="agent_a",
        content="Hello, this is a test message",
        actual_tokens=10
    )
    
    assert message.id is not None
    assert message.topic_id == sample_topic.id
    assert message.agent_id == "agent_a"
    assert message.content == "Hello, this is a test message"
    assert message.actual_tokens == 10
    assert message.created_at is not None


def test_create_message_increments_token_count(test_db, sample_topic):
    """Test that creating a message increments the topic's token count."""
    service = MessageService(test_db)
    
    initial_count = sample_topic.token_count_since_summary
    
    service.create_message(
        topic_id=sample_topic.id,
        agent_id="agent_a",
        content="Test message",
        actual_tokens=50
    )
    
    # Refresh topic from database
    test_db.refresh(sample_topic)
    
    assert sample_topic.token_count_since_summary == initial_count + 50


def test_create_message_triggers_summary_job_at_threshold(test_db, sample_topic):
    """Test that reaching threshold triggers a summary job."""
    service = MessageService(test_db)
    
    # Set token count close to threshold
    sample_topic.token_count_since_summary = settings.summary_threshold - 10
    test_db.commit()
    
    # Create message that exceeds threshold
    message = service.create_message(
        topic_id=sample_topic.id,
        agent_id="agent_a",
        content="This message will trigger summary",
        actual_tokens=20
    )
    
    # Refresh topic
    test_db.refresh(sample_topic)
    
    # Check that pending_summary_job flag is set
    assert sample_topic.pending_summary_job is True
    
    # Check that a summary job was created
    jobs = test_db.query(SummaryJob).filter(
        SummaryJob.topic_id == sample_topic.id,
        SummaryJob.status == "pending"
    ).all()
    
    assert len(jobs) == 1
    assert jobs[0].end_message_id == message.id


def test_create_message_does_not_trigger_duplicate_summary_job(test_db, sample_topic):
    """Test that pending_summary_job prevents duplicate job creation."""
    service = MessageService(test_db)
    
    # Set token count above threshold and mark as pending
    sample_topic.token_count_since_summary = settings.summary_threshold + 100
    sample_topic.pending_summary_job = True
    test_db.commit()
    
    # Create another message
    service.create_message(
        topic_id=sample_topic.id,
        agent_id="agent_a",
        content="Another message",
        actual_tokens=50
    )
    
    # Check that no new summary job was created
    jobs = test_db.query(SummaryJob).filter(
        SummaryJob.topic_id == sample_topic.id
    ).all()
    
    assert len(jobs) == 0


def test_create_message_rejects_closed_topic(test_db, sample_topic):
    """Test that messages cannot be posted to closed topics."""
    service = MessageService(test_db)
    
    # Close the topic
    sample_topic.status = "closed"
    test_db.commit()
    
    # Attempt to create message
    with pytest.raises(ValueError, match="Cannot post message to closed topic"):
        service.create_message(
            topic_id=sample_topic.id,
            agent_id="agent_a",
            content="This should fail",
            actual_tokens=10
        )


def test_create_message_rejects_invalid_topic(test_db):
    """Test that messages cannot be posted to non-existent topics."""
    service = MessageService(test_db)
    
    with pytest.raises(ValueError, match="Topic .* not found"):
        service.create_message(
            topic_id="non-existent-topic",
            agent_id="agent_a",
            content="This should fail",
            actual_tokens=10
        )


def test_get_messages_returns_correct_order(test_db, sample_topic):
    """Test that get_messages returns messages in correct order (oldest to newest)."""
    service = MessageService(test_db)
    
    # Create multiple messages
    msg1 = service.create_message(sample_topic.id, "agent_a", "First message", 10)
    msg2 = service.create_message(sample_topic.id, "agent_b", "Second message", 10)
    msg3 = service.create_message(sample_topic.id, "agent_a", "Third message", 10)
    
    # Get messages
    messages = service.get_messages(sample_topic.id, limit=10)
    
    assert len(messages) == 3
    assert messages[0].id == msg1.id
    assert messages[1].id == msg2.id
    assert messages[2].id == msg3.id


def test_get_messages_respects_limit(test_db, sample_topic):
    """Test that get_messages respects the limit parameter."""
    service = MessageService(test_db)
    
    # Create 5 messages
    for i in range(5):
        service.create_message(sample_topic.id, "agent_a", f"Message {i}", 10)
    
    # Get only 3 messages
    messages = service.get_messages(sample_topic.id, limit=3)
    
    assert len(messages) == 3


def test_get_messages_returns_empty_for_no_messages(test_db, sample_topic):
    """Test that get_messages returns empty list when no messages exist."""
    service = MessageService(test_db)
    
    messages = service.get_messages(sample_topic.id, limit=10)
    
    assert len(messages) == 0


def test_increment_token_count(test_db, sample_topic):
    """Test token count increment."""
    service = MessageService(test_db)
    
    initial_count = sample_topic.token_count_since_summary
    
    new_count = service.increment_token_count(sample_topic.id, 100)
    
    assert new_count == initial_count + 100
    
    # Commit the transaction (normally done by create_message)
    test_db.commit()
    
    # Verify in database
    test_db.refresh(sample_topic)
    assert sample_topic.token_count_since_summary == initial_count + 100


def test_increment_token_count_invalid_topic(test_db):
    """Test that increment_token_count raises error for invalid topic."""
    service = MessageService(test_db)
    
    with pytest.raises(ValueError, match="Topic .* not found"):
        service.increment_token_count("non-existent-topic", 100)


def test_message_includes_actual_tokens(test_db, sample_topic):
    """Test that messages store actual token count from LLM."""
    service = MessageService(test_db)
    
    actual_tokens = 42
    message = service.create_message(
        topic_id=sample_topic.id,
        agent_id="agent_a",
        content="Test message",
        actual_tokens=actual_tokens
    )
    
    assert message.actual_tokens == actual_tokens
    
    # Verify in database
    db_message = test_db.query(Message).filter(Message.id == message.id).first()
    assert db_message.actual_tokens == actual_tokens
