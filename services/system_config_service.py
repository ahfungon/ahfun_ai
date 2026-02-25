"""Service for managing system configuration."""
import json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from models.system_config import SystemConfig


class SystemConfigService:
    """Service for managing system configuration."""
    
    # Default configurations
    DEFAULT_CONFIGS = [
        {
            "key": "summary_threshold",
            "value": "8000",
            "config_type": "number",
            "category": "summary",
            "display_name": "总结触发阈值",
            "description": "Token 计数达到此阈值时触发总结任务",
            "default_value": "8000",
            "validation": json.dumps({"min": 1000, "max": 50000}),
            "display_order": 1
        },
        {
            "key": "scoring_prompt",
            "value": """你是一个专业的对话质量评估专家。请对以下智能体的发言进行评分和点评。

评分标准（0-100分）：
- 相关性（30分）：发言是否紧扣话题，是否偏离主题
- 深度（25分）：观点是否有深度，是否有独特见解
- 逻辑性（25分）：论述是否清晰，逻辑是否严密
- 建设性（20分）：是否推动对话发展，是否有价值

请以 JSON 格式返回评分结果：
{{
    "relevance_score": 85,
    "evaluation_comment": "发言紧扣主题，观点独特，逻辑清晰，有效推动了对话发展。"
}}

话题：{topic_title}
话题描述：{topic_description}
当前摘要：{current_summary}

智能体发言：
{message_content}

请给出评分和点评：""",
            "config_type": "textarea",
            "category": "prompts",
            "display_name": "消息评分 Prompt",
            "description": "用于评估每条消息质量的 Prompt 模板",
            "default_value": "...",
            "display_order": 10
        },
        {
            "key": "summary_prompt",
            "value": """你是一个专业的对话总结专家。请对以下对话内容进行总结，并给出建议。

任务：
1. 总结对话的核心观点和进展
2. 评估对话质量和完整性
3. 给出继续对话的建议

评估标准：
- 对话深度：是否深入探讨了话题
- 观点多样性：是否有多角度的讨论
- 逻辑连贯性：对话是否有清晰的逻辑线索
- 结论性：是否达成了有价值的结论

建议类型：
- continue: 对话进展良好，可以继续深入
- change_angle: 建议从不同角度探讨
- suggest_end: 对话已充分，建议考虑结束
- force_end: 对话质量下降或偏离主题，应该结束

请以 JSON 格式返回：
{{
    "summary": "对话总结内容...",
    "suggestion": "continue",
    "end_score": 75
}}

话题：{topic_title}
话题描述：{topic_description}
之前的摘要：{previous_summary}

新的对话内容：
{new_messages}

请给出总结和建议：""",
            "config_type": "textarea",
            "category": "prompts",
            "display_name": "对话总结 Prompt",
            "description": "用于生成对话总结和建议的 Prompt 模板",
            "default_value": "...",
            "display_order": 11
        },
        {
            "key": "llm_provider_scoring",
            "value": "deepseek",
            "config_type": "select",
            "category": "llm",
            "display_name": "消息评分 LLM",
            "description": "用于消息评分的大模型提供商",
            "default_value": "deepseek",
            "options": json.dumps([
                {"value": "deepseek", "label": "DeepSeek"},
                {"value": "minimax", "label": "MiniMax"}
            ]),
            "display_order": 20
        },
        {
            "key": "llm_provider_summary",
            "value": "deepseek",
            "config_type": "select",
            "category": "llm",
            "display_name": "对话总结 LLM",
            "description": "用于对话总结的大模型提供商",
            "default_value": "deepseek",
            "options": json.dumps([
                {"value": "deepseek", "label": "DeepSeek"},
                {"value": "minimax", "label": "MiniMax"}
            ]),
            "display_order": 21
        },
        {
            "key": "deepseek_api_key",
            "value": "",
            "config_type": "password",
            "category": "llm",
            "display_name": "DeepSeek API Key",
            "description": "DeepSeek API 密钥",
            "default_value": "",
            "display_order": 30
        },
        {
            "key": "deepseek_api_url",
            "value": "https://api.deepseek.com/v1",
            "config_type": "text",
            "category": "llm",
            "display_name": "DeepSeek API URL",
            "description": "DeepSeek API 端点地址",
            "default_value": "https://api.deepseek.com/v1",
            "display_order": 31
        },
        {
            "key": "deepseek_model",
            "value": "deepseek-chat",
            "config_type": "text",
            "category": "llm",
            "display_name": "DeepSeek 模型",
            "description": "DeepSeek 模型名称",
            "default_value": "deepseek-chat",
            "display_order": 32
        },
        {
            "key": "minimax_api_key",
            "value": "",
            "config_type": "password",
            "category": "llm",
            "display_name": "MiniMax API Key",
            "description": "MiniMax API 密钥",
            "default_value": "",
            "display_order": 40
        },
        {
            "key": "minimax_api_url",
            "value": "https://api.minimax.chat/v1",
            "config_type": "text",
            "category": "llm",
            "display_name": "MiniMax API URL",
            "description": "MiniMax API 端点地址（OpenAI 兼容格式）",
            "default_value": "https://api.minimax.chat/v1",
            "display_order": 41
        },
        {
            "key": "minimax_model",
            "value": "MiniMax-M2.5",
            "config_type": "text",
            "category": "llm",
            "display_name": "MiniMax 模型",
            "description": "MiniMax 模型名称（如 MiniMax-M2.5, MiniMax-M2.5-highspeed）",
            "default_value": "MiniMax-M2.5",
            "display_order": 42
        }
    ]
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
    
    def initialize_defaults(self):
        """Initialize default configurations if not exists."""
        for config_data in self.DEFAULT_CONFIGS:
            existing = self.db.query(SystemConfig).filter(
                SystemConfig.key == config_data["key"]
            ).first()
            
            if not existing:
                config = SystemConfig(**config_data)
                self.db.add(config)
        
        self.db.commit()
    
    def get_config(self, key: str) -> Optional[SystemConfig]:
        """Get configuration by key."""
        return self.db.query(SystemConfig).filter(SystemConfig.key == key).first()
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        config = self.get_config(key)
        if config:
            # Parse value based on type
            if config.config_type == "number":
                try:
                    return int(config.value)
                except ValueError:
                    return default
            elif config.config_type == "boolean":
                return config.value.lower() in ("true", "1", "yes")
            else:
                return config.value
        return default
    
    def get_all_configs(self, category: Optional[str] = None) -> List[SystemConfig]:
        """Get all configurations, optionally filtered by category."""
        query = self.db.query(SystemConfig)
        if category:
            query = query.filter(SystemConfig.category == category)
        return query.order_by(SystemConfig.display_order, SystemConfig.key).all()
    
    def get_configs_by_category(self) -> Dict[str, List[SystemConfig]]:
        """Get all configurations grouped by category."""
        configs = self.get_all_configs()
        result = {}
        for config in configs:
            if config.category not in result:
                result[config.category] = []
            result[config.category].append(config)
        return result
    
    def update_config(self, key: str, value: str) -> SystemConfig:
        """Update configuration value."""
        config = self.get_config(key)
        if not config:
            raise ValueError(f"Configuration key '{key}' not found")
        
        # Validate value if validation rules exist
        if config.validation:
            try:
                validation_rules = json.loads(config.validation)
                if config.config_type == "number":
                    num_value = int(value)
                    if "min" in validation_rules and num_value < validation_rules["min"]:
                        raise ValueError(f"Value must be >= {validation_rules['min']}")
                    if "max" in validation_rules and num_value > validation_rules["max"]:
                        raise ValueError(f"Value must be <= {validation_rules['max']}")
            except json.JSONDecodeError:
                pass
        
        config.value = value
        config.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(config)
        
        return config
    
    def update_multiple_configs(self, updates: Dict[str, str]) -> List[SystemConfig]:
        """Update multiple configurations at once."""
        updated_configs = []
        for key, value in updates.items():
            try:
                config = self.update_config(key, value)
                updated_configs.append(config)
            except ValueError as e:
                # Log error but continue with other updates
                print(f"Error updating {key}: {e}")
        return updated_configs
    
    def reset_config(self, key: str) -> SystemConfig:
        """Reset configuration to default value."""
        config = self.get_config(key)
        if not config:
            raise ValueError(f"Configuration key '{key}' not found")
        
        if config.default_value:
            config.value = config.default_value
            config.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(config)
        
        return config
    
    def export_configs(self) -> Dict[str, Any]:
        """Export all configurations as dictionary."""
        configs = self.get_all_configs()
        return {
            config.key: {
                "value": config.value,
                "category": config.category,
                "display_name": config.display_name
            }
            for config in configs
        }
    
    def import_configs(self, config_dict: Dict[str, str]):
        """Import configurations from dictionary."""
        for key, value in config_dict.items():
            try:
                self.update_config(key, value)
            except ValueError:
                pass  # Skip invalid keys


from datetime import datetime
