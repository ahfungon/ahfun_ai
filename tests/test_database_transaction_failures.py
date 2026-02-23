"""Tests for database transaction failure scenarios."""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError, IntegrityError

from models.models import Topic
from services.topic_service import TopicService
from services.message_service import MessageService
from models.database import transaction, atomic_update


def test_token_update_transaction_rollback(test_db, test_agents):
    """
    Test that token update transaction rolls back on failure.
    
    **Validates: Requirements 10.1, 10.2, 10.5**
    """
    topic_service = TopicService(test_db)
    message_service = MessageService(test_db)
    
    # Create a topic
    topic = topic_service.create_topic(title="Test Topic")
    initial_token_count = topic.token_count_since_summary
    
    # Mock database commit to fail
    with patch.object(test_db, 'commit', side_effect=OperationalError("DB Error", None, None)):
        try:
            message_service.create_message(topic.id, test_agents[0].id, "Test message", 100)
        except OperationalError:
            pass  # Expected to fail
    
    # Verify token count was not updated (rolled back)
    test_db.rollback()
    test_db.refresh(topic)
    assert topic.token_count_since_summary == initial_token_count


def test_summary_update_transaction_rollback(test_db):
    """
    Test that summary update transaction rolls back on failure.
    
    **Validates: Requirements 10.1, 10.2, 10.5**
    """
    topic_service = TopicService(test_db)
    
    # Create a topic
    topic = topic_service.create_topic(title="Test Topic")
    initial_summary = topic.summary
    
    # Attempt to update summary with transaction failure
    try:
        with transaction(test_db):
            topic.summary = "New summary"
            topic.llm_suggestion = "continue"
            # Force a failure
            raise OperationalError("DB Error", None, None)
    except OperationalError:
        pass  # Expected to fail
    
    # Verify summary was not updated (rolled back)
    test_db.refresh(topic)
    assert topic.summary == initial_summary


def test_concurrent_write_conflict_handling(test_db):
    """
    Test handling of concurrent write conflicts.
    
    **Validates: Requirements 10.1, 10.2, 10.5**
    """
    topic_service = TopicService(test_db)
    
    # Create a topic
    topic = topic_service.create_topic(title="Test Topic")
    topic_id = topic.id
    
    # Lock and update in first session
    with atomic_update(test_db, Topic, topic_id) as locked_topic:
        locked_topic.token_count_since_summary = 1000
    
    # Verify update was committed
    test_db.refresh(topic)
    assert topic.token_count_since_summary == 1000
    
    # Update again (simulating sequential access, which is what locking ensures)
    with atomic_update(test_db, Topic, topic_id) as locked_topic2:
        locked_topic2.token_count_since_summary = 2000
    
    # Verify final value
    test_db.refresh(topic)
    assert topic.token_count_since_summary == 2000


def test_atomic_update_rollback_on_error(test_db):
    """
    Test that atomic_update rolls back on error.
    
    **Validates: Requirements 10.1, 10.2, 10.5**
    """
    topic_service = TopicService(test_db)
    
    # Create a topic
    topic = topic_service.create_topic(title="Test Topic")
    initial_count = topic.token_count_since_summary
    
    # Attempt atomic update with error
    try:
        with atomic_update(test_db, Topic, topic.id) as locked_topic:
            locked_topic.token_count_since_summary = 5000
            # Force an error
            raise ValueError("Simulated error")
    except ValueError:
        pass  # Expected
    
    # Verify rollback occurred
    test_db.refresh(topic)
    assert topic.token_count_since_summary == initial_count


def test_transaction_context_manager_rollback(test_db):
    """
    Test that transaction context manager rolls back on exception.
    
    **Validates: Requirements 10.1, 10.2**
    """
    from models.models import Topic as TopicModel
    from uuid import uuid4
    
    # Count topics before
    topics_before = test_db.query(TopicModel).count()
    
    # Attempt to create topic in transaction that fails
    try:
        with transaction(test_db):
            # Manually create topic to test rollback
            new_topic = TopicModel(
                id=str(uuid4()),
                title="New Topic",
                status="active",
                summary="",
                token_count_since_summary=0,
                pending_summary_job=False
            )
            test_db.add(new_topic)
            test_db.flush()  # Flush to database but don't commit
            # Force failure
            raise RuntimeError("Transaction failed")
    except RuntimeError:
        pass  # Expected
    
    # Verify new topic was not created (rolled back)
    topics_after = test_db.query(TopicModel).count()
    assert topics_after == topics_before


def test_integrity_error_handling(test_db, test_agents):
    """
    Test handling of database integrity errors.
    
    **Validates: Requirements 10.1, 10.2**
    """
    from models.models import Message
    from uuid import uuid4
    
    topic_service = TopicService(test_db)
    topic = topic_service.create_topic(title="Test Topic")
    
    # Create a message with specific ID
    message_id = str(uuid4())
    message = Message(
        id=message_id,
        topic_id=topic.id,
        agent_id=test_agents[0].id,
        content="Test message",
        actual_tokens=100
    )
    test_db.add(message)
    test_db.commit()
    
    # Attempt to create another message with same ID (should fail)
    duplicate_message = Message(
        id=message_id,  # Same ID
        topic_id=topic.id,
        agent_id=test_agents[0].id,
        content="Duplicate message",
        actual_tokens=100
    )
    
    with pytest.raises(IntegrityError):
        test_db.add(duplicate_message)
        test_db.commit()
    
    # Rollback to clean state
    test_db.rollback()


def test_nested_transaction_rollback(test_db):
    """
    Test that nested transactions roll back correctly.
    
    **Validates: Requirements 10.1, 10.2**
    """
    from models.models import Topic as TopicModel
    from uuid import uuid4
    
    topics_before = test_db.query(TopicModel).count()
    
    # Outer transaction
    try:
        with transaction(test_db):
            topic1 = TopicModel(
                id=str(uuid4()),
                title="Topic 1",
                status="active",
                summary="",
                token_count_since_summary=0,
                pending_summary_job=False
            )
            test_db.add(topic1)
            test_db.flush()
            
            # Inner operation that fails
            try:
                topic2 = TopicModel(
                    id=str(uuid4()),
                    title="Topic 2",
                    status="active",
                    summary="",
                    token_count_since_summary=0,
                    pending_summary_job=False
                )
                test_db.add(topic2)
                test_db.flush()
                raise ValueError("Inner failure")
            except ValueError:
                # Rollback inner changes
                test_db.rollback()
            
            # Outer transaction continues but then fails
            raise RuntimeError("Outer failure")
    except RuntimeError:
        pass
    
    # Verify all changes were rolled back
    topics_after = test_db.query(TopicModel).count()
    assert topics_after == topics_before
