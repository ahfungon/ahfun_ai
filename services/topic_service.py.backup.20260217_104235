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
            domains = [
                "量子计算、生物技术、纳米材料",
                "人工智能、机器学习、神经网络",
                "区块链、Web3、去中心化",
                "太空探索、火星殖民、卫星技术",
                "基因编辑、精准医疗、抗衰老",
                "元宇宙、虚拟现实、数字孪生",
                "清洁能源、核聚变、氢能源",
                "自动驾驶、智能交通、城市规划",
                "远程医疗、心理健康、数字疗法",
                "教育科技、在线学习、知识图谱",
                "循环经济、可持续发展、碳交易",
                "数字货币、央行CBDC、金融科技",
                "隐私计算、联邦学习、数据主权",
                "合成生物学、人造肉、生物材料",
                "脑机接口、神经科技、意识研究"
            ]
            
            selected_domain = random.choice(domains)
            
            prompt = f"""你是一个话题生成助手。请生成一个适合AI智能体讨论的话题。

核心要求：
1. 话题必须具有原创性和创新性，避免陈词滥调
2. 话题应该跨学科融合，产生新颖的思考角度
3. 话题应该有深度，能够引发多角度的讨论
4. 话题应该具有时效性或前瞻性
5. 避免过于宽泛或过于狭窄的话题

本次话题建议领域（可以创新组合或延伸）：{selected_domain}

话题创新方向参考：
- 跨领域融合：将两个看似无关的领域结合
- 未来场景：设想5-10年后的技术应用场景
- 伦理困境：探讨新技术带来的道德两难
- 社会影响：分析技术对社会结构的深层改变
- 监管挑战：讨论新兴技术的治理难题
- 经济模式：探索新技术催生的商业模式
- 文化冲突：分析技术与传统文化的碰撞

请以JSON格式返回，包含以下字段：
{{
    "title": "话题标题（10-30字，要有创意和独特性，避免使用常见套路）",
    "description": "话题描述（50-150字，说明讨论范围和关键问题）"
}}

重要提示：
- 请确保生成的话题与常见话题有明显区别
- 标题要吸引人，避免使用"XXX的XXX"这种固定模式
- 展现创新思维和独特视角"""
            
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
