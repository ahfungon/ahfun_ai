"""Message service for managing messages and triggering summary jobs."""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.models import Message, Topic
from models.database import transaction, atomic_update
from config.settings import settings
from workers.celery_app import celery_app


class MessageService:
    """Service for managing messages and token counting."""
    
    def __init__(self, db: Session):
        """
        Initialize MessageService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_message(
        self,
        topic_id: str,
        agent_id: str,
        content: str,
        actual_tokens: int
    ) -> Message:
        """
        Create and store a new message, update token count, and trigger summary job if needed.
        
        Uses database transactions to ensure atomicity of:
        - Message creation
        - Token count update
        - Summary job trigger flag
        
        Args:
            topic_id: ID of the topic
            agent_id: ID of the agent sending the message
            content: Message content
            actual_tokens: Actual token count from OpenClaw LLM
        
        Returns:
            Created Message object
        
        Raises:
            ValueError: If topic not found or topic is closed
            
        Validates:
            Requirements 5.1, 5.2, 5.3, 5.4, 10.1, 10.2, 10.3
        """
        # Use atomic transaction for entire operation
        with transaction(self.db):
            # Verify topic exists and is not closed (with row lock)
            topic = self.db.query(Topic).filter(
                Topic.id == topic_id
            ).with_for_update().first()
            
            if not topic:
                raise ValueError(f"Topic {topic_id} not found")
            
            if topic.status == "closed":
                raise ValueError(f"Cannot post message to closed topic {topic_id}")
            
            # Create message
            message = Message(
                id=str(uuid.uuid4()),
                topic_id=topic_id,
                agent_id=agent_id,
                content=content,
                actual_tokens=actual_tokens,
                created_at=datetime.utcnow()
            )
            
            self.db.add(message)
            
            # Atomically update token count
            topic.token_count_since_summary += actual_tokens
            topic.updated_at = datetime.utcnow()
            new_token_count = topic.token_count_since_summary
            
            # Check if we need to trigger a summary job
            threshold = topic.summary_threshold if topic.summary_threshold else settings.summary_threshold
            
            should_trigger_summary = (
                new_token_count >= threshold and 
                not topic.pending_summary_job
            )
            
            if should_trigger_summary:
                # Mark that a summary job is pending
                topic.pending_summary_job = True
                topic.updated_at = datetime.utcnow()
            
            # Transaction commits here automatically
        
        # Refresh message to get committed state
        self.db.refresh(message)

        # Check for close keywords in message content
        # Auto-handle topic close when agents express intent in messages
        topic_after = self.db.query(Topic).filter(Topic.id == topic_id).first()
        
        # Keywords for requesting close
        request_close_keywords = ['建议结束', '可以结束了', '讨论得差不多了', '已经充分讨论', '达成共识', '没有更多要补充', '请求结束', '终止讨论']
        
        # Keywords for agreeing to close
        agree_close_keywords = ['同意', '赞成', '可以结束', '没问题', '确实该结束了', '同意结束', '赞成的', '可以关闭', '没问题了']
        
        if topic_after and topic_after.status == "closing_pending":
            # Topic is waiting for close agreement - check if this agent agrees
            if topic_after.closing_requested_by != agent_id:
                content_lower = content.lower()
                for keyword in agree_close_keywords:
                    if keyword in content_lower:
                        # Auto-agree to close
                        topic_after.agent_b_wants_close = True
                        topic_after.status = "closed"
                        topic_after.updated_at = datetime.utcnow()
                        self.db.commit()
                        
                        # Trigger new topic generation
                        from workers.tasks import generate_new_topic
                        generate_new_topic.apply_async(args=[agent_id], countdown=2)
                        break
        elif topic_after and topic_after.status == "active":
            # Check if message contains request close keywords
            content_lower = content.lower()
            for keyword in request_close_keywords:
                if keyword in content_lower:
                    # Auto-request close
                    if not topic_after.agent_a_wants_close and not topic_after.agent_b_wants_close:
                        topic_after.agent_a_wants_close = True
                        topic_after.closing_requested_by = agent_id
                        topic_after.closing_requested_at = datetime.utcnow()
                        topic_after.status = "closing_pending"
                        topic_after.updated_at = datetime.utcnow()
                        self.db.commit()
                    break


        
        # Trigger summary job outside transaction (async operation)
        if should_trigger_summary:
            from services.queue_service import QueueService
            queue_service = QueueService(self.db)
            queue_service.enqueue_summary_job(
                topic_id=topic_id,
                start_message_id=topic.last_summarized_message_id,
                end_message_id=message.id
            )
        
        # Trigger async message relevance evaluation
        from workers.tasks import evaluate_message_relevance
        evaluate_message_relevance.delay(
            message_id=message.id,
            topic_id=topic_id,
            agent_id=agent_id,
            content=content
        )
        
        return message
    
    def get_messages(self, topic_id: str, limit: int = 20) -> List[Message]:
        """
        Get recent messages for a topic, sorted by time (oldest to newest).
        
        Args:
            topic_id: ID of the topic
            limit: Maximum number of messages to return (default 20)
        
        Returns:
            List of Message objects sorted by created_at ascending
        """
        # Query messages in descending order, then reverse
        messages = self.db.query(Message).filter(
            Message.topic_id == topic_id
        ).order_by(desc(Message.created_at)).limit(limit).all()
        
        # Reverse to get oldest to newest
        return list(reversed(messages))
    
    def increment_token_count(self, topic_id: str, tokens: int) -> int:
        """
        Atomically increment the token count for a topic.
        
        This method uses database transactions with row-level locking
        to ensure atomic updates and prevent race conditions in concurrent scenarios.
        
        Note: This method is now primarily used internally by create_message.
        The transaction and locking are handled at the create_message level.
        
        Args:
            topic_id: ID of the topic
            tokens: Number of tokens to add
        
        Returns:
            New token count after increment
        
        Raises:
            ValueError: If topic not found
            
        Validates:
            Requirements 5.3, 10.1, 10.2, 10.5
        """
        with atomic_update(self.db, Topic, topic_id) as topic:
            # Atomically update token count with row lock
            topic.token_count_since_summary += tokens
            topic.updated_at = datetime.utcnow()
            new_count = topic.token_count_since_summary
        
        return new_count
