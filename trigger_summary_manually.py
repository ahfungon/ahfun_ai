#!/usr/bin/env python3
"""手动触发话题总结任务（用于测试）"""

import sys
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import Topic
from services.summary_service import SummaryService

def trigger_summary(topic_id: str):
    """手动触发指定话题的总结任务"""
    db = next(get_db())
    
    try:
        # 获取话题
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            print(f"❌ 话题 {topic_id} 不存在")
            return
        
        print(f"📊 话题信息:")
        print(f"  - ID: {topic.id}")
        print(f"  - 标题: {topic.title}")
        print(f"  - 状态: {topic.status}")
        print(f"  - Token 计数: {topic.token_count_since_summary}")
        print(f"  - 当前摘要: {'有' if topic.summary else '无'}")
        print(f"  - LLM 建议: {topic.llm_suggestion or '无'}")
        print()
        
        # 检查是否有待处理的总结任务
        if topic.pending_summary_job:
            print("⚠️  已有待处理的总结任务")
            return
        
        # 手动触发总结
        print("🚀 开始生成总结...")
        summary_service = SummaryService(db)
        
        # 获取所有消息（如果没有 last_summarized_message_id，获取所有消息）
        from models.models import Message
        if topic.last_summarized_message_id:
            messages = db.query(Message).filter(
                Message.topic_id == topic_id,
                Message.id > topic.last_summarized_message_id
            ).order_by(Message.created_at).all()
        else:
            messages = db.query(Message).filter(
                Message.topic_id == topic_id
            ).order_by(Message.created_at).all()
        
        print(f"📝 找到 {len(messages)} 条新消息")
        
        if len(messages) == 0:
            print("❌ 没有新消息，无法生成总结")
            return
        
        # 生成总结
        result = summary_service.generate_summary(topic, messages)
        
        if result:
            summary = result.summary
            suggestion = result.suggestion
            end_score = result.end_score
            
            # 更新话题
            summary_service.update_topic_summary(
                topic_id=topic.id,
                summary=summary,
                suggestion=suggestion,
                end_score=end_score
            )
            
            # 保存历史
            summary_service.save_summary_history(
                topic_id=topic.id,
                summary=summary,
                suggestion=suggestion,
                end_score=end_score
            )
            
            # 应用 LLM 建议
            summary_service.apply_llm_suggestion(topic, suggestion)
            
            # 重置 token 计数
            topic.token_count_since_summary = 0
            if messages:
                topic.last_summarized_message_id = messages[-1].id
            
            db.commit()
            
            print()
            print("✅ 总结生成成功!")
            print(f"  - 摘要长度: {len(summary)} 字符")
            print(f"  - LLM 建议: {suggestion}")
            print(f"  - 结束评分: {end_score}")
            print()
            print("📄 摘要内容:")
            print(f"  {summary[:200]}..." if len(summary) > 200 else f"  {summary}")
        else:
            print("❌ 总结生成失败")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 获取当前活跃话题
        db = next(get_db())
        topic = db.query(Topic).filter(Topic.status == 'active').first()
        db.close()
        
        if topic:
            print(f"使用当前活跃话题: {topic.id}")
            trigger_summary(topic.id)
        else:
            print("用法: python3 trigger_summary_manually.py [topic_id]")
            print("或者不带参数，自动使用当前活跃话题")
    else:
        topic_id = sys.argv[1]
        trigger_summary(topic_id)
