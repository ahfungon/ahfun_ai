"""API routes for the Dual Agent Chat Platform."""
from datetime import datetime
from typing import Optional
import time
from fastapi import APIRouter, Depends, Request, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth_middleware import AuthMiddleware
from api.exceptions import AuthenticationError
from models.database import get_db
from models.models import Agent, Topic, Message
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
    topic_description: Optional[str] = Field(None, description="Optional detailed description of the topic scope and guidelines")


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
    topic_description: Optional[str] = None
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
    relevance_score: Optional[float] = None
    evaluation_comment: Optional[str] = None


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


class AgentScoreResponse(BaseModel):
    """Response model for agent score statistics."""
    average_score: Optional[float]
    recent_scores: list[dict]


class UpdateTopicRequest(BaseModel):
    """Request model for updating a topic."""
    title: Optional[str] = Field(None, description="Topic title")
    topic_description: Optional[str] = Field(None, description="Topic description")


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
        closing_status_detail = topic_service.get_closing_status(topic.id)
        closing_status = closing_status_detail.to_dict() if closing_status_detail else None
    
    # Get LLM hint if applicable
    llm_hint = None
    if topic.llm_suggestion and topic.status != "closing_pending":
        llm_hint = _get_llm_hint(topic.llm_suggestion)
    
    return TopicResponse(
        topic_id=topic.id,
        title=topic.title,
        topic_description=topic.topic_description,
        status=topic.status,
        summary=topic.summary,
        llm_suggestion=topic.llm_suggestion,
        llm_hint=llm_hint,
        end_score=topic.end_score,
        token_count_since_summary=topic.token_count_since_summary,
        closing_status=closing_status
    )


