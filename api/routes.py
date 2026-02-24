"""API routes for the Dual Agent Chat Platform."""
from datetime import datetime
from typing import Optional
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
