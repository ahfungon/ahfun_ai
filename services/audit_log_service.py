"""Audit log service for recording system operations."""
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from models.models import AuditLog


class AuditLogService:
    """Service for recording audit logs of system operations."""
    
    # Operation types as defined in requirements 11.6
    OPERATION_TOPIC_CREATED = "topic_created"
    OPERATION_STATUS_CHANGED = "status_changed"
    OPERATION_SUMMARY_UPDATED = "summary_updated"
    OPERATION_CLOSE_REQUESTED = "close_requested"
    OPERATION_SUMMARY_ROLLED_BACK = "summary_rolled_back"
    OPERATION_FORCE_END_APPLIED = "force_end_applied"
    
    def __init__(self, db: Session):
        """
        Initialize AuditLogService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def record(
        self,
        operation_type: str,
        topic_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Record an audit log entry for a system operation.
        
        Args:
            operation_type: Type of operation (topic_created, status_changed, 
                          summary_updated, close_requested, summary_rolled_back, 
                          force_end_applied)
            topic_id: Optional ID of the related topic
            agent_id: Optional ID of the agent who performed the operation
            details: Optional dictionary with additional operation details
        
        Returns:
            Created AuditLog object
        
        Raises:
            ValueError: If operation_type is not valid
        """
        # Validate operation type
        valid_operations = {
            self.OPERATION_TOPIC_CREATED,
            self.OPERATION_STATUS_CHANGED,
            self.OPERATION_SUMMARY_UPDATED,
            self.OPERATION_CLOSE_REQUESTED,
            self.OPERATION_SUMMARY_ROLLED_BACK,
            self.OPERATION_FORCE_END_APPLIED
        }
        
        if operation_type not in valid_operations:
            raise ValueError(
                f"Invalid operation_type: {operation_type}. "
                f"Must be one of: {', '.join(valid_operations)}"
            )
        
        # Convert details dict to JSON string
        details_json = json.dumps(details) if details is not None else None
        
        # Create audit log entry
        audit_log = AuditLog(
            id=str(uuid.uuid4()),
            operation_type=operation_type,
            topic_id=topic_id,
            agent_id=agent_id,
            details=details_json,
            created_at=datetime.utcnow()
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        return audit_log
