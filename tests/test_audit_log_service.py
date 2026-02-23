"""Tests for AuditLogService."""
import json
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from services.audit_log_service import AuditLogService
from models.models import AuditLog


class TestAuditLogService:
    """Test suite for AuditLogService."""
    
    def test_record_topic_created(self, test_db: Session):
        """Test recording a topic_created operation."""
        service = AuditLogService(test_db)
        
        log = service.record(
            operation_type=AuditLogService.OPERATION_TOPIC_CREATED,
            topic_id="topic-123",
            agent_id="agent-a",
            details={"title": "Test Topic"}
        )
        
        assert log.id is not None
        assert log.operation_type == "topic_created"
        assert log.topic_id == "topic-123"
        assert log.agent_id == "agent-a"
        assert log.details is not None
        
        details = json.loads(log.details)
        assert details["title"] == "Test Topic"
        assert isinstance(log.created_at, datetime)
    
    def test_record_status_changed(self, test_db: Session):
        """Test recording a status_changed operation."""
        service = AuditLogService(test_db)
        
        log = service.record(
            operation_type=AuditLogService.OPERATION_STATUS_CHANGED,
            topic_id="topic-456",
            details={"old_status": "active", "new_status": "closing_pending"}
        )
        
        assert log.operation_type == "status_changed"
        assert log.topic_id == "topic-456"
        assert log.agent_id is None
        
        details = json.loads(log.details)
        assert details["old_status"] == "active"
        assert details["new_status"] == "closing_pending"
    
    def test_record_summary_updated(self, test_db: Session):
        """Test recording a summary_updated operation."""
        service = AuditLogService(test_db)
        
        log = service.record(
            operation_type=AuditLogService.OPERATION_SUMMARY_UPDATED,
            topic_id="topic-789",
            details={
                "job_id": "job-123",
                "llm_suggestion": "continue",
                "end_score": 25.5
            }
        )
        
        assert log.operation_type == "summary_updated"
        assert log.topic_id == "topic-789"
        
        details = json.loads(log.details)
        assert details["job_id"] == "job-123"
        assert details["llm_suggestion"] == "continue"
        assert details["end_score"] == 25.5
    
    def test_record_close_requested(self, test_db: Session):
        """Test recording a close_requested operation."""
        service = AuditLogService(test_db)
        
        log = service.record(
            operation_type=AuditLogService.OPERATION_CLOSE_REQUESTED,
            topic_id="topic-abc",
            agent_id="agent-b",
            details={"both_agreed": False}
        )
        
        assert log.operation_type == "close_requested"
        assert log.topic_id == "topic-abc"
        assert log.agent_id == "agent-b"
        
        details = json.loads(log.details)
        assert details["both_agreed"] is False
    
    def test_record_summary_rolled_back(self, test_db: Session):
        """Test recording a summary_rolled_back operation."""
        service = AuditLogService(test_db)
        
        log = service.record(
            operation_type=AuditLogService.OPERATION_SUMMARY_ROLLED_BACK,
            topic_id="topic-def",
            agent_id="admin",
            details={
                "history_id": "history-123",
                "reason": "Incorrect summary"
            }
        )
        
        assert log.operation_type == "summary_rolled_back"
        assert log.topic_id == "topic-def"
        assert log.agent_id == "admin"
        
        details = json.loads(log.details)
        assert details["history_id"] == "history-123"
        assert details["reason"] == "Incorrect summary"
    
    def test_record_force_end_applied(self, test_db: Session):
        """Test recording a force_end_applied operation."""
        service = AuditLogService(test_db)
        
        log = service.record(
            operation_type=AuditLogService.OPERATION_FORCE_END_APPLIED,
            topic_id="topic-ghi",
            details={"triggered_by": "llm_suggestion"}
        )
        
        assert log.operation_type == "force_end_applied"
        assert log.topic_id == "topic-ghi"
        
        details = json.loads(log.details)
        assert details["triggered_by"] == "llm_suggestion"
    
    def test_record_without_optional_fields(self, test_db: Session):
        """Test recording with minimal required fields."""
        service = AuditLogService(test_db)
        
        log = service.record(
            operation_type=AuditLogService.OPERATION_TOPIC_CREATED
        )
        
        assert log.id is not None
        assert log.operation_type == "topic_created"
        assert log.topic_id is None
        assert log.agent_id is None
        assert log.details is None
        assert isinstance(log.created_at, datetime)
    
    def test_record_with_none_details(self, test_db: Session):
        """Test recording with explicitly None details."""
        service = AuditLogService(test_db)
        
        log = service.record(
            operation_type=AuditLogService.OPERATION_STATUS_CHANGED,
            topic_id="topic-123",
            details=None
        )
        
        assert log.details is None
    
    def test_record_with_empty_details(self, test_db: Session):
        """Test recording with empty details dictionary."""
        service = AuditLogService(test_db)
        
        log = service.record(
            operation_type=AuditLogService.OPERATION_SUMMARY_UPDATED,
            topic_id="topic-456",
            details={}
        )
        
        assert log.details == "{}"
    
    def test_record_invalid_operation_type(self, test_db: Session):
        """Test that invalid operation type raises ValueError."""
        service = AuditLogService(test_db)
        
        with pytest.raises(ValueError) as exc_info:
            service.record(
                operation_type="invalid_operation",
                topic_id="topic-123"
            )
        
        assert "Invalid operation_type" in str(exc_info.value)
        assert "invalid_operation" in str(exc_info.value)
    
    def test_record_persists_to_database(self, test_db: Session):
        """Test that audit log is persisted to database."""
        service = AuditLogService(test_db)
        
        log = service.record(
            operation_type=AuditLogService.OPERATION_TOPIC_CREATED,
            topic_id="topic-persist",
            agent_id="agent-test"
        )
        
        # Query from database
        retrieved_log = test_db.query(AuditLog).filter(
            AuditLog.id == log.id
        ).first()
        
        assert retrieved_log is not None
        assert retrieved_log.id == log.id
        assert retrieved_log.operation_type == "topic_created"
        assert retrieved_log.topic_id == "topic-persist"
        assert retrieved_log.agent_id == "agent-test"
    
    def test_record_multiple_logs(self, test_db: Session):
        """Test recording multiple audit logs."""
        service = AuditLogService(test_db)
        
        log1 = service.record(
            operation_type=AuditLogService.OPERATION_TOPIC_CREATED,
            topic_id="topic-1"
        )
        
        log2 = service.record(
            operation_type=AuditLogService.OPERATION_STATUS_CHANGED,
            topic_id="topic-1"
        )
        
        log3 = service.record(
            operation_type=AuditLogService.OPERATION_SUMMARY_UPDATED,
            topic_id="topic-1"
        )
        
        # All logs should have unique IDs
        assert log1.id != log2.id
        assert log2.id != log3.id
        assert log1.id != log3.id
        
        # All logs should be in database
        all_logs = test_db.query(AuditLog).filter(
            AuditLog.topic_id == "topic-1"
        ).all()
        
        assert len(all_logs) == 3
    
    def test_record_with_complex_details(self, test_db: Session):
        """Test recording with complex nested details."""
        service = AuditLogService(test_db)
        
        complex_details = {
            "operation": "summary_update",
            "changes": {
                "summary": {
                    "old": "Old summary text",
                    "new": "New summary text"
                },
                "llm_suggestion": {
                    "old": "continue",
                    "new": "suggest_end"
                }
            },
            "metadata": {
                "job_id": "job-123",
                "retry_count": 0,
                "duration_ms": 1500
            }
        }
        
        log = service.record(
            operation_type=AuditLogService.OPERATION_SUMMARY_UPDATED,
            topic_id="topic-complex",
            details=complex_details
        )
        
        # Verify details can be parsed back
        parsed_details = json.loads(log.details)
        assert parsed_details["operation"] == "summary_update"
        assert parsed_details["changes"]["summary"]["old"] == "Old summary text"
        assert parsed_details["metadata"]["duration_ms"] == 1500
    
    def test_all_operation_constants_are_valid(self, test_db: Session):
        """Test that all operation type constants can be used."""
        service = AuditLogService(test_db)
        
        operations = [
            AuditLogService.OPERATION_TOPIC_CREATED,
            AuditLogService.OPERATION_STATUS_CHANGED,
            AuditLogService.OPERATION_SUMMARY_UPDATED,
            AuditLogService.OPERATION_CLOSE_REQUESTED,
            AuditLogService.OPERATION_SUMMARY_ROLLED_BACK,
            AuditLogService.OPERATION_FORCE_END_APPLIED
        ]
        
        for operation in operations:
            log = service.record(
                operation_type=operation,
                topic_id=f"topic-{operation}"
            )
            assert log.operation_type == operation
