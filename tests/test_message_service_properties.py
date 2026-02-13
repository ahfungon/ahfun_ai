"""Property-based tests for MessageService using Hypothesis.

This test suite validates the correctness properties defined in the design document
for the MessageService component of the dual-agent chat platform.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import Topic, Message, SummaryJob
from services.message_service import MessageService
from config.settings import settings as app_settings


# Context manager for test database
@contextmanager
def get_test_db():
    """Create a test database session as a context manager."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


# Hypothesis strategies for generating test data
@st.composite
def topic_id_strategy(draw):
    """Generate a valid topic ID."""
    return f"topic-{draw(st.uuids())}"


@st.composite
def agent_id_strategy(draw):
    """Generate a valid agent ID."""
    return draw(st.sampled_from(["agent_a", "agent_b"]))


@st.composite
def message_content_strategy(draw):
    """Generate valid message content."""
    return draw(st.text(min_size=1, max_size=1000))


@st.composite
def token_count_strategy(draw):
    """Generate valid token count."""
    return draw(st.integers(min_value=1, max_value=1000))


@st.composite
def limit_strategy(draw):
    """Generate valid limit parameter."""
    return draw(st.integers(min_value=1, max_value=100))


# Property 7: Messages belong to specified topic
# **Validates: Requirements 4.1**
@given(
    topic_id=topic_id_strategy(),
    agent_id=agent_id_strategy(),
    content=message_content_strategy(),
    tokens=token_count_strategy()
)
@settings(max_examples=100)
def test_property_7_messages_belong_to_topic(topic_id, agent_id, content, tokens):
    """
    Property 7: Messages belong to specified topic
    
    For any message query request, all returned messages must have topic_id
    equal to the requested topic ID.
    
    **Validates: Requirements 4.1**
    """
    with get_test_db() as test_db:
        # Create topic
        topic = Topic(
            id=topic_id,
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
        
        # Create service and add message
        service = MessageService(test_db)
        service.create_message(topic_id, agent_id, content, tokens)
        
        # Query messages
        messages = service.get_messages(topic_id)
        
        # Verify all messages belong to the topic
        assert len(messages) > 0
        for message in messages:
            assert message.topic_id == topic_id


# Property 8: Limit parameter limits return count
# **Validates: Requirements 4.2**
@given(
    topic_id=topic_id_strategy(),
    num_messages=st.integers(min_value=5, max_value=20),
    limit=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100)
def test_property_8_limit_parameter_limits_count(topic_id, num_messages, limit):
    """
    Property 8: Limit parameter limits return count
    
    For any message query with a limit parameter, the number of returned messages
    should not exceed the limit value (unless total messages are fewer than limit).
    
    **Validates: Requirements 4.2**
    """
    with get_test_db() as test_db:
        # Create topic
        topic = Topic(
            id=topic_id,
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
        
        # Create multiple messages
        service = MessageService(test_db)
        for i in range(num_messages):
            service.create_message(topic_id, "agent_a", f"Message {i}", 10)
        
        # Query with limit
        messages = service.get_messages(topic_id, limit=limit)
        
        # Verify count respects limit
        expected_count = min(num_messages, limit)
        assert len(messages) == expected_count


# Property 9: Messages include required fields
# **Validates: Requirements 4.4**
@given(
    topic_id=topic_id_strategy(),
    agent_id=agent_id_strategy(),
    content=message_content_strategy(),
    tokens=token_count_strategy()
)
@settings(max_examples=100)
def test_property_9_messages_include_required_fields(topic_id, agent_id, content, tokens):
    """
    Property 9: Messages include required fields
    
    For any returned message object, it must include agent_id, content, and created_at
    fields, and these fields must not be empty/null.
    
    **Validates: Requirements 4.4**
    """
    with get_test_db() as test_db:
        # Create topic
        topic = Topic(
            id=topic_id,
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
        
        # Create message
        service = MessageService(test_db)
        message = service.create_message(topic_id, agent_id, content, tokens)
        
        # Verify required fields are present and not empty
        assert message.agent_id is not None
        assert message.agent_id != ""
        assert message.content is not None
        assert message.content != ""
        assert message.created_at is not None


# Property 10: Messages in time order
# **Validates: Requirements 4.5**
@given(
    topic_id=topic_id_strategy(),
    num_messages=st.integers(min_value=2, max_value=10)
)
@settings(max_examples=100)
def test_property_10_messages_in_time_order(topic_id, num_messages):
    """
    Property 10: Messages in time order
    
    For any topic's message list, messages should be sorted by created_at timestamp
    from oldest to newest.
    
    **Validates: Requirements 4.5**
    """
    with get_test_db() as test_db:
        # Create topic
        topic = Topic(
            id=topic_id,
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
        
        # Create multiple messages
        service = MessageService(test_db)
        for i in range(num_messages):
            service.create_message(topic_id, "agent_a", f"Message {i}", 10)
        
        # Query messages
        messages = service.get_messages(topic_id, limit=num_messages)
        
        # Verify time ordering (oldest to newest)
        for i in range(len(messages) - 1):
            assert messages[i].created_at <= messages[i + 1].created_at


# Property 11: Invalid topic ID rejected
# **Validates: Requirements 5.1**
@given(
    invalid_topic_id=topic_id_strategy(),
    agent_id=agent_id_strategy(),
    content=message_content_strategy(),
    tokens=token_count_strategy()
)
@settings(max_examples=100)
def test_property_11_invalid_topic_id_rejected(invalid_topic_id, agent_id, content, tokens):
    """
    Property 11: Invalid topic ID rejected
    
    For any message submission with a non-existent topic_id, the system should
    raise a ValueError.
    
    **Validates: Requirements 5.1**
    """
    with get_test_db() as test_db:
        # Do NOT create the topic
        service = MessageService(test_db)
        
        # Attempt to create message with invalid topic_id
        with pytest.raises(ValueError, match="Topic .* not found"):
            service.create_message(invalid_topic_id, agent_id, content, tokens)


# Property 12: Message ID uniqueness
# **Validates: Requirements 5.2**
@given(
    topic_id=topic_id_strategy(),
    num_messages=st.integers(min_value=2, max_value=20)
)
@settings(max_examples=100)
def test_property_12_message_id_uniqueness(topic_id, num_messages):
    """
    Property 12: Message ID uniqueness
    
    For any two different messages, their IDs must be different.
    
    **Validates: Requirements 5.2**
    """
    with get_test_db() as test_db:
        # Create topic
        topic = Topic(
            id=topic_id,
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
        
        # Create multiple messages
        service = MessageService(test_db)
        message_ids = set()
        
        for i in range(num_messages):
            message = service.create_message(topic_id, "agent_a", f"Message {i}", 10)
            message_ids.add(message.id)
        
        # Verify all IDs are unique
        assert len(message_ids) == num_messages


# Property 13: Message submission increases token count
# **Validates: Requirements 5.3**
@given(
    topic_id=topic_id_strategy(),
    agent_id=agent_id_strategy(),
    content=message_content_strategy(),
    tokens=token_count_strategy()
)
@settings(max_examples=100)
def test_property_13_message_increases_token_count(topic_id, agent_id, content, tokens):
    """
    Property 13: Message submission increases token count
    
    For any topic, submitting a new message should increase the topic's
    token_count_since_summary by the message's actual token count.
    
    **Validates: Requirements 5.3**
    """
    with get_test_db() as test_db:
        # Create topic
        topic = Topic(
            id=topic_id,
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
        
        # Record initial token count
        initial_count = topic.token_count_since_summary
        
        # Create message
        service = MessageService(test_db)
        service.create_message(topic_id, agent_id, content, tokens)
        
        # Refresh topic and verify token count increased
        test_db.refresh(topic)
        assert topic.token_count_since_summary == initial_count + tokens


# Property 14: Message submission response completeness
# **Validates: Requirements 5.4**
@given(
    topic_id=topic_id_strategy(),
    agent_id=agent_id_strategy(),
    content=message_content_strategy(),
    tokens=token_count_strategy()
)
@settings(max_examples=100)
def test_property_14_message_response_completeness(topic_id, agent_id, content, tokens):
    """
    Property 14: Message submission response completeness
    
    For any successful message submission, the response should include the
    new message ID and the updated token count.
    
    **Validates: Requirements 5.4**
    """
    with get_test_db() as test_db:
        # Create topic
        topic = Topic(
            id=topic_id,
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
        
        # Create message
        service = MessageService(test_db)
        message = service.create_message(topic_id, agent_id, content, tokens)
        
        # Verify response includes message ID
        assert message.id is not None
        assert message.id != ""
        
        # Verify we can get updated token count
        test_db.refresh(topic)
        assert topic.token_count_since_summary >= tokens


# Property 15: Threshold triggers summary job
# **Validates: Requirements 6.1**
@given(
    topic_id=topic_id_strategy(),
    initial_tokens=st.integers(min_value=0, max_value=100),
    message_tokens=st.integers(min_value=1, max_value=1000)
)
@settings(max_examples=100)
def test_property_15_threshold_triggers_summary_job(topic_id, initial_tokens, message_tokens):
    """
    Property 15: Threshold triggers summary job
    
    For any topic, when token_count_since_summary reaches the configured threshold
    and pending_summary_job is false, the system should create a SummaryJob and
    set pending_summary_job to true.
    
    **Validates: Requirements 6.1**
    """
    with get_test_db() as test_db:
        # Calculate if this message will trigger threshold
        threshold = app_settings.summary_threshold
        will_trigger = (initial_tokens + message_tokens >= threshold)
        
        # Create topic with initial token count
        topic = Topic(
            id=topic_id,
            title="Test Topic",
            status="active",
            summary="",
            token_count_since_summary=initial_tokens,
            pending_summary_job=False,
            agent_a_wants_close=False,
            agent_b_wants_close=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(topic)
        test_db.commit()
        
        # Create message
        service = MessageService(test_db)
        message = service.create_message(topic_id, "agent_a", "Test message", message_tokens)
        
        # Refresh topic
        test_db.refresh(topic)
        
        if will_trigger:
            # Verify summary job was created
            assert topic.pending_summary_job is True
            
            jobs = test_db.query(SummaryJob).filter(
                SummaryJob.topic_id == topic_id,
                SummaryJob.status == "pending"
            ).all()
            
            assert len(jobs) == 1
            assert jobs[0].end_message_id == message.id
        else:
            # Verify no summary job was created
            assert topic.pending_summary_job is False


# Property 15a: Prevent concurrent duplicate tasks
# **Validates: Requirements 6.1, 12.3**
@given(
    topic_id=topic_id_strategy(),
    message_tokens=st.integers(min_value=100, max_value=1000)
)
@settings(max_examples=100)
def test_property_15a_prevent_concurrent_duplicate_tasks(topic_id, message_tokens):
    """
    Property 15a: Prevent concurrent duplicate tasks
    
    For any topic with pending_summary_job set to true, even if token count
    reaches the threshold, no new SummaryJob should be created.
    
    **Validates: Requirements 6.1, 12.3**
    """
    with get_test_db() as test_db:
        threshold = app_settings.summary_threshold
        
        # Create topic with tokens above threshold and pending job flag set
        topic = Topic(
            id=topic_id,
            title="Test Topic",
            status="active",
            summary="",
            token_count_since_summary=threshold + 100,
            pending_summary_job=True,  # Already has pending job
            agent_a_wants_close=False,
            agent_b_wants_close=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(topic)
        test_db.commit()
        
        # Create message (should not trigger new job)
        service = MessageService(test_db)
        service.create_message(topic_id, "agent_a", "Test message", message_tokens)
        
        # Verify no new summary job was created
        jobs = test_db.query(SummaryJob).filter(
            SummaryJob.topic_id == topic_id
        ).all()
        
        assert len(jobs) == 0  # No jobs should be created
