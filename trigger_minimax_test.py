#!/usr/bin/env python3
"""Trigger a summary task to test MiniMax integration."""

import sys
from models.database import SessionLocal
from models.models import Topic, Message
from services.summary_service import SummaryService


def trigger_summary_for_topic(topic_id: str):
    """Trigger a summary for a specific topic."""
    db = SessionLocal()
    try:
        # Get topic
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            print(f"❌ 话题 {topic_id} 不存在")
            return False
        
        print(f"📋 话题信息:")
        print(f"  ID: {topic.id}")
        print(f"  标题: {topic.title}")
        print(f"  状态: {topic.status}")
        
        # Get recent messages
        messages = db.query(Message).filter(
            Message.topic_id == topic_id
        ).order_by(Message.created_at.desc()).limit(5).all()
        
        if not messages:
            print("❌ 没有找到消息")
            return False
        
        print(f"\n📝 最近 {len(messages)} 条消息:")
        for msg in reversed(messages):
            print(f"  [{msg.agent_id}]: {msg.content[:50]}...")
        
        # Initialize summary service
        print("\n🔧 初始化 SummaryService...")
        summary_service = SummaryService(db)
        print(f"  ✓ 使用的 LLM: {summary_service.llm_provider}")
        print(f"  ✓ 客户端类型: {type(summary_service.llm_client).__name__}")
        
        # Generate summary
        print("\n🚀 生成总结...")
        print("  (这将调用 MiniMax API，请稍候...)")
        
        result = summary_service.generate_summary(topic, list(reversed(messages)))
        
        print("\n✅ 总结生成成功!")
        print(f"\n📊 结果:")
        print(f"  总结: {result.summary[:200]}...")
        print(f"  建议: {result.suggestion}")
        print(f"  结束评分: {result.end_score}")
        
        # Update topic
        print("\n💾 更新话题...")
        summary_service.update_topic_summary(
            topic_id=topic.id,
            summary=result.summary,
            suggestion=result.suggestion,
            end_score=result.end_score
        )
        
        print("✅ 话题更新成功!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


def main():
    """Main function."""
    print("=" * 60)
    print("MiniMax 测试 - 触发总结任务")
    print("=" * 60)
    
    # Get active topics
    db = SessionLocal()
    try:
        topics = db.query(Topic).filter(Topic.status == 'active').all()
        
        if not topics:
            print("\n❌ 没有找到活跃话题")
            print("\n请先创建一个话题并发送一些消息")
            return 1
        
        print(f"\n找到 {len(topics)} 个活跃话题:")
        for i, topic in enumerate(topics, 1):
            msg_count = db.query(Message).filter(Message.topic_id == topic.id).count()
            print(f"{i}. {topic.title} (ID: {topic.id[:8]}..., {msg_count} 条消息)")
        
        # Use first topic
        topic_id = topics[0].id
        print(f"\n使用话题: {topics[0].title}")
        
    finally:
        db.close()
    
    # Trigger summary
    print("\n" + "=" * 60)
    success = trigger_summary_for_topic(topic_id)
    print("=" * 60)
    
    if success:
        print("\n✅ 测试成功!")
        print("\n查看日志确认 MiniMax 被调用:")
        print("  tail -50 logs/api.log | grep -i minimax")
        return 0
    else:
        print("\n❌ 测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
