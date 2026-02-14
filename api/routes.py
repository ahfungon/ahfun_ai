"""API routes for the Dual Agent Chat Platform."""
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth_middleware import AuthMiddleware
from api.exceptions import AuthenticationError
from models.database import get_db
from models.models import Agent
from services.topic_service import TopicService
from services.message_service import MessageService
from services.summary_service import SummaryService


# Create API router
router = APIRouter(prefix="/api", tags=["api"])


# Request/Response Models
class CreateTopicRequest(BaseModel):
    """Request model for creating a new topic."""
    title: Optional[str] = Field(None, description="Optional topic title")


class CreateTopicResponse(BaseModel):
    """Response model for topic creation."""
    topic_id: str
    status: str
    title: str


class PostMessageRequest(BaseModel):
    """Request model for posting a message."""
    topic_id: str
    content: str
    actual_tokens: int = Field(..., description="Actual token count from OpenClaw")


class PostMessageResponse(BaseModel):
    """Response model for message posting."""
    message_id: str
    token_count: int


class RequestCloseResponse(BaseModel):
    """Response model for close request."""
    status: str
    both_agreed: bool


class TopicResponse(BaseModel):
    """Response model for topic information."""
    topic_id: str
    title: str
    status: str
    summary: str
    llm_suggestion: Optional[str]
    end_score: float
    token_count_since_summary: int
    closing_status: Optional[dict] = None


class MessageResponse(BaseModel):
    """Response model for a single message."""
    message_id: str
    agent_id: str
    content: str
    created_at: str


class MessagesResponse(BaseModel):
    """Response model for messages list."""
    messages: list[MessageResponse]


class SummaryHistoryItem(BaseModel):
    """Response model for a summary history item."""
    history_id: str
    summary: str
    llm_suggestion: str
    end_score: float
    created_at: str


class SummaryHistoryResponse(BaseModel):
    """Response model for summary history."""
    history: list[SummaryHistoryItem]


class RollbackSummaryRequest(BaseModel):
    """Request model for rolling back summary."""
    history_id: str


# Dependency for authentication
def get_current_agent(request: Request, db: Session = Depends(get_db)) -> Agent:
    """
    Dependency to authenticate and get current agent from request headers.
    
    Args:
        request: FastAPI request object
        db: Database session
    
    Returns:
        Authenticated Agent object
    
    Raises:
        HTTPException: 401 if authentication fails
    """
    try:
        return AuthMiddleware.authenticate(request, db)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


# API Endpoints

@router.get("/topic/active", response_model=TopicResponse)
async def get_active_topic(
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
):
    """
    Get the current active or closing_pending topic.
    
    Returns topic information including summary, LLM suggestion, and status.
    """
    topic_service = TopicService(db)
    topic = topic_service.get_active_topic()
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active topic found"
        )
    
    # Get closing status details if in closing_pending state
    closing_status = None
    if topic.status == "closing_pending":
        closing_detail = topic_service.get_closing_status(topic.id)
        closing_status = closing_detail.to_dict()
    
    return TopicResponse(
        topic_id=topic.id,
        title=topic.title,
        status=topic.status,
        summary=topic.summary,
        llm_suggestion=topic.llm_suggestion,
        end_score=topic.end_score,
        token_count_since_summary=topic.token_count_since_summary,
        closing_status=closing_status
    )


@router.get("/topic/{topic_id}/messages", response_model=MessagesResponse)
async def get_topic_messages(
    topic_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
):
    """
    Get recent messages for a topic.
    
    Args:
        topic_id: ID of the topic
        limit: Maximum number of messages to return (default 20)
    
    Returns:
        List of messages sorted by time (oldest to newest)
    """
    message_service = MessageService(db)
    messages = message_service.get_messages(topic_id, limit)
    
    return MessagesResponse(
        messages=[
            MessageResponse(
                message_id=msg.id,
                agent_id=msg.agent_id,
                content=msg.content,
                created_at=msg.created_at.isoformat()
            )
            for msg in messages
        ]
    )


@router.post("/message", response_model=PostMessageResponse)
async def post_message(
    request: PostMessageRequest,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
):
    """
    Post a new message to a topic.
    
    Creates the message, updates token count, and triggers summary job if threshold is reached.
    """
    message_service = MessageService(db)
    
    try:
        message = message_service.create_message(
            topic_id=request.topic_id,
            agent_id=agent.id,
            content=request.content,
            actual_tokens=request.actual_tokens
        )
        
        # Get updated token count
        topic_service = TopicService(db)
        topic = topic_service.get_active_topic()
        
        return PostMessageResponse(
            message_id=message.id,
            token_count=topic.token_count_since_summary if topic else 0
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/topic/{topic_id}/request-close", response_model=RequestCloseResponse)
async def request_close_topic(
    topic_id: str,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
):
    """
    Request to close a topic.
    
    Records the agent's close request. If both agents agree, closes the topic.
    """
    topic_service = TopicService(db)
    
    try:
        close_status = topic_service.record_close_request(topic_id, agent.id)
        
        return RequestCloseResponse(
            status=close_status.status,
            both_agreed=close_status.both_agreed
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/topic/{topic_id}/cancel-close")
async def cancel_close_request(
    topic_id: str,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
):
    """
    Cancel a close request for a topic.
    
    Only the agent who requested close can cancel it.
    """
    topic_service = TopicService(db)
    
    try:
        topic_service.cancel_close_request(topic_id, agent.id)
        
        return {"status": "success", "message": "Close request cancelled"}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/topic", response_model=CreateTopicResponse)
async def create_topic(
    request: CreateTopicRequest,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
):
    """
    Create a new topic.
    
    Args:
        request: Topic creation request with optional title
    
    Returns:
        Created topic information
    """
    topic_service = TopicService(db)
    topic = topic_service.create_topic(title=request.title)
    
    return CreateTopicResponse(
        topic_id=topic.id,
        status=topic.status,
        title=topic.title
    )


@router.get("/topic/{topic_id}/summary-history", response_model=SummaryHistoryResponse)
async def get_summary_history(
    topic_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
):
    """
    Get historical summary versions for a topic.
    
    Args:
        topic_id: ID of the topic
        limit: Maximum number of history records to return
    
    Returns:
        List of summary history records
    """
    summary_service = SummaryService(db)
    history = summary_service.get_summary_history(topic_id, limit)
    
    return SummaryHistoryResponse(
        history=[
            SummaryHistoryItem(
                history_id=h.id,
                summary=h.summary,
                llm_suggestion=h.llm_suggestion,
                end_score=h.end_score,
                created_at=h.created_at.isoformat()
            )
            for h in history
        ]
    )


@router.post("/topic/{topic_id}/rollback-summary")
async def rollback_summary(
    topic_id: str,
    request: RollbackSummaryRequest,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
):
    """
    Rollback topic summary to a historical version.
    
    Args:
        topic_id: ID of the topic
        request: Rollback request with history_id
    
    Returns:
        Success message
    """
    summary_service = SummaryService(db)
    
    try:
        summary_service.rollback_summary(topic_id, request.history_id)
        
        return {"status": "success", "message": "Summary rolled back successfully"}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns system status and service availability.
    """
    # Basic health check - will be enhanced in Task 20
    return {
        "status": "ok",
        "message": "Service is running",
        "database": "connected",  # TODO: Add actual database check
        "redis": "unknown",  # TODO: Add Redis check
        "llm_service": "unknown"  # TODO: Add LLM service check
    }
