"""Unit tests for closing timeout check periodic task."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models.models import Topic, AuditLog
from workers.tasks import check_closing_timeouts
from services.topic_service import TopicService
from services.audit_log_service import AuditLogService
from config.settings import settings


def test_check_closing_timeouts_no_topics(test_db: Session):
    """Test closing timeout check when no topics exist."""
    result = check_closing_timeouts(db_session=test_db)
    
    assert result["closed_count"] == 0
    assert result["closed_topic_ids"] == []


def test_check_closing_timeouts_no_closing_pending(test_db: Session):
    """Test closing timeout check when no topics are in closing_pending state."""
    # Create active topic
    topic_service = TopicService(test_db)
    topic = topic_service.create_topic(title="Active Topic")
    
    result = check_closing_timeouts(db_session=test_db)
    
    assert result["closed_count"] == 0
    assert result["closed_topic_ids"] == []
    
    # Verify topic is still active
    test_db.refresh(topic)
    assert topic.status == "active"


def test_check_closing_timeouts_not_timed_out(test_db: Session):
    """Test closing timeout check when closing_pending topic has not timed out."""
    # Create topic in closing_pending state
    topic_service = TopicService(test_db)
    topic = topic_service.create_topic(title="Pending Topic")
    
    # Set to closing_pending with recent timestamp
    topic.status = "closing_pending"
    topic.closing_requested_by = "agent_a"
    topic.closing_requested_at = datetime.utcnow() - timedelta(seconds=60)  # 1 minute ago
    test_db.commit()
    
    result = check_closing_timeouts(db_session=test_db)
    
    assert result["closed_count"] == 0
    assert result["closed_topic_ids"] == []
    
    # Verify topic is still closing_pending
    test_db.refresh(topic)
    assert topic.status == "closing_pending"


def test_check_closing_timeouts_single_timed_out(test_db: Session):
    """Test closing timeout check closes a single timed-out topic."""
    # Create topic in closing_pending state
    topic_service = TopicService(test_db)
    topic = topic_service.create_topic(title="Timed Out Topic")
    
    # Set to closing_pending with old timestamp (beyond timeout)
    timeout_seconds = settings.closing_timeout
    topic.status = "closing_pending"
    topic.closing_requested_by = "agent_a"
    topic.closing_requested_at = datetime.utcnow() - timedelta(seconds=timeout_seconds + 10)
    test_db.commit()
    
    result = check_closing_timeouts(db_session=test_db)
    
    assert result["closed_count"] == 1
    assert topic.id in result["closed_topic_ids"]
    
    # Verify topic is now closed
    test_db.refresh(topic)
    assert topic.status == "closed"


def test_check_closing_timeouts_multiple_timed_out(test_db: Session):
    """Test closing timeout check closes multiple timed-out topics."""
    # Create multiple topics in closing_pending state
    topic_service = TopicService(test_db)
    timeout_seconds = settings.closing_timeout
    
    topic1 = topic_service.create_topic(title="Timed Out Topic 1")
    topic1.status = "closing_pending"
    topic1.closing_requested_by = "agent_a"
    topic1.closing_requested_at = datetime.utcnow() - timedelta(seconds=timeout_seconds + 10)
    
    topic2 = topic_service.create_topic(title="Timed Out Topic 2")
    topic2.status = "closing_pending"
    topic2.closing_requested_by = "agent_b"
    topic2.closing_requested_at = datetime.utcnow() - timedelta(seconds=timeout_seconds + 20)
    
    # Create one that hasn't timed out
    topic3 = topic_service.create_topic(title="Not Timed Out Topic")
    topic3.status = "closing_pending"
    topic3.closing_requested_by = "agent_a"
    topic3.closing_requested_at = datetime.utcnow() - timedelta(seconds=60)
    
    test_db.commit()
    
    result = check_closing_timeouts(db_session=test_db)
    
    assert result["closed_count"] == 2
    assert topic1.id in result["closed_topic_ids"]
    assert topic2.id in result["closed_topic_ids"]
    assert topic3.id not in result["closed_topic_ids"]
    
    # Verify topics are closed
    test_db.refresh(topic1)
    test_db.refresh(topic2)
    test_db.refresh(topic3)
    assert topic1.status == "closed"
    assert topic2.status == "closed"
    assert topic3.status == "closing_pending"


def test_check_closing_timeouts_creates_audit_log(test_db: Session):
    """Test closing timeout check creates audit log for closed topics."""
    # Create topic in closing_pending state
    topic_service = TopicService(test_db)
    topic = topic_service.create_topic(title="Timed Out Topic")
    
    # Set to closing_pending with old timestamp
    timeout_seconds = settings.closing_timeout
    topic.status = "closing_pending"
    topic.closing_requested_by = "agent_a"
    topic.closing_requested_at = datetime.utcnow() - timedelta(seconds=timeout_seconds + 10)
    test_db.commit()
    
    result = check_closing_timeouts(db_session=test_db)
    
    assert result["closed_count"] == 1
    
    # Verify audit log was created
    audit_logs = test_db.query(AuditLog).filter(
        AuditLog.topic_id == topic.id,
        AuditLog.operation_type == AuditLogService.OPERATION_STATUS_CHANGED
    ).all()
    
    assert len(audit_logs) == 1
    audit_log = audit_logs[0]
    assert audit_log.topic_id == topic.id
    assert audit_log.agent_id is None  # System action
    assert "closing_timeout" in audit_log.details


def test_check_closing_timeouts_at_exact_timeout(test_db: Session):
    """Test closing timeout check at exact timeout boundary."""
    # Create topic in closing_pending state
    topic_service = TopicService(test_db)
    topic = topic_service.create_topic(title="Exact Timeout Topic")
    
    # Set to closing_pending at exact timeout threshold
    timeout_seconds = settings.closing_timeout
    topic.status = "closing_pending"
    topic.closing_requested_by = "agent_a"
    topic.closing_requested_at = datetime.utcnow() - timedelta(seconds=timeout_seconds)
    test_db.commit()
    
    result = check_closing_timeouts(db_session=test_db)
    
    # Should be closed (>= timeout)
    assert result["closed_count"] == 1
    assert topic.id in result["closed_topic_ids"]
    
    # Verify topic is closed
    test_db.refresh(topic)
    assert topic.status == "closed"


def test_check_closing_timeouts_updates_updated_at(test_db: Session):
    """Test closing timeout check updates the updated_at timestamp."""
    # Create topic in closing_pending state
    topic_service = TopicService(test_db)
    topic = topic_service.create_topic(title="Timed Out Topic")
    
    # Set to closing_pending with old timestamp
    timeout_seconds = settings.closing_timeout
    topic.status = "closing_pending"
    topic.closing_requested_by = "agent_a"
    topic.closing_requested_at = datetime.utcnow() - timedelta(seconds=timeout_seconds + 10)
    original_updated_at = topic.updated_at
    test_db.commit()
    
    # Wait a moment to ensure timestamp difference
    import time
    time.sleep(0.1)
    
    result = check_closing_timeouts(db_session=test_db)
    
    assert result["closed_count"] == 1
    
    # Verify updated_at was changed
    test_db.refresh(topic)
    assert topic.updated_at > original_updated_at


def test_check_closing_timeouts_preserves_other_fields(test_db: Session):
    """Test closing timeout check preserves other topic fields."""
    # Create topic in closing_pending state with various fields set
    topic_service = TopicService(test_db)
    topic = topic_service.create_topic(title="Timed Out Topic")
    
    # Set various fields
    timeout_seconds = settings.closing_timeout
    topic.status = "closing_pending"
    topic.closing_requested_by = "agent_a"
    topic.closing_requested_at = datetime.utcnow() - timedelta(seconds=timeout_seconds + 10)
    topic.summary = "Test summary"
    topic.llm_suggestion = "suggest_end"
    topic.end_score = 75.5
    topic.token_count_since_summary = 1000
    topic.agent_a_wants_close = True
    test_db.commit()
    
    result = check_closing_timeouts(db_session=test_db)
    
    assert result["closed_count"] == 1
    
    # Verify other fields are preserved
    test_db.refresh(topic)
    assert topic.status == "closed"
    assert topic.closing_requested_by == "agent_a"
    assert topic.summary == "Test summary"
    assert topic.llm_suggestion == "suggest_end"
    assert topic.end_score == 75.5
    assert topic.token_count_since_summary == 1000
    assert topic.agent_a_wants_close is True


def test_check_closing_timeouts_mixed_states(test_db: Session):
    """Test closing timeout check with topics in various states."""
    topic_service = TopicService(test_db)
    timeout_seconds = settings.closing_timeout
    
    # Create topics in different states
    # 1. Active topic
    active_topic = topic_service.create_topic(title="Active Topic")
    
    # 2. Closed topic
    closed_topic = topic_service.create_topic(title="Closed Topic")
    closed_topic.status = "closed"
    
    # 3. Closing pending but not timed out
    pending_not_timed = topic_service.create_topic(title="Pending Not Timed")
    pending_not_timed.status = "closing_pending"
    pending_not_timed.closing_requested_by = "agent_a"
    pending_not_timed.closing_requested_at = datetime.utcnow() - timedelta(seconds=60)
    
    # 4. Closing pending and timed out
    pending_timed = topic_service.create_topic(title="Pending Timed")
    pending_timed.status = "closing_pending"
    pending_timed.closing_requested_by = "agent_b"
    pending_timed.closing_requested_at = datetime.utcnow() - timedelta(seconds=timeout_seconds + 10)
    
    test_db.commit()
    
    result = check_closing_timeouts(db_session=test_db)
    
    # Only the timed out topic should be closed
    assert result["closed_count"] == 1
    assert pending_timed.id in result["closed_topic_ids"]
    
    # Verify states
    test_db.refresh(active_topic)
    test_db.refresh(closed_topic)
    test_db.refresh(pending_not_timed)
    test_db.refresh(pending_timed)
    
    assert active_topic.status == "active"
    assert closed_topic.status == "closed"
    assert pending_not_timed.status == "closing_pending"
    assert pending_timed.status == "closed"


def test_check_closing_timeouts_audit_log_details(test_db: Session):
    """Test closing timeout check creates audit log with correct details."""
    topic_service = TopicService(test_db)
    topic = topic_service.create_topic(title="Timed Out Topic")
    
    timeout_seconds = settings.closing_timeout
    topic.status = "closing_pending"
    topic.closing_requested_by = "agent_a"
    requested_at = datetime.utcnow() - timedelta(seconds=timeout_seconds + 10)
    topic.closing_requested_at = requested_at
    test_db.commit()
    
    result = check_closing_timeouts(db_session=test_db)
    
    assert result["closed_count"] == 1
    
    # Verify audit log details
    audit_logs = test_db.query(AuditLog).filter(
        AuditLog.topic_id == topic.id,
        AuditLog.operation_type == AuditLogService.OPERATION_STATUS_CHANGED
    ).all()
    
    assert len(audit_logs) == 1
    audit_log = audit_logs[0]
    
    # Parse details JSON
    import json
    details = json.loads(audit_log.details)
    
    assert details["reason"] == "closing_timeout"
    assert details["old_status"] == "closing_pending"
    assert details["new_status"] == "closed"
    assert details["timeout_seconds"] == timeout_seconds


def test_check_closing_timeouts_no_closing_requested_at(test_db: Session):
    """Test closing timeout check handles topics with missing closing_requested_at."""
    topic_service = TopicService(test_db)
    topic = topic_service.create_topic(title="Invalid Pending Topic")
    
    # Set to closing_pending but without closing_requested_at (invalid state)
    topic.status = "closing_pending"
    topic.closing_requested_by = "agent_a"
    topic.closing_requested_at = None  # Missing timestamp
    test_db.commit()
    
    # Should not crash, should skip this topic
    result = check_closing_timeouts(db_session=test_db)
    
    assert result["closed_count"] == 0
    assert result["closed_topic_ids"] == []
    
    # Topic should remain in closing_pending state
    test_db.refresh(topic)
    assert topic.status == "closing_pending"


def test_check_closing_timeouts_idempotent(test_db: Session):
    """Test closing timeout check is idempotent (can be run multiple times safely)."""
    topic_service = TopicService(test_db)
    topic = topic_service.create_topic(title="Timed Out Topic")
    
    timeout_seconds = settings.closing_timeout
    topic.status = "closing_pending"
    topic.closing_requested_by = "agent_a"
    topic.closing_requested_at = datetime.utcnow() - timedelta(seconds=timeout_seconds + 10)
    test_db.commit()
    
    # Run timeout check first time
    result1 = check_closing_timeouts(db_session=test_db)
    assert result1["closed_count"] == 1
    
    # Run timeout check second time
    result2 = check_closing_timeouts(db_session=test_db)
    assert result2["closed_count"] == 0  # Already closed
    
    # Verify topic is still closed
    test_db.refresh(topic)
    assert topic.status == "closed"
    
    # Verify only one audit log was created
    audit_logs = test_db.query(AuditLog).filter(
        AuditLog.topic_id == topic.id,
        AuditLog.operation_type == AuditLogService.OPERATION_STATUS_CHANGED
    ).all()
    assert len(audit_logs) == 1


def test_check_closing_timeouts_different_agents(test_db: Session):
    """Test closing timeout check works for different requesting agents."""
    topic_service = TopicService(test_db)
    timeout_seconds = settings.closing_timeout
    
    # Create topics requested by different agents
    topic_a = topic_service.create_topic(title="Topic A")
    topic_a.status = "closing_pending"
    topic_a.closing_requested_by = "agent_a"
    topic_a.closing_requested_at = datetime.utcnow() - timedelta(seconds=timeout_seconds + 10)
    
    topic_b = topic_service.create_topic(title="Topic B")
    topic_b.status = "closing_pending"
    topic_b.closing_requested_by = "agent_b"
    topic_b.closing_requested_at = datetime.utcnow() - timedelta(seconds=timeout_seconds + 20)
    
    test_db.commit()
    
    result = check_closing_timeouts(db_session=test_db)
    
    assert result["closed_count"] == 2
    assert topic_a.id in result["closed_topic_ids"]
    assert topic_b.id in result["closed_topic_ids"]
    
    # Verify both are closed
    test_db.refresh(topic_a)
    test_db.refresh(topic_b)
    assert topic_a.status == "closed"
    assert topic_b.status == "closed"
    
    # Verify audit logs were created for both topics
    audit_log_a = test_db.query(AuditLog).filter(
        AuditLog.topic_id == topic_a.id,
        AuditLog.operation_type == AuditLogService.OPERATION_STATUS_CHANGED
    ).first()
    
    audit_log_b = test_db.query(AuditLog).filter(
        AuditLog.topic_id == topic_b.id,
        AuditLog.operation_type == AuditLogService.OPERATION_STATUS_CHANGED
    ).first()
    
    assert audit_log_a is not None
    assert audit_log_b is not None
    
    # Verify audit log details
    import json
    details_a = json.loads(audit_log_a.details)
    details_b = json.loads(audit_log_b.details)
    
    assert details_a["reason"] == "closing_timeout"
    assert details_b["reason"] == "closing_timeout"
