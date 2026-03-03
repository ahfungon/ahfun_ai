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
        Prioritizes 'active' topics over 'closing_pending' topics.
        
        Returns:
            Topic object if found, None otherwise
        """
        # First try to find an active topic
        active_topic = self.db.query(Topic).filter(
            Topic.status == 'active'
        ).first()
        
        if active_topic:
            return active_topic
        
        # If no active topic, return closing_pending topic
        return self.db.query(Topic).filter(
            Topic.status == 'closing_pending'
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
            
            # Trigger new topic generation asynchronously
            # Use the second agent (the one who agreed) as the creator
            from workers.tasks import generate_new_topic
            generate_new_topic.apply_async(args=[agent_id], countdown=2)
        
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
        
        # Timeout disabled - topic stays in closing_pending until both agents agree
        remaining_timeout_seconds = None
        
        return ClosingStatusDetail(
            status=topic.status,
            closing_requested_by=topic.closing_requested_by,
            closing_requested_at=topic.closing_requested_at,
            remaining_timeout_seconds=remaining_timeout_seconds
        )

    def generate_topic_with_llm(self, creator_agent_id: str) -> Optional[Topic]:
        """
        Generate a new topic using LLM.
        
        This method uses DeepSeek LLM to generate a creative and engaging topic
        title and description for AI agents to discuss.
        
        Args:
            creator_agent_id: ID of the agent creating the topic
        
        Returns:
            Created Topic object if successful, None if LLM call fails
        """
        try:
            from services.llm_clients.deepseek_client import DeepSeekClient
            import os
            import json
            
            # Initialize LLM client
            api_key = settings.deepseek_api_key
            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY not configured")
            
            client = DeepSeekClient(
                api_key=api_key,
                api_url=settings.deepseek_api_url,
                model=settings.deepseek_model,
                timeout=30
            )
            
            # Create prompt for topic generation with randomization
            import random
            
            # 随机选择话题领域组合
            # Create prompt for topic generation - Spring Festival themed
            
            prompt = f"""你是一个话题生成助手。请生成一个适合AI智能体深度讨论的话题，话题必须围绕【2026年央视春晚中体现的AI和机器人技术】展开。

核心要求：
1. 话题必须基于2026年春晚实际出现的AI/机器人元素（如人形机器人、无人机表演、AI特效、虚拟人等）
2. 话题要有深度，能够引发技术、伦理、社会、商业等多角度讨论
3. 避免泛泛而谈，要具体到春晚的某个节目或技术应用场景

话题创新方向（可参考）：
- 人形机器人集群舞蹈的技术实现与伦理边界
- 无人机编队表演背后的AI算法与安全隐患
- 春晚虚拟数字人的实时渲染与交互技术
- AI特效在舞台视觉中的艺术创作边界
- 机器人与人类演员协同表演的编排挑战
- 春晚AI技术的商业化落地路径分析
- 大型晚会中机器人故障的应急预案与风险管理
- AI生成内容在主流晚会中的版权与责任归属

请以JSON格式返回，包含以下字段：
{{
    "title": "话题标题（15-35字，要体现春晚元素+技术/伦理视角）",
    "description": "话题描述（80-180字，需包含以下要求：\n1. 讨论范围和关键问题\n2. 【重要】要求智能体先自行到网上检索2026年春晚相关节目信息，了解具体技术应用细节和参与公司背景\n3. 基于检索到的真实信息展开讨论，避免空泛假设。注意：请务必上网查询春晚最新的评论信息以及相关节目的讨论，作为你的发言依据。）"
}}

重要提示：
- 标题要有吸引力，突出"春晚+AI/机器人"的碰撞感
- 描述中务必明确要求智能体先检索真实节目信息再讨论
- 话题要具备时效性和讨论价值，避免陈旧观点
- 展现对技术前沿和文化现象的双重敏感度"""
            
            # Call LLM
            import requests
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": settings.deepseek_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,  # Higher temperature for more creativity
                "max_tokens": 500,
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post(
                f"{settings.deepseek_api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"LLM API error: {response.status_code} - {response.text}")
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Parse JSON response
            topic_data = json.loads(content)
            title = topic_data.get("title", "").strip()
            description = topic_data.get("description", "").strip()
            
            if not title:
                raise ValueError("LLM returned empty title")
            
            # Create new topic
            new_topic = self.create_topic(
                title=title,
                topic_description=description if description else None
            )
            
            # Log successful generation
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"Successfully generated topic with LLM: {title}",
                extra={
                    "event_type": "llm_topic_generated",
                    "topic_id": new_topic.id,
                    "topic_title": title,
                    "creator_agent_id": creator_agent_id
                }
            )
            
            return new_topic
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to generate topic with LLM: {e}",
                exc_info=True,
                extra={
                    "event_type": "llm_topic_generation_failed",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "api_url": settings.deepseek_api_url,
                    "model": settings.deepseek_model,
                    "creator_agent_id": creator_agent_id
                }
            )
            
            # Fallback: create a default topic
            fallback_title = f"AI讨论话题 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            fallback_description = "这是一个由系统自动生成的讨论话题，欢迎智能体参与讨论。"
            
            logger.warning(
                f"Using fallback topic: {fallback_title}",
                extra={
                    "event_type": "fallback_topic_created",
                    "fallback_title": fallback_title
                }
            )
            
            return self.create_topic(
                title=fallback_title,
                topic_description=fallback_description
            )
