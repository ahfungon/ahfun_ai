"""SQLAlchemy models for Dual Agent Chat Platform."""
from datetime import datetime
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Float, 
    ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship

from models.database import Base


class Topic(Base):
    """
    Topic model representing a discussion topic.
    
    Attributes:
        id: Unique topic identifier (UUID)
        title: Topic title
        topic_description: Detailed description of the topic scope and guidelines
        status: Topic status (active, closing_pending, closed)
        summary: Cumulative summary of the discussion
        llm_suggestion: LLM suggestion (continue, change_angle, suggest_end, force_end)
        end_score: End score from LLM (0-100)
        token_count_since_summary: Token count since last summary
        summary_threshold: Custom threshold for this topic (optional)
        last_summarized_message_id: ID of last summarized message
        pending_summary_job: Flag indicating pending summary job
        agent_a_wants_close: Whether agent A wants to close
        agent_b_wants_close: Whether agent B wants to close
        closing_requested_by: Agent ID who requested closing
        closing_requested_at: Timestamp of closing request
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "topics"
    
    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    topic_description = Column(Text, nullable=True)
    status = Column(
        String(20), 
        nullable=False, 
        default="active"
    )
    summary = Column(Text, nullable=True, default="")
    llm_suggestion = Column(String(20), nullable=True)
    end_score = Column(Float, nullable=True, default=0.0)
    token_count_since_summary = Column(Integer, nullable=False, default=0)
    summary_threshold = Column(Integer, nullable=True)
    last_summarized_message_id = Column(String(36), nullable=True)
    pending_summary_job = Column(Boolean, nullable=False, default=False)
    agent_a_wants_close = Column(Boolean, nullable=False, default=False)
    agent_b_wants_close = Column(Boolean, nullable=False, default=False)
    closing_requested_by = Column(Text, nullable=True)
    closing_requested_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="topic", cascade="all, delete-orphan")
    summary_jobs = relationship("SummaryJob", back_populates="topic", cascade="all, delete-orphan")
    summary_history = relationship("SummaryHistory", back_populates="topic", cascade="all, delete-orphan")
    relevance_scores = relationship("MessageRelevanceScore", back_populates="topic", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'closing_pending', 'closed')",
            name="check_topic_status"
        ),
        CheckConstraint(
            "llm_suggestion IS NULL OR llm_suggestion IN ('continue', 'change_angle', 'suggest_end', 'force_end')",
            name="check_llm_suggestion"
        ),
        CheckConstraint(
            "token_count_since_summary >= 0",
            name="check_token_count_positive"
        ),
        CheckConstraint(
            "end_score IS NULL OR (end_score >= 0 AND end_score <= 100)",
            name="check_end_score_range"
        ),
    )


class Message(Base):
    """
    Message model representing a single message in a topic.
    
    Attributes:
        id: Unique message identifier (UUID)
        topic_id: Foreign key to topic
        agent_id: Agent who sent the message
        content: Message content
        actual_tokens: Actual token count from LLM
        created_at: Creation timestamp
    """
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True)
    topic_id = Column(String(36), ForeignKey("topics.id"), nullable=False)
    agent_id = Column(String(36), nullable=False)
    content = Column(Text, nullable=False)
    actual_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    topic = relationship("Topic", back_populates="messages")
    relevance_score = relationship("MessageRelevanceScore", back_populates="message", uselist=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "content != ''",
            name="check_content_not_empty"
        ),
        CheckConstraint(
            "actual_tokens >= 0",
            name="check_actual_tokens_positive"
        ),
    )


class Agent(Base):
    """
    Agent model representing an AI agent.
    
    Attributes:
        id: Unique agent identifier
        name: Display name
        auth_token_hash: Hashed authentication token
        system_prompt: System prompt for agent personality and speaking style
        created_at: Creation timestamp
    """
    __tablename__ = "agents"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    auth_token_hash = Column(String(128), nullable=False)
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SummaryJob(Base):
    """
    SummaryJob model representing an asynchronous summary task.
    
    Attributes:
        id: Unique job identifier (UUID)
        topic_id: Foreign key to topic
        start_message_id: Starting message ID for summary
        end_message_id: Ending message ID for summary
        status: Job status (pending, processing, done, failed)
        retry_count: Number of retry attempts
        error_message: Error message if failed
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "summary_jobs"
    
    id = Column(String(36), primary_key=True)
    topic_id = Column(String(36), ForeignKey("topics.id"), nullable=False)
    start_message_id = Column(String(36), nullable=True)
    end_message_id = Column(String(36), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    retry_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    topic = relationship("Topic", back_populates="summary_jobs")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'done', 'failed')",
            name="check_summary_job_status"
        ),
        CheckConstraint(
            "retry_count >= 0",
            name="check_retry_count_positive"
        ),
    )


class SummaryHistory(Base):
    """
    SummaryHistory model representing historical summary versions.
    
    Attributes:
        id: Unique history identifier (UUID)
        topic_id: Foreign key to topic
        summary: Summary content
        llm_suggestion: LLM suggestion at time of summary
        end_score: End score at time of summary
        created_at: Creation timestamp
    """
    __tablename__ = "summary_history"
    
    id = Column(String(36), primary_key=True)
    topic_id = Column(String(36), ForeignKey("topics.id"), nullable=False)
    summary = Column(Text, nullable=False)
    llm_suggestion = Column(String(20), nullable=False)
    end_score = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    topic = relationship("Topic", back_populates="summary_history")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "llm_suggestion IN ('continue', 'change_angle', 'suggest_end', 'force_end')",
            name="check_history_llm_suggestion"
        ),
        CheckConstraint(
            "end_score >= 0 AND end_score <= 100",
            name="check_history_end_score_range"
        ),
    )


class AuditLog(Base):
    """
    AuditLog model representing audit trail of operations.
    
    Attributes:
        id: Unique log identifier (UUID)
        operation_type: Type of operation performed
        topic_id: Related topic ID (optional)
        agent_id: Agent who performed operation (optional)
        details: JSON details of the operation
        created_at: Operation timestamp
    """
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True)
    operation_type = Column(String(50), nullable=False)
    topic_id = Column(String(36), nullable=True)
    agent_id = Column(String(36), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class MessageRelevanceScore(Base):
    """
    MessageRelevanceScore model representing relevance evaluation for messages.
    
    Attributes:
        id: Unique score identifier (UUID)
        message_id: Foreign key to message
        topic_id: Foreign key to topic
        agent_id: Agent who sent the message
        relevance_score: Relevance score (0-100)
        evaluation_comment: Brief evaluation comment
        evaluated_at: Evaluation timestamp
    """
    __tablename__ = "message_relevance_scores"
    
    id = Column(String(36), primary_key=True)
    message_id = Column(String(36), ForeignKey("messages.id"), nullable=False, unique=True)
    topic_id = Column(String(36), ForeignKey("topics.id"), nullable=False)
    agent_id = Column(String(36), nullable=False)
    relevance_score = Column(Float, nullable=False)
    evaluation_comment = Column(Text, nullable=True)
    evaluated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="relevance_score")
    topic = relationship("Topic", back_populates="relevance_scores")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "relevance_score >= 0 AND relevance_score <= 100",
            name="check_relevance_score_range"
        ),
    )
