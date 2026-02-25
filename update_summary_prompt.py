#!/usr/bin/env python3
"""
更新总结 Prompt 以更好地归纳发言人观点
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from models.system_config import SystemConfig

# 新的总结 Prompt
NEW_SUMMARY_PROMPT = """你是一个专业的对话总结专家。你的任务是将对话内容压缩成简洁的摘要，以便作为历史记录提供给智能体，节省 token。

【总结要求】

1. 按发言人归纳观点
   - 明确列出每个发言人的核心观点
   - 用简洁的语言概括他们的立场和论据
   - 保留关键的论点和例子

2. 梳理对话脉络
   - 对话如何展开的（从什么话题开始）
   - 双方在哪些点上有共识
   - 双方在哪些点上有分歧
   - 对话是否有新的突破或转折

3. 评估对话状态
   - 对话深度：是否深入探讨了话题
   - 观点多样性：是否有多角度的讨论
   - 逻辑连贯性：对话是否有清晰的逻辑线索
   - 结论性：是否达成了有价值的结论

【建议类型】
- continue: 对话进展良好，可以继续深入
- change_angle: 建议从不同角度探讨
- suggest_end: 对话已充分，建议考虑结束
- force_end: 对话质量下降或偏离主题，应该结束

【输出格式】
请以 JSON 格式返回（只返回 JSON，不要其他文字）：
{{
    "summary": "【对话脉络】\\n...\\n\\n【各方观点】\\n发言人A：...\\n发言人B：...\\n\\n【共识与分歧】\\n...",
    "suggestion": "continue",
    "end_score": 75
}}

【输入信息】

话题：{topic_title}
话题描述：{topic_description}

之前的摘要：
{previous_summary}

新的对话内容：
{new_messages}

请生成简洁的总结，重点归纳每个发言人的核心观点："""

def update_summary_prompt():
    """更新总结 Prompt"""
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        config = db.query(SystemConfig).filter(
            SystemConfig.key == 'summary_prompt'
        ).first()
        
        if config:
            print("📝 更新 summary_prompt...")
            print()
            print("旧 Prompt 长度:", len(config.value), "字符")
            print("新 Prompt 长度:", len(NEW_SUMMARY_PROMPT), "字符")
            print()
            
            config.value = NEW_SUMMARY_PROMPT
            db.commit()
            
            print("✅ summary_prompt 已更新")
            print()
            print("新 Prompt 预览:")
            print("=" * 70)
            print(NEW_SUMMARY_PROMPT[:500] + "...")
            print("=" * 70)
            print()
            print("📝 下一步:")
            print("1. 重启 API 服务器: ./restart_api.sh")
            print("2. 重启 Worker: bash restart_worker_quick.sh")
            print("3. 测试总结功能: 在管理后台触发一次总结")
        else:
            print("❌ 未找到 summary_prompt 配置")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_summary_prompt()
