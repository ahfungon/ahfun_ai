"""API routes for the Dual Agent Chat Platform."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth_middleware import AuthMiddleware
from api.exceptions import AuthenticationError
from models.database import get_db
from models.models import Agent
from services.topic_service import TopicService
from services.message_service import MessageService
from services.summary_service import SummaryService
from services.audit_log_service import AuditLogService


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


class RegisterAgentRequest(BaseModel):
    """Request model for agent registration."""
    agent_name: str = Field(..., description="Display name for the agent", min_length=1, max_length=100)


class RegisterAgentResponse(BaseModel):
    """Response model for agent registration."""
    agent_id: str
    agent_name: str
    auth_token: str


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
    llm_hint: Optional[str] = None  # Hint message for LLM suggestions


class MessageResponse(BaseModel):
    """Response model for a single message."""
    message_id: str
    agent_id: str
    agent_name: Optional[str] = None
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

@router.get("/monitor/topic/active", response_model=TopicResponse)
async def monitor_active_topic(db: Session = Depends(get_db)):
    """
    Monitor endpoint: Get the current active topic without authentication.
    This endpoint is for monitoring/display purposes only.
    
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
        closing_status = topic_service.get_closing_status(topic.id)
    
    # Get LLM hint if applicable
    llm_hint = None
    if topic.llm_suggestion and topic.status != "closing_pending":
        llm_hint = _get_llm_hint(topic.llm_suggestion)
    
    return TopicResponse(
        topic_id=topic.id,
        title=topic.title,
        status=topic.status,
        summary=topic.summary,
        llm_suggestion=topic.llm_suggestion,
        llm_hint=llm_hint,
        end_score=topic.end_score,
        token_count_since_summary=topic.token_count_since_summary,
        agent_a_wants_close=topic.agent_a_wants_close,
        agent_b_wants_close=topic.agent_b_wants_close,
        closing_requested_by=closing_status.get("requested_by") if closing_status else None,
        closing_requested_at=closing_status.get("requested_at") if closing_status else None,
        closing_timeout_remaining=closing_status.get("timeout_remaining") if closing_status else None,
        created_at=topic.created_at,
        updated_at=topic.updated_at
    )