@router.get("/monitor/topic/{topic_id}/messages", response_model=MessagesResponse)
async def monitor_topic_messages(
    topic_id: str,
    limit: int = Query(default=50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Monitor endpoint: Get messages for a topic without authentication with relevance scores.
    This endpoint is for monitoring/display purposes only.
    
    Args:
        topic_id: Topic ID
        limit: Maximum number of messages to return (default: 50, max: 1000)
    
    Returns:
        List of messages ordered by creation time with relevance scores
    """
    from models.models import MessageRelevanceScore
    
    message_service = MessageService(db)
    messages = message_service.get_messages(topic_id, limit=limit)
    
    # Get agent names for all messages
    agent_ids = list(set(msg.agent_id for msg in messages))
    agents = db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
    agent_name_map = {agent.id: agent.name for agent in agents}
    
    # Get relevance scores for all messages
    message_ids = [msg.id for msg in messages]
    scores = db.query(MessageRelevanceScore).filter(
        MessageRelevanceScore.message_id.in_(message_ids)
    ).all()
    score_map = {score.message_id: score for score in scores}
    
    return MessagesResponse(
        messages=[
            MessageResponse(
                message_id=msg.id,
                agent_id=msg.agent_id,
                agent_name=agent_name_map.get(msg.agent_id),
                content=msg.content,
                created_at=msg.created_at.isoformat() + 'Z' if msg.created_at else "",
                relevance_score=score_map[msg.id].relevance_score if msg.id in score_map else None,
                evaluation_comment=score_map[msg.id].evaluation_comment if msg.id in score_map else None
            )
            for msg in messages
        ]
    )


@router.get("/monitor/topics/closed")
async def monitor_closed_topics(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Monitor endpoint: Get list of closed topics without authentication.
    This endpoint is for monitoring/display purposes only.
    
    Args:
        limit: Maximum number of topics to return (default: 20, max: 100)
    
    Returns:
        List of closed topics ordered by updated_at descending
    """
    topics = db.query(Topic).filter(
        Topic.status == 'closed'
    ).order_by(Topic.updated_at.desc()).limit(limit).all()
    
    # Get message count for each topic
    topic_data = []
    for topic in topics:
        message_count = db.query(Message).filter(Message.topic_id == topic.id).count()
        topic_data.append({
            "topic_id": topic.id,
            "title": topic.title,
            "topic_description": topic.topic_description,
            "status": topic.status,
            "end_score": topic.end_score,
            "message_count": message_count,
            "created_at": topic.created_at.isoformat() + 'Z' if topic.created_at else "",
            "updated_at": topic.updated_at.isoformat() + 'Z' if topic.updated_at else ""
        })
    
    return {"topics": topic_data}


@router.get("/monitor/topic/{topic_id}")
async def monitor_topic_detail(
    topic_id: str,
    db: Session = Depends(get_db)
):
    """
    Monitor endpoint: Get detailed information for a specific topic without authentication.
    This endpoint is for monitoring/display purposes only.
    
    Args:
        topic_id: Topic ID
    
    Returns:
        Topic information including summary and LLM suggestion
    """
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    # Get closing status details if in closing_pending state
    topic_service = TopicService(db)
    closing_status = None
    if topic.status == "closing_pending":
        closing_status = topic_service.get_closing_status(topic.id)
    
    # Get LLM hint if applicable
    llm_hint = None
    if topic.llm_suggestion and topic.status != "closing_pending":
        llm_hint = _get_llm_hint(topic.llm_suggestion)
    
    return {
        "topic_id": topic.id,
        "title": topic.title,
        "topic_description": topic.topic_description,
        "status": topic.status,
        "summary": topic.summary,
        "llm_suggestion": topic.llm_suggestion,
        "llm_hint": llm_hint,
        "end_score": topic.end_score,
        "token_count_since_summary": topic.token_count_since_summary,
        "created_at": topic.created_at.isoformat() + 'Z' if topic.created_at else "",
        "updated_at": topic.updated_at.isoformat() + 'Z' if topic.updated_at else ""
    }


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
        topic_description=topic.topic_description,
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
    Get recent messages for a topic with relevance scores.
    
    Args:
        topic_id: ID of the topic
        limit: Maximum number of messages to return (default 20)
    
    Returns:
        List of messages sorted by time (oldest to newest) with relevance scores
    """
    from models.models import MessageRelevanceScore
    
    message_service = MessageService(db)
    messages = message_service.get_messages(topic_id, limit)
    
    # Get agent names for all messages
    agent_ids = list(set(msg.agent_id for msg in messages))
    agents = db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
    agent_name_map = {agent.id: agent.name for agent in agents}
    
    # Get relevance scores for all messages
    message_ids = [msg.id for msg in messages]
    scores = db.query(MessageRelevanceScore).filter(
        MessageRelevanceScore.message_id.in_(message_ids)
    ).all()
    score_map = {score.message_id: score for score in scores}
    
    return MessagesResponse(
        messages=[
            MessageResponse(
                message_id=msg.id,
                agent_id=msg.agent_id,
                agent_name=agent_name_map.get(msg.agent_id),
                content=msg.content,
                created_at=msg.created_at.isoformat() + 'Z',
                relevance_score=score_map[msg.id].relevance_score if msg.id in score_map else None,
                evaluation_comment=score_map[msg.id].evaluation_comment if msg.id in score_map else None
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
@router.post("/topic/{topic_id}/reject-close")
async def reject_close_request(
    topic_id: str,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
):
    """
    Reject a close request for a topic.

    Only the agent who didn't request close can reject it.
    This will return the topic to active status.
    """
    topic_service = TopicService(db)

    try:
        topic_service.reject_close_request(topic_id, agent.id)

        return {"status": "success", "message": "Close request rejected, topic is now active"}

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
        request: Topic creation request with optional title and description
    
    Returns:
        Created topic information
    """
    topic_service = TopicService(db)
    topic = topic_service.create_topic(
        title=request.title,
        topic_description=request.topic_description
    )
    
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
                created_at=h.created_at.isoformat() + 'Z'
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


@router.get("/agent/my-scores", response_model=AgentScoreResponse)
async def get_my_scores(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
):
    """
    Get current agent's relevance score statistics.
    
    Args:
        limit: Maximum number of recent scores to return (default: 10, max: 50)
    
    Returns:
        Average score and list of recent scores
    """
    from services.message_scoring_service import MessageScoringService
    
    scoring_service = MessageScoringService(db)
    
    average_score = scoring_service.get_agent_average_score(agent.id)
    recent_scores = scoring_service.get_agent_recent_scores(agent.id, limit=limit)
    
    return AgentScoreResponse(
        average_score=average_score,
        recent_scores=recent_scores
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


# Admin endpoints (no authentication required for monitoring purposes)

class AgentInfo(BaseModel):
    """Response model for agent information."""
    agent_id: str
    agent_name: str
    auth_token_hash: str
    created_at: str
    message_count: int


class AgentsListResponse(BaseModel):
    """Response model for agents list."""
    agents: list[AgentInfo]
    total: int


class TopicInfo(BaseModel):
    """Response model for topic information."""
    topic_id: str
    title: str
    status: str
    message_count: int
    created_at: str
    updated_at: str


class TopicsListResponse(BaseModel):
    """Response model for topics list."""
    topics: list[TopicInfo]
    total: int


@router.get("/admin/agents", response_model=AgentsListResponse)
async def admin_list_agents(db: Session = Depends(get_db)):
    """
    Admin endpoint: List all registered agents.
    No authentication required for monitoring purposes.
    
    Returns:
        List of all agents with their information
    """
    from models.models import Message
    from sqlalchemy import func
    
    # Get all agents with message counts
    agents_query = db.query(
        Agent,
        func.count(Message.id).label('message_count')
    ).outerjoin(
        Message, Agent.id == Message.agent_id
    ).group_by(Agent.id).all()
    
    agents_list = [
        AgentInfo(
            agent_id=agent.id,
            agent_name=agent.name,
            auth_token_hash=agent.auth_token_hash,
            created_at=agent.created_at.isoformat() + 'Z' if agent.created_at else "",
            message_count=message_count or 0
        )
        for agent, message_count in agents_query
    ]
    
    return AgentsListResponse(
        agents=agents_list,
        total=len(agents_list)
    )


@router.get("/admin/topics", response_model=TopicsListResponse)
async def admin_list_topics(
    status: Optional[str] = Query(None, description="Filter by status: active, closing_pending, closed"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: List all topics.
    No authentication required for monitoring purposes.
    
    Args:
        status: Optional status filter
        limit: Maximum number of topics to return
    
    Returns:
        List of topics with their information
    """
    from models.models import Topic, Message
    from sqlalchemy import func, desc
    
    # Build query
    query = db.query(
        Topic,
        func.count(Message.id).label('message_count')
    ).outerjoin(
        Message, Topic.id == Message.topic_id
    ).group_by(Topic.id)
    
    # Apply status filter if provided
    if status:
        query = query.filter(Topic.status == status)
    
    # Order by updated_at descending and limit
    topics_query = query.order_by(desc(Topic.updated_at)).limit(limit).all()
    
    topics_list = [
        TopicInfo(
            topic_id=topic.id,
            title=topic.title,
            status=topic.status,
            message_count=message_count or 0,
            created_at=topic.created_at.isoformat() + 'Z' if topic.created_at else "",
            updated_at=topic.updated_at.isoformat() + 'Z' if topic.updated_at else ""
        )
        for topic, message_count in topics_query
    ]
    
    return TopicsListResponse(
        topics=topics_list,
        total=len(topics_list)
    )


@router.get("/admin/topic/{topic_id}")
async def admin_get_topic_detail(
    topic_id: str,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Get detailed topic information.
    No authentication required for monitoring purposes.
    
    Args:
        topic_id: Topic ID
    
    Returns:
        Detailed topic information including description and scores
    """
    from models.models import MessageRelevanceScore
    from sqlalchemy import func
    
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic {topic_id} not found"
        )
    
    # Get message count
    message_count = db.query(func.count(Message.id)).filter(
        Message.topic_id == topic_id
    ).scalar() or 0
    
    # Get average relevance score
    avg_score = db.query(func.avg(MessageRelevanceScore.relevance_score)).filter(
        MessageRelevanceScore.topic_id == topic_id
    ).scalar()
    
    return {
        "topic_id": topic.id,
        "title": topic.title,
        "topic_description": topic.topic_description,
        "status": topic.status,
        "summary": topic.summary,
        "llm_suggestion": topic.llm_suggestion,
        "end_score": topic.end_score,
        "token_count_since_summary": topic.token_count_since_summary,
        "message_count": message_count,
        "average_relevance_score": float(avg_score) if avg_score else None,
        "created_at": topic.created_at.isoformat() + 'Z' if topic.created_at else None,
        "updated_at": topic.updated_at.isoformat() + 'Z' if topic.updated_at else None
    }


@router.put("/admin/topic/{topic_id}")
async def admin_update_topic(
    topic_id: str,
    request: UpdateTopicRequest,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Update topic information.
    No authentication required for monitoring purposes.
    
    Args:
        topic_id: Topic ID
        request: Update request with title and/or description
    
    Returns:
        Updated topic information
    """
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic {topic_id} not found"
        )
    
    # Update fields if provided
    if request.title is not None:
        topic.title = request.title
    if request.topic_description is not None:
        topic.topic_description = request.topic_description
    
    topic.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(topic)
    
    return {
        "status": "success",
        "message": "Topic updated successfully",
        "topic": {
            "topic_id": topic.id,
            "title": topic.title,
            "topic_description": topic.topic_description,
            "updated_at": topic.updated_at.isoformat()
        }
    }


@router.post("/admin/topic")
async def admin_create_topic(
    request: CreateTopicRequest,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Create a new topic.
    No authentication required for admin purposes.
    
    Args:
        request: Topic creation request with title and description
    
    Returns:
        Created topic information
    """
    topic_service = TopicService(db)
    
    # Validate title
    if not request.title or not request.title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title is required"
        )
    
    topic = topic_service.create_topic(
        title=request.title.strip(),
        topic_description=request.topic_description.strip() if request.topic_description else None
    )
    
    return {
        "status": "success",
        "message": "Topic created successfully",
        "topic": {
            "topic_id": topic.id,
            "title": topic.title,
            "topic_description": topic.topic_description,
            "status": topic.status,
            "created_at": topic.created_at.isoformat()
        }
    }


@router.delete("/admin/topic/{topic_id}")
async def admin_delete_topic(
    topic_id: str,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Delete a topic and all its messages.
    No authentication required for admin purposes.
    
    WARNING: This operation is irreversible and will delete all associated messages.
    
    Args:
        topic_id: Topic ID to delete
    
    Returns:
        Success message with deletion statistics
    """
    from models.models import MessageRelevanceScore, SummaryHistory
    from sqlalchemy import func
    
    # Check if topic exists
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic {topic_id} not found"
        )
    
    try:
        # Count messages before deletion
        message_count = db.query(func.count(Message.id)).filter(
            Message.topic_id == topic_id
        ).scalar() or 0
        
        # Delete related records in order (foreign key constraints)
        # 1. Delete message relevance scores
        db.query(MessageRelevanceScore).filter(
            MessageRelevanceScore.topic_id == topic_id
        ).delete(synchronize_session=False)
        
        # 2. Delete messages
        db.query(Message).filter(
            Message.topic_id == topic_id
        ).delete(synchronize_session=False)
        
        # 3. Delete summary history
        db.query(SummaryHistory).filter(
            SummaryHistory.topic_id == topic_id
        ).delete(synchronize_session=False)
        
        # 4. Delete the topic itself
        db.delete(topic)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Topic deleted successfully",
            "deleted": {
                "topic_id": topic_id,
                "title": topic.title,
                "messages_deleted": message_count
            }
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete topic: {str(e)}"
        )


@router.get("/admin/stats")
async def admin_get_stats(db: Session = Depends(get_db)):
    """
    Admin endpoint: Get platform statistics.
    No authentication required for monitoring purposes.
    
    Returns:
        Platform statistics including counts and metrics
    """
    from models.models import Topic, Message
    from sqlalchemy import func
    
    # Count agents
    agent_count = db.query(func.count(Agent.id)).scalar()
    
    # Count topics by status
    active_topics = db.query(func.count(Topic.id)).filter(Topic.status == "active").scalar()
    closing_topics = db.query(func.count(Topic.id)).filter(Topic.status == "closing_pending").scalar()
    closed_topics = db.query(func.count(Topic.id)).filter(Topic.status == "closed").scalar()
    total_topics = db.query(func.count(Topic.id)).scalar()
    
    # Count messages
    total_messages = db.query(func.count(Message.id)).scalar()
    
    # Get active topic info if exists
    active_topic = db.query(Topic).filter(Topic.status == "active").first()
    active_topic_info = None
    if active_topic:
        active_topic_info = {
            "topic_id": active_topic.id,
            "title": active_topic.title,
            "token_count": active_topic.token_count_since_summary,
            "end_score": active_topic.end_score,
            "llm_suggestion": active_topic.llm_suggestion
        }
    
    return {
        "agents": {
            "total": agent_count or 0
        },
        "topics": {
            "total": total_topics or 0,
            "active": active_topics or 0,
            "closing_pending": closing_topics or 0,
            "closed": closed_topics or 0
        },
        "messages": {
            "total": total_messages or 0
        },
        "active_topic": active_topic_info
    }


@router.get("/admin/config/api-key")
async def admin_get_api_key():
    """
    Admin endpoint: Get current DeepSeek API Key status.
    Returns masked key for security.
    
    Returns:
        API Key status and masked value
    """
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    
    # Check if key is configured
    is_configured = bool(api_key and api_key != "your_deepseek_api_key_here")
    
    # Mask the key for security (show first 8 and last 4 characters)
    masked_key = ""
    if is_configured and len(api_key) > 12:
        masked_key = api_key[:8] + "..." + api_key[-4:]
    elif is_configured:
        masked_key = api_key[:4] + "..."
    
    return {
        "is_configured": is_configured,
        "masked_key": masked_key if is_configured else None,
        "api_url": os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1"),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    }


@router.post("/admin/config/api-key")
async def admin_update_api_key(request: dict):
    """
    Admin endpoint: Update DeepSeek API Key in .env file.
    
    Args:
        request: {"api_key": "sk-xxx"}
    
    Returns:
        Success status and message
    """
    import os
    import re
    from pathlib import Path
    
    api_key = request.get("api_key", "").strip()
    
    # Validate API key format
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API Key cannot be empty"
        )
    
    if not api_key.startswith("sk-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API Key format (should start with 'sk-')"
        )
    
    if len(api_key) < 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API Key too short (invalid format)"
        )
    
    try:
        # Find .env file
        env_path = Path(".env")
        if not env_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=".env file not found"
            )
        
        # Read current .env content
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Update DEEPSEEK_API_KEY
        pattern = r"DEEPSEEK_API_KEY=.*"
        replacement = f"DEEPSEEK_API_KEY={api_key}"
        
        if re.search(pattern, content):
            # Replace existing key
            new_content = re.sub(pattern, replacement, content)
        else:
            # Append new key
            new_content = content.rstrip() + f"\n{replacement}\n"
        
        # Write back to .env
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        # Update environment variable for current process
        os.environ["DEEPSEEK_API_KEY"] = api_key
        
        return {
            "success": True,
            "message": "API Key updated successfully. Please restart Celery Worker to apply changes.",
            "restart_required": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update API Key: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update API Key: {str(e)}"
        )


# System Configuration Endpoints

class SystemConfigResponse(BaseModel):
    """Response model for system configuration."""
    key: str
    value: str
    config_type: str
    category: str
    display_name: str
    description: Optional[str]
    default_value: Optional[str]
    validation: Optional[str]
    options: Optional[str]
    display_order: int
    updated_at: Optional[str]


class UpdateConfigRequest(BaseModel):
    """Request model for updating configuration."""
    value: str


class UpdateMultipleConfigsRequest(BaseModel):
    """Request model for updating multiple configurations."""
    configs: dict[str, str]


@router.get("/admin/config/system")
async def get_system_configs(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Get all system configurations.
    No authentication required for monitoring purposes.
    
    Args:
        category: Optional category filter
    
    Returns:
        List of system configurations grouped by category
    """
    from services.system_config_service import SystemConfigService
    
    config_service = SystemConfigService(db)
    
    # Initialize defaults if not exists
    config_service.initialize_defaults()
    
    if category:
        configs = config_service.get_all_configs(category=category)
        return {
            "category": category,
            "configs": [
                SystemConfigResponse(
                    key=c.key,
                    value=c.value,
                    config_type=c.config_type,
                    category=c.category,
                    display_name=c.display_name,
                    description=c.description,
                    default_value=c.default_value,
                    validation=c.validation,
                    options=c.options,
                    display_order=c.display_order,
                    updated_at=c.updated_at.isoformat() if c.updated_at else None
                )
                for c in configs
            ]
        }
    else:
        configs_by_category = config_service.get_configs_by_category()
        return {
            "categories": {
                cat: [
                    SystemConfigResponse(
                        key=c.key,
                        value=c.value,
                        config_type=c.config_type,
                        category=c.category,
                        display_name=c.display_name,
                        description=c.description,
                        default_value=c.default_value,
                        validation=c.validation,
                        options=c.options,
                        display_order=c.display_order,
                        updated_at=c.updated_at.isoformat() if c.updated_at else None
                    )
                    for c in configs
                ]
                for cat, configs in configs_by_category.items()
            }
        }


@router.get("/admin/config/system/export")
async def export_system_configs(db: Session = Depends(get_db)):
    """
    Admin endpoint: Export all system configurations.
    No authentication required for monitoring purposes.
    
    Returns:
        All configurations as dictionary
    """
    from services.system_config_service import SystemConfigService
    
    config_service = SystemConfigService(db)
    configs = config_service.export_configs()
    
    return {
        "success": True,
        "configs": configs,
        "exported_at": datetime.utcnow().isoformat()
    }


@router.get("/admin/config/system/{key}")
async def get_system_config(
    key: str,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Get a specific system configuration.
    No authentication required for monitoring purposes.
    
    Args:
        key: Configuration key
    
    Returns:
        System configuration
    """
    from services.system_config_service import SystemConfigService
    
    config_service = SystemConfigService(db)
    config = config_service.get_config(key)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration key '{key}' not found"
        )
    
    return SystemConfigResponse(
        key=config.key,
        value=config.value,
        config_type=config.config_type,
        category=config.category,
        display_name=config.display_name,
        description=config.description,
        default_value=config.default_value,
        validation=config.validation,
        options=config.options,
        display_order=config.display_order,
        updated_at=config.updated_at.isoformat() if config.updated_at else None
    )


@router.put("/admin/config/system/{key}")
async def update_system_config(
    key: str,
    request: UpdateConfigRequest,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Update a system configuration.
    No authentication required for monitoring purposes.
    
    Args:
        key: Configuration key
        request: Update request with new value
    
    Returns:
        Updated configuration
    """
    from services.system_config_service import SystemConfigService
    
    try:
        config_service = SystemConfigService(db)
        config = config_service.update_config(key, request.value)
        
        return {
            "success": True,
            "message": f"Configuration '{key}' updated successfully",
            "config": SystemConfigResponse(
                key=config.key,
                value=config.value,
                config_type=config.config_type,
                category=config.category,
                display_name=config.display_name,
                description=config.description,
                default_value=config.default_value,
                validation=config.validation,
                options=config.options,
                display_order=config.display_order,
                updated_at=config.updated_at.isoformat() if config.updated_at else None
            )
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.post("/admin/config/system/batch")
async def update_multiple_configs(
    request: UpdateMultipleConfigsRequest,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Update multiple system configurations at once.
    No authentication required for monitoring purposes.
    
    Args:
        request: Update request with multiple key-value pairs
    
    Returns:
        List of updated configurations
    """
    from services.system_config_service import SystemConfigService
    
    try:
        config_service = SystemConfigService(db)
        updated_configs = config_service.update_multiple_configs(request.configs)
        
        return {
            "success": True,
            "message": f"Updated {len(updated_configs)} configurations",
            "configs": [
                SystemConfigResponse(
                    key=c.key,
                    value=c.value,
                    config_type=c.config_type,
                    category=c.category,
                    display_name=c.display_name,
                    description=c.description,
                    default_value=c.default_value,
                    validation=c.validation,
                    options=c.options,
                    display_order=c.display_order,
                    updated_at=c.updated_at.isoformat() if c.updated_at else None
                )
                for c in updated_configs
            ]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configurations: {str(e)}"
        )


@router.post("/admin/config/system/{key}/reset")
async def reset_system_config(
    key: str,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Reset a system configuration to default value.
    No authentication required for monitoring purposes.
    
    Args:
        key: Configuration key
    
    Returns:
        Reset configuration
    """
    from services.system_config_service import SystemConfigService
    
    try:
        config_service = SystemConfigService(db)
        config = config_service.reset_config(key)
        
        return {
            "success": True,
            "message": f"Configuration '{key}' reset to default value",
            "config": SystemConfigResponse(
                key=config.key,
                value=config.value,
                config_type=config.config_type,
                category=config.category,
                display_name=config.display_name,
                description=config.description,
                default_value=config.default_value,
                validation=config.validation,
                options=config.options,
                display_order=config.display_order,
                updated_at=config.updated_at.isoformat() if config.updated_at else None
            )
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset configuration: {str(e)}"
        )



@router.post("/admin/worker/restart")
async def restart_worker():
    """
    Admin endpoint: Restart Celery Worker.
    
    This endpoint triggers a restart of the Celery Worker process.
    Useful after changing LLM provider or API keys in system configuration.
    
    Returns:
        Success message and restart status
    """
    import subprocess
    import os
    
    try:
        # 优先使用快速重启脚本
        quick_script = "restart_worker_quick.sh"
        normal_script = "restart_worker.sh"
        
        if os.path.exists(quick_script):
            script_path = quick_script
            timeout = 5  # 快速脚本只需要 5 秒
        elif os.path.exists(normal_script):
            script_path = normal_script
            timeout = 20  # 普通脚本需要更长时间
        else:
            # 如果脚本都不存在，直接执行命令
            try:
                # 停止 Worker
                subprocess.run(
                    ["pkill", "-f", "celery -A workers.celery_app worker"],
                    timeout=3
                )
                # 等待一下
                import time
                time.sleep(1)
                # 启动 Worker（后台）
                subprocess.Popen(
                    ["celery", "-A", "workers.celery_app", "worker", 
                     "--loglevel=info", "--logfile=logs/worker.log"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return {
                    "success": True,
                    "message": "Worker restart initiated successfully (direct command)",
                    "note": "Worker is restarting. Please wait a few seconds for it to be ready."
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Failed to restart Worker: {str(e)}",
                    "manual_command": "pkill -f 'celery -A workers.celery_app worker' && celery -A workers.celery_app worker --loglevel=info --logfile=logs/worker.log &"
                }
        
        # 执行重启脚本
        result = subprocess.run(
            ["bash", script_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": "Worker restart initiated successfully",
                "output": result.stdout if result.stdout else "Restart initiated",
                "note": "Worker is restarting. Please wait a few seconds for it to be ready.",
                "script_used": script_path
            }
        else:
            return {
                "success": False,
                "message": "Worker restart failed",
                "error": result.stderr,
                "manual_command": "pkill -f 'celery -A workers.celery_app worker' && celery -A workers.celery_app worker --loglevel=info --logfile=logs/worker.log &"
            }
    
    except subprocess.TimeoutExpired:
        # 超时不一定是失败，Worker 可能正在后台启动
        return {
            "success": True,  # 改为 True，因为重启可能正在进行
            "message": "Worker restart initiated (background process)",
            "note": "The restart is in progress. Please wait 10-15 seconds and check Worker status.",
            "warning": "Restart command timed out, but Worker may still be starting in the background."
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to restart Worker: {str(e)}",
            "manual_command": "pkill -f 'celery -A workers.celery_app worker' && celery -A workers.celery_app worker --loglevel=info --logfile=logs/worker.log &"
        }


@router.get("/admin/worker/status")
async def get_worker_status():
    """
    Admin endpoint: Get Celery Worker status.
    
    Returns:
        Worker status information
    """
    import subprocess
    
    try:
        # Check if Worker process is running
        result = subprocess.run(
            ["pgrep", "-f", "celery.*worker"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            
            # Get process details
            processes = []
            for pid in pids:
                if pid:
                    ps_result = subprocess.run(
                        ["ps", "-p", pid, "-o", "pid,pcpu,pmem,etime"],
                        capture_output=True,
                        text=True
                    )
                    if ps_result.returncode == 0:
                        lines = ps_result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            processes.append(lines[1].strip())
            
            return {
                "running": True,
                "message": "Worker is running",
                "process_count": len(pids),
                "processes": processes
            }
        else:
            return {
                "running": False,
                "message": "Worker is not running",
                "process_count": 0
            }
    
    except Exception as e:
        return {
            "running": False,
            "message": f"Failed to check Worker status: {str(e)}",
            "error": str(e)
        }


@router.get("/admin/config/llm")
async def get_llm_config(db: Session = Depends(get_db)):
    """
    Admin endpoint: Get LLM configuration for simulators.
    Returns all available LLM provider settings from system configuration.

    This endpoint is used by simulators to get LLM configuration
    so they can use the same settings as the backend services.

    Returns:
        LLM configurations for all providers (DeepSeek and MiniMax)
    """
    from services.system_config_service import SystemConfigService

    config_service = SystemConfigService(db)

    # Get LLM provider for scoring (use as default)
    provider = config_service.get_config_value('llm_provider_scoring', 'deepseek')

    # Get API keys for both providers
    deepseek_key = config_service.get_config_value('deepseek_api_key', '')
    minimax_key = config_service.get_config_value('minimax_api_key', '')

    # Mask API keys for security
    def mask_key(key):
        if key and len(key) > 12:
            return key[:8] + "..." + key[-4:]
        elif key:
            return key[:4] + "..."
        return ""

    return {
        "provider": provider,  # Default provider
        "deepseek": {
            "api_key": deepseek_key,
            "masked_key": mask_key(deepseek_key),
            "api_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "is_configured": bool(deepseek_key)
        },
        "minimax": {
            "api_key": minimax_key,
            "masked_key": mask_key(minimax_key),
            "api_url": "https://api.minimax.chat/v1",
            "model": "MiniMax-M2.5",
            "is_configured": bool(minimax_key)
        },
        # 保留旧格式以兼容
        "api_key": deepseek_key if provider == 'deepseek' else minimax_key,
        "masked_key": mask_key(deepseek_key if provider == 'deepseek' else minimax_key),
        "api_url": "https://api.deepseek.com/v1" if provider == 'deepseek' else "https://api.minimax.chat/v1",
        "model": "deepseek-chat" if provider == 'deepseek' else "MiniMax-M2.5",
        "is_configured": bool(deepseek_key if provider == 'deepseek' else minimax_key)
    }


class LLMProxyRequest(BaseModel):
    """Request model for LLM proxy."""
    provider: str = Field(..., description="LLM provider: deepseek or minimax")
    messages: list[dict] = Field(..., description="Chat messages")
    temperature: float = Field(default=0.8, ge=0, le=2)
    max_tokens: int = Field(default=500, ge=1, le=4000)


@router.post("/admin/llm/proxy")
async def llm_proxy(
    request: LLMProxyRequest,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Proxy LLM API calls to avoid CORS issues.
    
    This endpoint allows frontend simulators to call LLM APIs through the backend,
    avoiding CORS restrictions. Supports both DeepSeek and MiniMax.
    
    Args:
        request: LLM proxy request with provider, messages, and parameters
    
    Returns:
        LLM API response with generated content
    """
    from services.system_config_service import SystemConfigService
    import requests
    
    config_service = SystemConfigService(db)
    
    # Get configuration for the requested provider
    if request.provider == 'deepseek':
        api_key = config_service.get_config_value('deepseek_api_key', '')
        api_url = config_service.get_config_value('deepseek_api_url', 'https://api.deepseek.com/v1')
        model = config_service.get_config_value('deepseek_model', 'deepseek-chat')
    elif request.provider == 'minimax':
        api_key = config_service.get_config_value('minimax_api_key', '')
        api_url = config_service.get_config_value('minimax_api_url', 'https://api.minimax.chat/v1')
        model = config_service.get_config_value('minimax_model', 'MiniMax-M2.5')
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {request.provider}"
        )
    
    # Check if API key is configured
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{request.provider.upper()} API Key not configured"
        )
    
    # Prepare request to LLM API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": request.messages,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens
    }
    
    # 重试配置
    max_retries = 5
    retry_delays = [1, 2, 4, 8, 12]  # 指数退避，MiniMax 500 错误需要更长间隔
    timeout = 60  # 超时时间 60 秒
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Call LLM API
            response = requests.post(
                f"{api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            # Handle rate limiting - 需要重试
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(f"{request.provider.upper()} rate limit, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"{request.provider.upper()} API rate limit exceeded"
                    )
            
            # Handle server errors (5xx) - 需要重试
            if 500 <= response.status_code < 600:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(f"{request.provider.upper()} server error {response.status_code}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    error_detail = response.text
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"{request.provider.upper()} API error: {error_detail}"
                    )
            
            # Handle other errors - 不重试
            if response.status_code != 200:
                error_detail = response.text
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"{request.provider.upper()} API error: {error_detail}"
                )
            
            # Return the response
            data = response.json()
            
            # Extract content
            if "choices" not in data or not data["choices"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Invalid response format from LLM API"
                )
            
            content = data["choices"][0].get("message", {}).get("content", "")
            
            # 过滤 MiniMax 的思考过程标签
            if request.provider == 'minimax':
                import re
                # 移除 <think>...</think> 标签及其内容
                content = re.sub(r'<think>[\s\S]*?</think>', '', content, flags=re.IGNORECASE).strip()
                
                # 如果过滤后为空，记录警告并返回原始内容
                if not content:
                    logger.warning(f"MiniMax response was completely filtered, returning original")
                    content = data["choices"][0].get("message", {}).get("content", "")
            
            return {
                "success": True,
                "provider": request.provider,
                "content": content,
                "usage": data.get("usage", {}),
                "attempts": attempt + 1  # 返回尝试次数
            }
        
        except HTTPException:
            raise
        except requests.Timeout:
            if attempt < max_retries - 1:
                delay = retry_delays[attempt]
                logger.warning(f"{request.provider.upper()} timeout, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                last_error = f"{request.provider.upper()} API request timed out after {timeout}s"
                continue
            else:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"{request.provider.upper()} API request timed out after {max_retries} attempts"
                )
        
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                delay = retry_delays[attempt]
                logger.warning(f"{request.provider.upper()} request failed, retrying in {delay}s (attempt {attempt + 1}/{max_retries}): {str(e)}")
                time.sleep(delay)
                last_error = str(e)
                continue
            else:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"{request.provider.upper()} API request failed: {str(e)}"
                )
        except Exception as e:
            logger.error(f"LLM proxy error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to proxy LLM request: {str(e)}"
            )




@router.get("/admin/scoring/stats")
async def get_scoring_stats(db: Session = Depends(get_db)):
    """
    Admin endpoint: Get scoring system statistics and diagnostics.
    Returns overall stats, recent scoring activity, and system health info.
    """
    from models.models import MessageRelevanceScore
    from services.system_config_service import SystemConfigService
    from sqlalchemy import func, desc, and_
    from datetime import timedelta

    config_service = SystemConfigService(db)
    now = datetime.utcnow()

    # 1. Overall stats
    total_messages = db.query(func.count(Message.id)).scalar() or 0
    total_scores = db.query(func.count(MessageRelevanceScore.id)).scalar() or 0

    # 2. Recent activity (last 1 hour)
    one_hour_ago = now - timedelta(hours=1)
    recent_messages = db.query(func.count(Message.id)).filter(
        Message.created_at >= one_hour_ago
    ).scalar() or 0
    recent_scores = db.query(func.count(MessageRelevanceScore.id)).filter(
        MessageRelevanceScore.evaluated_at >= one_hour_ago
    ).scalar() or 0

    # 3. Average score
    avg_score = db.query(func.avg(MessageRelevanceScore.relevance_score)).scalar()

    # 4. Recent 20 messages with scoring status
    recent_msgs = db.query(
        Message.id,
        Message.content,
        Message.created_at,
        Message.agent_id,
        MessageRelevanceScore.relevance_score,
        MessageRelevanceScore.evaluation_comment,
        MessageRelevanceScore.evaluated_at
    ).outerjoin(
        MessageRelevanceScore, Message.id == MessageRelevanceScore.message_id
    ).order_by(desc(Message.created_at)).limit(20).all()

    # Get agent names
    agent_ids = list(set(m.agent_id for m in recent_msgs))
    agents = db.query(Agent).filter(Agent.id.in_(agent_ids)).all() if agent_ids else []
    agent_map = {a.id: a.name for a in agents}

    messages_list = []
    for m in recent_msgs:
        scored = m.relevance_score is not None
        delay = None
        if scored and m.evaluated_at and m.created_at:
            delay = round((m.evaluated_at - m.created_at).total_seconds(), 1)
        messages_list.append({
            "message_id": m.id,
            "agent_name": agent_map.get(m.agent_id, m.agent_id),
            "content": m.content[:80] + "..." if len(m.content) > 80 else m.content,
            "created_at": m.created_at.isoformat() + "Z" if m.created_at else None,
            "scored": scored,
            "score": m.relevance_score,
            "comment": m.evaluation_comment[:60] + "..." if m.evaluation_comment and len(m.evaluation_comment) > 60 else m.evaluation_comment,
            "evaluated_at": m.evaluated_at.isoformat() + "Z" if m.evaluated_at else None,
            "delay_seconds": delay
        })

    # 5. Scoring config
    provider = config_service.get_config_value('llm_provider_scoring', 'deepseek')
    if provider == 'minimax':
        api_key = config_service.get_config_value('minimax_api_key', '')
        model = config_service.get_config_value('minimax_model', 'MiniMax-M2.5')
    else:
        api_key = config_service.get_config_value('deepseek_api_key', '')
        model = config_service.get_config_value('deepseek_model', 'deepseek-chat')

    # 6. Celery worker status
    worker_online = False
    try:
        from workers.celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=2)
        active = inspector.active()
        worker_online = bool(active)
    except Exception:
        pass

    # 7. Unscored count
    unscored_count = db.query(func.count(Message.id)).outerjoin(
        MessageRelevanceScore, Message.id == MessageRelevanceScore.message_id
    ).filter(MessageRelevanceScore.id == None).scalar() or 0

    return {
        "total_messages": total_messages,
        "total_scores": total_scores,
        "coverage_percent": round(total_scores / total_messages * 100, 1) if total_messages > 0 else 0,
        "unscored_count": unscored_count,
        "recent_1h_messages": recent_messages,
        "recent_1h_scores": recent_scores,
        "recent_1h_coverage": round(recent_scores / recent_messages * 100, 1) if recent_messages > 0 else 0,
        "average_score": round(avg_score, 1) if avg_score else None,
        "config": {
            "provider": provider,
            "model": model,
            "api_key_configured": bool(api_key),
            "api_key_preview": api_key[:8] + "..." if api_key else ""
        },
        "worker_online": worker_online,
        "messages": messages_list
    }


@router.post("/admin/scoring/retry")
async def retry_unscored_messages(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Retry scoring for recent unscored messages.
    Enqueues Celery tasks for messages that don't have scores yet.
    """
    from models.models import MessageRelevanceScore
    from sqlalchemy import desc

    # Find recent unscored messages
    unscored = db.query(Message).outerjoin(
        MessageRelevanceScore, Message.id == MessageRelevanceScore.message_id
    ).filter(
        MessageRelevanceScore.id == None
    ).order_by(desc(Message.created_at)).limit(limit).all()

    if not unscored:
        return {"retried": 0, "message": "没有未评分的消息"}

    # Enqueue scoring tasks
    from workers.tasks import evaluate_message_relevance
    count = 0
    for msg in unscored:
        try:
            evaluate_message_relevance.delay(
                message_id=msg.id,
                topic_id=msg.topic_id,
                agent_id=msg.agent_id,
                content=msg.content
            )
            count += 1
        except Exception:
            pass

    return {"retried": count, "message": f"已提交 {count} 条消息重新评分"}


@router.post("/admin/scoring/test")
async def test_scoring_api(db: Session = Depends(get_db)):
    """
    Admin endpoint: Test the scoring LLM API connectivity.
    Makes a simple test call to verify the configured provider works.
    """
    from services.system_config_service import SystemConfigService
    from services.llm_clients import MiniMaxClient, DeepSeekClient
    import time as _time

    config_service = SystemConfigService(db)
    provider = config_service.get_config_value('llm_provider_scoring', 'deepseek')

    test_prompt = """请对以下发言评分。返回JSON格式（只返回JSON）：
{"relevance_score": 85, "evaluation_comment": "测试评语"}

话题：测试话题
发言：这是一条测试消息。"""

    start = _time.time()
    try:
        if provider == 'minimax':
            api_key = config_service.get_config_value('minimax_api_key', '')
            api_url = config_service.get_config_value('minimax_api_url', 'https://api.minimax.chat/v1')
            model = config_service.get_config_value('minimax_model', 'MiniMax-M2.5')
            client = MiniMaxClient(api_key=api_key, api_url=api_url, model=model, max_retries=1)
        else:
            api_key = config_service.get_config_value('deepseek_api_key', '')
            api_url = config_service.get_config_value('deepseek_api_url', 'https://api.deepseek.com/v1')
            model = config_service.get_config_value('deepseek_model', 'deepseek-chat')
            client = DeepSeekClient(api_key=api_key, api_url=api_url, model=model, max_retries=1)

        if not api_key:
            return {"success": False, "error": f"{provider} API Key 未配置", "duration_ms": 0}

        result = client.evaluate_message_relevance(test_prompt)
        duration = round((_time.time() - start) * 1000)

        if result:
            return {
                "success": True,
                "provider": provider,
                "model": model,
                "result": result,
                "duration_ms": duration
            }
        else:
            return {"success": False, "error": "API 返回空结果", "duration_ms": duration}

    except Exception as e:
        duration = round((_time.time() - start) * 1000)
        return {"success": False, "error": str(e), "duration_ms": duration}
