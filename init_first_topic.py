#!/usr/bin/env python3
"""
初始化第一个话题

这个脚本会：
1. 检查是否已有活跃话题
2. 如果没有，使用 LLM 生成一个新话题
3. 创建话题并设置为 active 状态
"""

import sys
from models.database import SessionLocal
from services.topic_service import TopicService

def main():
    """主函数"""
    print("=" * 60)
    print("初始化第一个话题")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        topic_service = TopicService(db)
        
        # 检查是否已有活跃话题
        active_topic = topic_service.get_active_topic()
        
        if active_topic:
            print(f"\n✅ 已存在活跃话题:")
            print(f"   ID: {active_topic.id}")
            print(f"   标题: {active_topic.title}")
            print(f"   状态: {active_topic.status}")
            print(f"   描述: {active_topic.topic_description[:100] if active_topic.topic_description else 'N/A'}...")
            return 0
        
        print("\n📝 没有活跃话题，正在生成新话题...")
        print("   使用 DeepSeek LLM 生成话题...")
        
        # 使用 LLM 生成话题
        # 使用第一个注册的 agent 作为创建者
        from models.models import Agent
        first_agent = db.query(Agent).first()
        
        if not first_agent:
            print("\n❌ 错误: 没有找到注册的 Agent")
            print("   请先注册 Agent:")
            print("   python3 init_agents.py")
            return 1
        
        creator_agent_id = first_agent.id
        print(f"   创建者: {first_agent.name} ({creator_agent_id})")
        
        # 生成话题
        new_topic = topic_service.generate_topic_with_llm(creator_agent_id)
        
        if new_topic:
            print(f"\n✅ 话题创建成功!")
            print(f"   ID: {new_topic.id}")
            print(f"   标题: {new_topic.title}")
            print(f"   状态: {new_topic.status}")
            print(f"   描述: {new_topic.topic_description[:200] if new_topic.topic_description else 'N/A'}...")
            print(f"\n💡 现在可以:")
            print(f"   1. 访问 http://localhost:8080/ 查看话题")
            print(f"   2. 访问 http://localhost:8080/simulator.html 启动智能体")
            return 0
        else:
            print("\n❌ 话题生成失败")
            print("   可能原因:")
            print("   1. DeepSeek API Key 未配置")
            print("   2. LLM API 调用失败")
            print("   3. 网络连接问题")
            print("\n   请检查 .env 文件中的 DEEPSEEK_API_KEY")
            return 1
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
