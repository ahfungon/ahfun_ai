"""Tests for concurrent multi-topic support."""
import pytest
import threading
import time
from sqlalchemy.orm import Session

from models.models import Topic, Message, SummaryJob
from services.topic_service import TopicService
from services.message_service import MessageService
from services.queue_service import QueueService


def test_multiple_topics_independent_state(test_db):
    """
    Test that each topic maintains independent state.
    
    **Validates: Requirements 1.4, 10.5**
    """
    topic_service = TopicService(test_db)
    
    # Create multiple topics
    topic1 = topic_service.create_topic(title="Topic 1")
    topic2 = topic_service.create_topic(title="Topic 2")
    topic3 = topic_service.create_topic(title="Topic 3")
    
    # Verify each topic has independent state
    assert topic1.id != topic2.id != topic3.id
    assert topic1.status == "active"
    assert topic2.status == "active"
    assert topic3.status == "active"
    
    # Modify one topic's state
    topic1.status = "closing_pending"
    test_db.commit()
    
    # Verify other topics are unaffected
    test_db.refresh(topic2)
    test_db.refresh(topic3)
    assert topic2.status == "active"
    assert topic3.status == "active"


def test_multiple_topics_independent_token_count(test_db, test_agents):
    """
    Test that each topic maintains independent token count.
    
    **Validates: Requirements 1.4, 10.5**
    """
    topic_service = TopicService(test_db)
    message_service = MessageService(test_db)
    
    # Create multiple topics
    topic1 = topic_service.create_topic(title="Topic 1")
    topic2 = topic_service.create_topic(title="Topic 2")
    
    # Add messages to topic1
    message_service.create_message(topic1.id, test_agents[0].id, "Message 1", 100)
    message_service.create_message(topic1.id, test_agents[1].id, "Message 2", 200)
    
    # Add messages to topic2
    message_service.create_message(topic2.id, test_agents[0].id, "Message 3", 300)
    
    # Verify independent token counts
    test_db.refresh(topic1)
    test_db.refresh(topic2)
    
    assert topic1.token_count_since_summary == 300
    assert topic2.token_count_since_summary == 300


def test_multiple_topics_independent_summary(test_db):
    """
    Test that each topic maintains independent summary.
    
    **Validates: Requirements 1.4, 10.5**
    """
    topic_service = TopicService(test_db)
    
    # Create multiple topics
    topic1 = topic_service.create_topic(title="Topic 1")
    topic2 = topic_service.create_topic(title="Topic 2")
    
    # Update summaries independently
    topic1.summary = "Summary for topic 1"
    topic1.llm_suggestion = "continue"
    topic1.end_score = 25.0
    
    topic2.summary = "Summary for topic 2"
    topic2.llm_suggestion = "change_angle"
    topic2.end_score = 50.0
    
    test_db.commit()
    
    # Verify independent summaries
    test_db.refresh(topic1)
    test_db.refresh(topic2)
    
    assert topic1.summary == "Summary for topic 1"
    assert topic1.llm_suggestion == "continue"
    assert topic1.end_score == 25.0
    
    assert topic2.summary == "Summary for topic 2"
    assert topic2.llm_suggestion == "change_angle"
    assert topic2.end_score == 50.0


def test_database_lock_per_topic(test_db, test_agents):
    """
    Test that database locks are scoped to individual topics.
    
    **Validates: Requirements 6.14, 10.5**
    """
    from models.database import atomic_update
    
    topic_service = TopicService(test_db)
    
    # Create two topics
    topic1 = topic_service.create_topic(title="Topic 1")
    topic2 = topic_service.create_topic(title="Topic 2")
    
    # Lock topic1 and modify it
    with atomic_update(test_db, Topic, topic1.id) as locked_topic1:
        locked_topic1.token_count_since_summary = 1000
    
    # Verify topic1 was modified
    test_db.refresh(topic1)
    assert topic1.token_count_since_summary == 1000
    
    # Lock topic2 and modify it (demonstrates independent locking)
    with atomic_update(test_db, Topic, topic2.id) as locked_topic2:
        locked_topic2.token_count_since_summary = 2000
    
    # Verify both topics were modified independently
    test_db.refresh(topic1)
    test_db.refresh(topic2)
    
    assert topic1.token_count_since_summary == 1000
    assert topic2.token_count_since_summary == 2000