@router.get("/monitor/topic/{topic_id}/messages", response_model=MessagesResponse)
async def monitor_topic_messages(
    topic_id: str,
    limit: int = Query(default=50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Monitor endpoint: Get messages for a topic without authentication.
    This endpoint is for monitoring/display purposes only.
    
    Args:
        topic_id: Topic ID
        limit: Maximum number of messages to return (default: 50, max: 1000)
    
    Returns:
        List of messages ordered by creation time
    """
    message_service = MessageService(db)
    messages = message_service.get_messages(topic_id, limit=limit)
    
    # Get agent names for all messages
    agent_ids = list(set(msg.agent_id for msg in messages))
    agents = db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
    agent_name_map = {agent.id: agent.name for agent in agents}
    
    return MessagesResponse(
        messages=[
            MessageResponse(
                message_id=msg.id,
                topic_id=msg.topic_id,
                agent_id=msg.agent_id,
                agent_name=agent_name_map.get(msg.agent_id),
                content=msg.content,
                created_at=msg.created_at.isoformat() if msg.created_at else ""
            )
            for msg in messages
        ]
    )


@router.get("/topic/active", response_model=TopicResponse)
async def get_active_topic(
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
):
    """
    Get the current active or closing_pending topic.
    
    Returns topic information including summary, LLM suggestion, and status.
    Includes hint messages for change_angle and suggest_end suggestions.
    
    Validates:
        Requirements 7.1, 7.2, 7.3, 7.4, 7.8
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
    
    # Generate hint message based on LLM suggestion
    # When in closing_pending, don't provide new hints (Requirement 7.8)
    llm_hint = None
    if topic.status != "closing_pending" and topic.llm_suggestion:
        llm_hint = _get_llm_hint(topic.llm_suggestion)
    
    return TopicResponse(
        topic_id=topic.id,
        title=topic.title,
        status=topic.status,
        summary=topic.summary,
        llm_suggestion=topic.llm_suggestion,
        end_score=topic.end_score,
        token_count_since_summary=topic.token_count_since_summary,
        closing_status=closing_status,
        llm_hint=llm_hint
    )


def _get_llm_hint(suggestion: str) -> Optional[str]:
    """
    Get hint message for LLM suggestion.
    
    Args:
        suggestion: LLM suggestion type
    
    Returns:
        Hint message string or None for continue/force_end
    
    Validates:
        Requirements 7.2, 7.3, 7.4
    """
    hints = {
        "change_angle": "The conversation may benefit from exploring a different perspective or angle.",
        "suggest_end": "Consider whether the discussion has reached a natural conclusion.",
        "continue": None,  # No hint for continue
        "force_end": None  # force_end is handled automatically by system
    }
    return hints.get(suggestion)


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
    
    # Get agent names for all messages
    agent_ids = list(set(msg.agent_id for msg in messages))
    agents = db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
    agent_name_map = {agent.id: agent.name for agent in agents}
    
    return MessagesResponse(
        messages=[
            MessageResponse(
                message_id=msg.id,
                agent_id=msg.agent_id,
                agent_name=agent_name_map.get(msg.agent_id),
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
        
    Validates:
        Requirements 11.5, 11.6
    """
    summary_service = SummaryService(db)
    audit_service = AuditLogService(db)
    
    try:
        summary_service.rollback_summary(topic_id, request.history_id)
        
        # Record audit log for rollback operation
        audit_service.record(
            operation_type=AuditLogService.OPERATION_SUMMARY_ROLLED_BACK,
            topic_id=topic_id,
            agent_id=agent.id,
            details={
                "history_id": request.history_id
            }
        )
        
        return {"status": "success", "message": "Summary rolled back successfully"}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    
    Returns system status and service availability.
    Checks:
    - Database connection
    - Redis connection
    - LLM services (OpenClaw and DeepSeek)
    
    Validates:
        Requirement 12.9
    """
    from services.llm_clients.openclaw_client import OpenClawClient
    from services.llm_clients.deepseek_client import DeepSeekClient
    import redis
    from config.settings import settings
    
    health_status = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check database connection
    try:
        # Simple query to test database
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # Check Redis connection
    try:
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        health_status["services"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
    
    # Check OpenClaw LLM service
    try:
        openclaw_client = OpenClawClient(
            api_key=settings.openclaw_api_key,
            api_url=settings.openclaw_api_url
        )
        # We don't actually call the API, just check if client can be initialized
        health_status["services"]["openclaw"] = {
            "status": "healthy",
            "message": "OpenClaw client initialized"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["openclaw"] = {
            "status": "unhealthy",
            "message": f"OpenClaw client initialization failed: {str(e)}"
        }
    
    # Check DeepSeek LLM service
    try:
        deepseek_client = DeepSeekClient(
            api_key=settings.deepseek_api_key,
            api_url=settings.deepseek_api_url
        )
        # We don't actually call the API, just check if client can be initialized
        health_status["services"]["deepseek"] = {
            "status": "healthy",
            "message": "DeepSeek client initialized"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["deepseek"] = {
            "status": "unhealthy",
            "message": f"DeepSeek client initialization failed: {str(e)}"
        }
    
    return health_status
@router.post("/agent/register", response_model=RegisterAgentResponse)
async def register_agent(
    request: RegisterAgentRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new AI agent.

    This endpoint allows AI agents to self-register and obtain authentication credentials.
    No authentication required for this endpoint.

    Args:
        request: Agent registration request with name

    Returns:
        Agent ID and authentication token
    """
    import uuid
    import secrets
    from utils.auth_utils import hash_token

    # Generate unique agent ID
    agent_id = f"agent-{uuid.uuid4().hex[:8]}"

    # Generate secure random token
    auth_token = f"token-{secrets.token_urlsafe(32)}"

    # Create agent record
    agent = Agent(
        id=agent_id,
        name=request.agent_name,
        auth_token_hash=hash_token(auth_token)
    )

    try:
        db.add(agent)
        db.commit()
        db.refresh(agent)

        return RegisterAgentResponse(
            agent_id=agent.id,
            agent_name=agent.name,
            auth_token=auth_token
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register agent: {str(e)}"
        )
