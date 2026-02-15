"""Topic service for managing discussion topics."""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from models.models import Topic
from config.settings import settings


class ClosingStatusDetail:
    """Data class for closing status details."""
    
    def __init__(
        self,
        status: str,
        closing_requested_by: Optional[str] = None,
        closing_requested_at: Optional[datetime] = None,
        remaining_timeout_seconds: Optional[int] = None
    ):
        self.status = status
        self.closing_requested_by = closing_requested_by
        self.closing_requested_at = closing_requested_at
        self.remaining_timeout_seconds = remaining_timeout_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "status": self.status,
            "closing_requested_by": self.closing_requested_by,
            "closing_requested_at": self.closing_requested_at.isoformat() if self.closing_requested_at else None,
            "remaining_timeout_seconds": self.remaining_timeout_seconds
        }


class CloseStatus:
    """Data class for close request status."""
    
    def __init__(self, both_agreed: bool, status: str):
        self.both_agreed = both_agreed
        self.status = status


class TopicService:
    """Service for managing discussion topics."""
    
    def __init__(self, db: Session):
        """
        Initialize TopicService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_active_topic(self) -> Optional[Topic]:
        """
        Get the current active or closing_pending topic.
        
        Returns:
            Topic object if found, None otherwise
        """
        return self.db.query(Topic).filter(
            Topic.status.in_(['active', 'closing_pending'])
        ).first()
    
    def create_topic(self, title: Optional[str] = None, topic_description: Optional[str] = None) -> Topic:
        """
        Create a new topic with default values.
        
        Args:
            title: Optional topic title. If not provided, generates default title.
            topic_description: Optional detailed description of the topic scope and guidelines.
        
        Returns:
            Created Topic object
        """
        if title is None:
            title = f"Discussion Topic {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        
        topic = Topic(
            id=str(uuid.uuid4()),
            title=title,
            topic_description=topic_description,
            status="active",
            summary="",
            llm_suggestion=None,
            end_score=0.0,
            token_count_since_summary=0,
            summary_threshold=None,
            last_summarized_message_id=None,
            pending_summary_job=False,
            agent_a_wants_close=False,
            agent_b_wants_close=False,
            closing_requested_by=None,
            closing_requested_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)
        
        return topic
    
    def close_topic(self, topic_id: str) -> None:
        """
        Close a topic by setting its status to closed.
        
        Args:
            topic_id: ID of the topic to close
        
        Raises:
            ValueError: If topic not found
        """
        topic = self.db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")
        
        topic.status = "closed"
        topic.updated_at = datetime.utcnow()
        
        self.db.commit()
    
    def record_close_request(self, topic_id: str, agent_id: str) -> CloseStatus:
        """
        Record a close request from an agent and handle closing negotiation.
        
        Args:
            topic_id: ID of the topic
            agent_id: ID of the agent requesting close
        
        Returns:
            CloseStatus indicating whether both agents agreed and the new status
        
        Raises:
            ValueError: If topic not found
        """
        topic = self.db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")
        
        # Determine which agent is requesting
        # Assuming agent_id is either 'agent_a' or 'agent_b' or we use a simple logic
        # For simplicity, we'll use agent_a for the first requester and agent_b for the second
        if not topic.agent_a_wants_close and not topic.agent_b_wants_close:
            # First request
            topic.agent_a_wants_close = True
            topic.closing_requested_by = agent_id
            topic.closing_requested_at = datetime.utcnow()
            topic.status = "closing_pending"
            both_agreed = False
        elif topic.closing_requested_by == agent_id:
            # Same agent requesting again - no change
            both_agreed = False
        else:
            # Second agent agreeing
            topic.agent_b_wants_close = True
            both_agreed = True
            topic.status = "closed"
        
        topic.updated_at = datetime.utcnow()
        self.db.commit()
        
        return CloseStatus(both_agreed=both_agreed, status=topic.status)
    
    def cancel_close_request(self, topic_id: str, agent_id: str) -> None:
        """
        Cancel a close request from an agent.
        
        Args:
            topic_id: ID of the topic
            agent_id: ID of the agent canceling the request
        
        Raises:
            ValueError: If topic not found or agent didn't request close
        """
        topic = self.db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")
        
        # Only the agent who requested can cancel
        if topic.closing_requested_by != agent_id:
            raise ValueError(f"Agent {agent_id} did not request close")
        
        # Reset closing state
        topic.agent_a_wants_close = False
        topic.agent_b_wants_close = False
        topic.closing_requested_by = None
        topic.closing_requested_at = None
        topic.status = "active"
        topic.updated_at = datetime.utcnow()
        
        self.db.commit()
    def reject_close_request(self, topic_id: str, agent_id: str) -> None:
        """
        Reject a close request from another agent.

        Args:
            topic_id: ID of the topic
            agent_id: ID of the agent rejecting the request

        Raises:
            ValueError: If topic not found or not in closing_pending state
        """
        topic = self.db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")

        if topic.status != "closing_pending":
            raise ValueError("Topic is not in closing_pending state")

        # Only the agent who didn't request can reject
        if topic.closing_requested_by == agent_id:
            raise ValueError("Cannot reject your own close request")

        # Reset closing state - return to active
        topic.agent_a_wants_close = False
        topic.agent_b_wants_close = False
        topic.closing_requested_by = None
        topic.closing_requested_at = None
        topic.status = "active"
        topic.updated_at = datetime.utcnow()

        self.db.commit()

    
    
    def get_closing_status(self, topic_id: str) -> ClosingStatusDetail:
        """
        Get detailed closing status for a topic.
        
        Args:
            topic_id: ID of the topic
        
        Returns:
            ClosingStatusDetail with status information
        
        Raises:
            ValueError: If topic not found
        """
        topic = self.db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")
        
        remaining_timeout_seconds = None
        if topic.status == "closing_pending" and topic.closing_requested_at:
            timeout_seconds = settings.closing_timeout
            elapsed = (datetime.utcnow() - topic.closing_requested_at).total_seconds()
            remaining_timeout_seconds = max(0, int(timeout_seconds - elapsed))
        
        return ClosingStatusDetail(
            status=topic.status,
            closing_requested_by=topic.closing_requested_by,
            closing_requested_at=topic.closing_requested_at,
            remaining_timeout_seconds=remaining_timeout_seconds
        )
