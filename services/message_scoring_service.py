"""Message scoring service for evaluating message relevance."""
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from models.models import MessageRelevanceScore, Message, Topic, Agent
from services.llm_clients import DeepSeekClient, MiniMaxClient
from services.system_config_service import SystemConfigService
from config.settings import settings

logger = logging.getLogger(__name__)


class MessageScoringService:
    """Service for scoring message relevance using DeepSeek LLM."""
    
    def __init__(self, db: Session):
        """
        Initialize MessageScoringService.
        
        Args:
            db: Database session
        """
        self.db = db
        self.config_service = SystemConfigService(db)
        
        # Get LLM provider from system config
        provider = self.config_service.get_config_value('llm_provider_scoring', 'deepseek')
        
        logger.info(f"[MessageScoringService] Initializing with LLM provider: {provider}")
        
        if provider == 'minimax':
            # Initialize MiniMax client
            api_key = self.config_service.get_config_value('minimax_api_key', '')
            api_url = self.config_service.get_config_value('minimax_api_url', 'https://api.minimax.io/v1')
            model = self.config_service.get_config_value('minimax_model', 'MiniMax-M2.5')
            
            self.llm_client = MiniMaxClient(
                api_key=api_key,
                api_url=api_url,
                model=model
            )
            self.llm_provider = 'MiniMax'
        else:
            # Initialize DeepSeek client (default)
            api_key = self.config_service.get_config_value('deepseek_api_key', settings.deepseek_api_key)
            api_url = self.config_service.get_config_value('deepseek_api_url', settings.deepseek_api_url)
            model = self.config_service.get_config_value('deepseek_model', settings.deepseek_model)
            
            self.llm_client = DeepSeekClient(
                api_key=api_key,
                api_url=api_url,
                model=model
            )
            self.llm_provider = 'DeepSeek'
    
    def evaluate_message(
        self,
        message_id: str,
        topic_id: str,
        agent_id: str,
        content: str
    ) -> Optional[MessageRelevanceScore]:
        """
        Evaluate a message relevance to the topic using DeepSeek LLM.
        
        This method is designed to be called asynchronously and will not raise
        exceptions on failure (returns None instead).
        
        Args:
            message_id: ID of the message to evaluate
            topic_id: ID of the topic
            agent_id: ID of the agent who sent the message
            content: Message content
        
        Returns:
            MessageRelevanceScore object if successful, None if failed
        """
        try:
            # Get topic information
            topic = self.db.query(Topic).filter(Topic.id == topic_id).first()
            if not topic:
                logger.error(f"Topic {topic_id} not found for message scoring")
                return None
            
            # Get agent name
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            agent_name = agent.name if agent else agent_id
            
            # Build evaluation prompt
            prompt = self._build_evaluation_prompt(
                topic_title=topic.title,
                topic_description=topic.topic_description or "",
                summary=topic.summary or "",
                agent_name=agent_name,
                message_content=content
            )
            
            # Call LLM (DeepSeek or MiniMax based on config)
            logger.info(f"[MessageScoringService] Evaluating message {message_id} using {self.llm_provider}")
            result = self.llm_client.evaluate_message_relevance(prompt)
            
            if not result:
                logger.warning(f"{self.llm_provider} returned empty result for message {message_id}")
                return None
            
            # Create score record
            score = MessageRelevanceScore(
                id=str(uuid.uuid4()),
                message_id=message_id,
                topic_id=topic_id,
                agent_id=agent_id,
                relevance_score=result.get("relevance_score", 0.0),
                evaluation_comment=result.get("evaluation_comment", ""),
                evaluated_at=datetime.utcnow()
            )
            
            self.db.add(score)
            self.db.commit()
            self.db.refresh(score)
            
            logger.info(f"Message {message_id} scored: {score.relevance_score}")
            return score
        
        except Exception as e:
            logger.error(f"Failed to evaluate message {message_id}: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def _build_evaluation_prompt(
        self,
        topic_title: str,
        topic_description: str,
        summary: str,
        agent_name: str,
        message_content: str
    ) -> str:
        """Build evaluation prompt for LLM (DeepSeek or MiniMax)."""
        # Try to get custom prompt from system config
        custom_prompt = self.config_service.get_config_value('scoring_prompt', None)
        
        if custom_prompt:
            # Use custom prompt template with variable substitution
            try:
                return custom_prompt.format(
                    topic_title=topic_title,
                    topic_description=topic_description if topic_description else "（无详细描述）",
                    current_summary=summary if summary else "（讨论刚开始，暂无总结）",
                    message_content=message_content
                )
            except KeyError as e:
                logger.warning(f"Custom scoring prompt has invalid placeholder: {e}, using default")
        
        # Default prompt
        prompt = f"""你是一个主题相关性评估专家。请评估以下发言与主题的相关性。

【主题】
标题：{topic_title}
描述：{topic_description if topic_description else "（无详细描述）"}

【历史总结】
{summary if summary else "（讨论刚开始，暂无总结）"}

【当前发言】
发言者：{agent_name}
内容：{message_content}

请从以下维度进行综合评分（0-100分）：
1. 主题相关性（40%）：是否紧扣主题核心，是否偏离讨论范围
2. 内容质量（30%）：论述是否清晰、有深度、有见地
3. 讨论推进（30%）：是否推动讨论向前发展，是否提出新观点或问题

返回JSON格式（只返回JSON，不要其他文字）：
{{
  "relevance_score": 85,
  "evaluation_comment": "紧扣主题，提出了新的视角"
}}"""
        
        return prompt
    
    def get_message_score(self, message_id: str) -> Optional[MessageRelevanceScore]:
        """Get the relevance score for a message."""
        return self.db.query(MessageRelevanceScore).filter(
            MessageRelevanceScore.message_id == message_id
        ).first()
    
    def get_agent_recent_scores(
        self,
        agent_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent scores for an agent."""
        scores = self.db.query(
            MessageRelevanceScore, Message
        ).join(
            Message, MessageRelevanceScore.message_id == Message.id
        ).filter(
            MessageRelevanceScore.agent_id == agent_id
        ).order_by(
            MessageRelevanceScore.evaluated_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "message_id": score.message_id,
                "score": score.relevance_score,
                "comment": score.evaluation_comment,
                "content": message.content[:100] + "..." if len(message.content) > 100 else message.content,
                "evaluated_at": score.evaluated_at.isoformat()
            }
            for score, message in scores
        ]
    
    def get_agent_average_score(self, agent_id: str) -> Optional[float]:
        """Get average score for an agent."""
        from sqlalchemy import func
        
        result = self.db.query(
            func.avg(MessageRelevanceScore.relevance_score)
        ).filter(
            MessageRelevanceScore.agent_id == agent_id
        ).scalar()
        
        return float(result) if result else None
