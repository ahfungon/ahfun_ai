#!/usr/bin/env python3
"""
测试新的总结 Prompt
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from models.models import Topic
from services.summary_service import SummaryService

def test_summary():
    """测试总结功能"""
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # 获取话题
        topic_id = "33de203c-d7fe-4201-9848-feb185641e63"
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        
        if not topic:
            print(f"❌ 未找到话题 {topic_id}")
            return
        
        print(f"📊 话题信息:")
        print(f"  标题: {topic.title}")
        print(f"  Token 计数: {topic.token_count_since_summary}")
        print(f"  当前总结长度: {len(topic.summary) if topic.summary else 0} 字符")
        print()
        
        # 获取未总结的消息
        from models.models import Message
        query = db.query(Message).filter(Message.topic_id == topic_id)
        
        if topic.last_summarized_message_id:
            # 获取最后总结消息的创建时间
            last_msg = db.query(Message).filter(
                Message.id == topic.last_summarized_message_id
            ).first()
            
            if last_msg:
                query = query.filter(Message.created_at > last_msg.created_at)
        
        new_messages = query.order_by(Message.created_at).all()
        
        print(f"📝 未总结的消息数: {len(new_messages)}")
        print()
        
        if not new_messages:
            print("⚠️  没有新消息需要总结")
            return
        
        # 创建总结服务
        summary_service = SummaryService(db)
        
        print(f"🤖 使用 LLM 提供商: {summary_service.llm_provider}")
        print()
        print("⏳ 正在生成总结...")
        print()
        
        # 生成总结
        result = summary_service.generate_summary(topic, new_messages)
        
        print("=" * 70)
        print("✅ 总结生成成功")
        print("=" * 70)
        print()
        print(f"📋 总结内容:")
        print(result.summary)
        print()
        print(f"💡 建议: {result.suggestion}")
        print(f"📊 结束评分: {result.end_score}")
        print()
        
        # 更新话题
        summary_service.update_topic_summary(
            topic_id=topic_id,
            summary=result.summary,
            suggestion=result.suggestion,
            end_score=result.end_score
        )
        
        # 保存历史
        summary_service.save_summary_history(
            topic_id=topic_id,
            summary=result.summary,
            suggestion=result.suggestion,
            end_score=result.end_score
        )
        
        # 更新 last_summarized_message_id 和 token_count_since_summary
        topic.last_summarized_message_id = new_messages[-1].id
        topic.token_count_since_summary = 0
        db.commit()
        
        print("✅ 话题已更新")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_summary()