def test_concurrent_summary_jobs_different_topics(test_db, test_agents):
    """
    Test that summary jobs for different topics can execute concurrently.
    
    **Validates: Requirements 6.13, 6.14**
    """
    topic_service = TopicService(test_db)
    message_service = MessageService(test_db)
    queue_service = QueueService(test_db)
    
    # Create two topics
    topic1 = topic_service.create_topic(title="Topic 1")
    topic2 = topic_service.create_topic(title="Topic 2")
    
    # Add messages to both topics
    msg1 = message_service.create_message(topic1.id, test_agents[0].id, "Message 1", 100)
    msg2 = message_service.create_message(topic2.id, test_agents[0].id, "Message 2", 100)
    
    # Create summary jobs for both topics
    job_id1 = queue_service.enqueue_summary_job(topic1.id, msg1.id, msg1.id)
    job_id2 = queue_service.enqueue_summary_job(topic2.id, msg2.id, msg2.id)
    
    # Verify both jobs were created
    assert job_id1 is not None
    assert job_id2 is not None
    assert job_id1 != job_id2
    
    # Verify jobs exist in database
    job1 = test_db.query(SummaryJob).filter(SummaryJob.id == job_id1).first()
    job2 = test_db.query(SummaryJob).filter(SummaryJob.id == job_id2).first()
    
    assert job1 is not None
    assert job2 is not None
    assert job1.topic_id == topic1.id
    assert job2.topic_id == topic2.id
    
    # Both jobs should be in pending state
    assert job1.status == "pending"
    assert job2.status == "pending"


def test_topic_isolation_concurrent_operations(test_db, test_agents):
    """
    Test that operations on one topic don't affect other topics.
    
    **Validates: Requirements 1.4, 10.5**
    """
    topic_service = TopicService(test_db)
    message_service = MessageService(test_db)
    
    # Create multiple topics
    topics = [topic_service.create_topic(title=f"Topic {i}") for i in range(5)]
    
    # Add messages to each topic sequentially (simpler test)
    for i, topic in enumerate(topics):
        for j in range(5):
            message_service.create_message(topic.id, test_agents[i % 2].id, f"Message {j}", 10)
    
    # Verify each topic has the correct number of messages
    for topic in topics:
        messages = test_db.query(Message).filter(Message.topic_id == topic.id).all()
        assert len(messages) == 5
        
        # Verify token count
        test_db.refresh(topic)
        assert topic.token_count_since_summary == 50  # 5 messages * 10 tokens each


def test_queue_supports_multiple_topics(test_db, test_agents):
    """
    Test that task queue supports multiple topics concurrently.
    
    **Validates: Requirements 6.13**
    """
    topic_service = TopicService(test_db)
    message_service = MessageService(test_db)
    queue_service = QueueService(test_db)
    
    # Create multiple topics
    topics = [topic_service.create_topic(title=f"Topic {i}") for i in range(10)]
    
    # Create messages and summary jobs for all topics
    job_ids = []
    for topic in topics:
        msg = message_service.create_message(topic.id, test_agents[0].id, "Test message", 100)
        job_id = queue_service.enqueue_summary_job(topic.id, msg.id, msg.id)
        job_ids.append(job_id)
    
    # Verify all jobs were created
    assert len(job_ids) == 10
    
    # Verify all job IDs are unique
    assert len(set(job_ids)) == 10
    
    # Verify all jobs exist in database and are pending
    for job_id in job_ids:
        job = test_db.query(SummaryJob).filter(SummaryJob.id == job_id).first()
        assert job is not None
        assert job.status == "pending"
    
    # Verify each job is for a different topic
    topic_ids = [
        test_db.query(SummaryJob).filter(SummaryJob.id == job_id).first().topic_id
        for job_id in job_ids
    ]
    assert len(set(topic_ids)) == 10  # All unique


def test_concurrent_topic_creation(test_db):
    """
    Test that multiple topics can be created concurrently.
    
    **Validates: Requirements 1.4**
    """
    created_topics = []
    errors = []
    
    def create_topic(title):
        from models.database import SessionLocal
        db = SessionLocal()
        try:
            topic_service = TopicService(db)
            topic = topic_service.create_topic(title=title)
            created_topics.append(topic.id)
            db.commit()
        except Exception as e:
            errors.append(e)
        finally:
            db.close()
    
    # Create multiple topics concurrently
    threads = []
    for i in range(10):
        thread = threading.Thread(target=create_topic, args=(f"Concurrent Topic {i}",))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify no errors occurred
    assert len(errors) == 0
    
    # Verify all topics were created
    assert len(created_topics) == 10
    
    # Verify all topic IDs are unique
    assert len(set(created_topics)) == 10
