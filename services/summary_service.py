"""Summary service for generating and managing conversation summaries."""
import uuid
import json
import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.models import Topic, Message, SummaryHistory
from models.database import transaction, atomic_update
from config.settings import settings
from utils.logging_config import log_llm_call, log_error_with_context
from services.llm_clients import DeepSeekClient, MiniMaxClient, LLMClientError
from services.system_config_service import SystemConfigService

# Configure logging
logger = logging.getLogger(__name__)


class SummaryResult:
    """Data class for summary generation result."""
    
    def __init__(self, summary: str, suggestion: str, end_score: float):
        """
        Initialize SummaryResult.
        
        Args:
            summary: Generated summary text
            suggestion: LLM suggestion (continue/change_angle/suggest_end/force_end)
            end_score: End score from 0-100
        """
        self.summary = summary
        self.suggestion = suggestion
        self.end_score = end_score


class SummaryService:
    """Service for generating and managing conversation summaries."""
    
    def __init__(self, db: Session, deepseek_client: Optional[DeepSeekClient] = None):
        """
        Initialize SummaryService.
        
        Args:
            db: Database session
            deepseek_client: DeepSeek client instance (optional, deprecated - will use system config)
        """
        self.db = db
        self.config_service = SystemConfigService(db)
        
        # Get LLM provider from system config
        provider = self.config_service.get_config_value('llm_provider_summary', 'deepseek')
        
        logger.info(f"[SummaryService] Initializing with LLM provider: {provider}")
        
        # Initialize LLM client based on config
        if deepseek_client is not None:
            # Legacy: use provided client
            self.llm_client = deepseek_client
            self.llm_provider = 'DeepSeek (legacy)'
        elif provider == 'minimax':
            # Initialize MiniMax client
            api_key = self.config_service.get_config_value('minimax_api_key', '')
            api_url = self.config_service.get_config_value('minimax_api_url', 'https://api.minimax.chat/v1')
            model = self.config_service.get_config_value('minimax_model', 'abab6.5-chat')
            
            self.llm_client = MiniMaxClient(
                api_key=api_key,
                api_url=api_url,
                timeout=30,
                max_retries=3,
                retry_delays=[1, 2, 4],
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
                timeout=30,
                max_retries=3,
                retry_delays=[1, 2, 4],
                model=model
            )
            self.llm_provider = 'DeepSeek'
    
    def generate_summary(
        self,
        topic: Topic,
        new_messages: List[Message]
    ) -> SummaryResult:
        """
        Generate a new cumulative summary using configured LLM (DeepSeek or MiniMax).

        This method constructs a prompt with the old summary and new messages,
        calls the configured LLM, and parses the response to extract the summary,
        suggestion, and end_score.

        Args:
            topic: Topic object containing old summary
            new_messages: List of new messages since last summary

        Returns:
            SummaryResult containing summary, suggestion, and end_score

        Raises:
            Exception: If LLM API call fails
        """
        # Build prompt
        prompt = self._build_summary_prompt(topic.summary, new_messages)

        # Prepare request parameters for logging
        request_params = {
            "topic_id": topic.id,
            "old_summary_length": len(topic.summary) if topic.summary else 0,
            "new_messages_count": len(new_messages),
            "prompt_length": len(prompt),
            "llm_provider": self.llm_provider
        }

        # Call LLM API with timing and logging
        start_time = time.time()
        try:
            logger.info(f"[SummaryService] Generating summary for topic {topic.id} using {self.llm_provider}")
            llm_response = self._call_llm_api(prompt)
            duration_ms = (time.time() - start_time) * 1000

            # Log successful LLM call
            log_llm_call(
                logger,
                provider=self.llm_provider,
                operation="generate_summary",
                request_params=request_params,
                response=llm_response,
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Log failed LLM call
            log_llm_call(
                logger,
                provider=self.llm_provider,
                operation="generate_summary",
                request_params=request_params,
                error=e,
                duration_ms=duration_ms
            )
            raise

        # Parse LLM response
        summary, suggestion, end_score = self._parse_llm_response(llm_response)

        return SummaryResult(
            summary=summary,
            suggestion=suggestion,
            end_score=end_score
        )

    
    def update_topic_summary(
        self,
        topic_id: str,
        summary: str,
        suggestion: str,
        end_score: float
    ) -> None:
        """
        Update topic's summary, suggestion, and end score atomically.
        
        Uses database transaction to ensure atomic update of all fields.
        
        Args:
            topic_id: ID of the topic to update
            summary: New summary text
            suggestion: LLM suggestion
            end_score: End score (0-100)
        
        Raises:
            ValueError: If topic not found
            
        Validates:
            Requirements 6.7, 10.1, 10.2, 10.4
        """
        with atomic_update(self.db, Topic, topic_id) as topic:
            topic.summary = summary
            topic.llm_suggestion = suggestion
            topic.end_score = end_score
            topic.updated_at = datetime.utcnow()
    
    def save_summary_history(
        self,
        topic_id: str,
        summary: str,
        suggestion: str,
        end_score: float
    ) -> SummaryHistory:
        """
        Save a summary history record atomically.
        
        Uses database transaction to ensure atomic insert.
        
        Args:
            topic_id: ID of the topic
            summary: Summary text
            suggestion: LLM suggestion
            end_score: End score (0-100)
        
        Returns:
            Created SummaryHistory object
            
        Validates:
            Requirements 11.1, 11.2, 10.1, 10.2
        """
        with transaction(self.db):
            history = SummaryHistory(
                id=str(uuid.uuid4()),
                topic_id=topic_id,
                summary=summary,
                llm_suggestion=suggestion,
                end_score=end_score,
                created_at=datetime.utcnow()
            )
            
            self.db.add(history)
        
        self.db.refresh(history)
        return history
    
    def get_summary_history(
        self,
        topic_id: str,
        limit: int = 10
    ) -> List[SummaryHistory]:
        """
        Get historical summary versions for a topic.
        
        Args:
            topic_id: ID of the topic
            limit: Maximum number of history records to return
        
        Returns:
            List of SummaryHistory objects, newest first
        """
        return self.db.query(SummaryHistory).filter(
            SummaryHistory.topic_id == topic_id
        ).order_by(
            SummaryHistory.created_at.desc()
        ).limit(limit).all()
    
    def rollback_summary(self, topic_id: str, history_id: str) -> None:
        """
        Rollback topic summary to a historical version atomically.
        
        This method restores the topic's summary, suggestion, and end_score
        from a historical record. Uses transaction to ensure atomicity.
        Note: last_summarized_message_id should be updated by the caller if needed.
        
        Args:
            topic_id: ID of the topic
            history_id: ID of the history record to restore
        
        Raises:
            ValueError: If topic or history not found, or history doesn't belong to topic
            
        Validates:
            Requirements 11.5, 10.1, 10.2, 10.4
        """
        with transaction(self.db):
            # Get topic with row lock
            topic = self.db.query(Topic).filter(
                Topic.id == topic_id
            ).with_for_update().first()
            
            if not topic:
                raise ValueError(f"Topic {topic_id} not found")
            
            # Get history record
            history = self.db.query(SummaryHistory).filter(
                SummaryHistory.id == history_id
            ).first()
            
            if not history:
                raise ValueError(f"History {history_id} not found")
            
            if history.topic_id != topic_id:
                raise ValueError(f"History {history_id} does not belong to topic {topic_id}")
            
            # Restore from history
            topic.summary = history.summary
            topic.llm_suggestion = history.llm_suggestion
            topic.end_score = history.end_score
            topic.updated_at = datetime.utcnow()
    
    def apply_llm_suggestion(self, topic: Topic, suggestion: str) -> None:
        """
        Apply LLM suggestion logic to topic atomically.
        
        Currently handles force_end by setting topic to closing_pending.
        Other suggestions (continue, change_angle, suggest_end) are informational only.
        Uses transaction to ensure atomic status update.
        
        When topic is in closing_pending state, ignores new LLM suggestions
        until status returns to active (Requirement 7.8).
        
        Args:
            topic: Topic object to apply suggestion to
            suggestion: LLM suggestion to apply
            
        Validates:
            Requirements 7.5, 7.8, 10.1, 10.2
        """
        # Ignore new LLM suggestions when in closing_pending state (Requirement 7.8)
        if topic.status == "closing_pending":
            return
        
        if suggestion == "force_end":
            # Automatically set topic to closing_pending
            with transaction(self.db):
                topic.status = "closing_pending"
                topic.closing_requested_by = "system"  # System-initiated close
                topic.closing_requested_at = datetime.utcnow()
                topic.updated_at = datetime.utcnow()
    
    def _build_summary_prompt(
        self,
        old_summary: str,
        new_messages: List[Message]
    ) -> str:
        """
        Build prompt for LLM summary generation (DeepSeek or MiniMax).
        
        Args:
            old_summary: Previous cumulative summary
            new_messages: New messages to summarize
        
        Returns:
            Formatted prompt string
        """
        # Try to get custom prompt from system config
        custom_prompt = self.config_service.get_config_value('summary_prompt', None)
        
        # Format messages
        formatted_messages = []
        for msg in new_messages:
            formatted_messages.append(f"[{msg.agent_id}]: {msg.content}")
        
        messages_text = "\n".join(formatted_messages)
        
        if custom_prompt:
            # Use custom prompt template with variable substitution
            try:
                return custom_prompt.format(
                    previous_summary=old_summary if old_summary else "（暂无历史总结）",
                    new_messages=messages_text
                )
            except KeyError as e:
                logger.warning(f"Custom summary prompt has invalid placeholder: {e}, using default")
        
        # Default prompt
        prompt = f"""你是一个对话总结助手。请将以下内容压缩为简洁的中文摘要。

【历史总结】
{old_summary if old_summary else "（暂无历史总结）"}

【新对话内容】
{messages_text}

请提供：
1. 更新后的累积总结（保留关键信息，用中文表达）
2. 对话建议（continue/change_angle/suggest_end/force_end）
   - continue: 继续当前话题
   - change_angle: 建议换个角度讨论
   - suggest_end: 建议结束话题
   - force_end: 强制结束话题
3. 结束评分（0-100分，分数越高表示越建议结束）

请以 json 格式返回（summary 必须用中文）：
{{
    "summary": "你的中文总结内容",
    "suggestion": "continue|change_angle|suggest_end|force_end",
    "end_score": 0-100
}}"""
        
        return prompt
    
    def _call_llm_api(self, prompt: str) -> Dict[str, Any]:
        """
        Call configured LLM API (DeepSeek or MiniMax) for summary generation.
        
        Uses the LLM client wrapper with retry logic and error handling.
        
        Args:
            prompt: Prompt to send to LLM
        
        Returns:
            API response as dictionary containing summary, suggestion, and end_score
        
        Raises:
            LLMClientError: If API call fails after all retries
        """
        try:
            response = self.llm_client.generate_summary(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )
            return response
            
        except LLMClientError as e:
            logger.error(f"{self.llm_provider} API call failed: {e}")
            raise Exception(f"{self.llm_provider} API call failed: {e}")
    
    def _parse_llm_response(
        self,
        response: Dict[str, Any]
    ) -> tuple[str, str, float]:
        """
        Parse LLM response to extract summary, suggestion, and end_score.
        
        Args:
            response: LLM API response
        
        Returns:
            Tuple of (summary, suggestion, end_score)
        
        Raises:
            ValueError: If response format is invalid
        """
        try:
            summary = response.get("summary", "")
            suggestion = response.get("suggestion", "continue")
            end_score = float(response.get("end_score", 0.0))
            
            # Validate suggestion
            valid_suggestions = ["continue", "change_angle", "suggest_end", "force_end"]
            if suggestion not in valid_suggestions:
                raise ValueError(f"Invalid suggestion: {suggestion}")
            
            # Validate end_score range
            if not (0 <= end_score <= 100):
                raise ValueError(f"Invalid end_score: {end_score}")
            
            return summary, suggestion, end_score
        
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Failed to parse LLM response: {e}")
