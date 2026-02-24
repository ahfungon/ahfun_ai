#!/usr/bin/env python3
"""
快速启动脚本

自动完成所有初始化步骤：
1. 检查并创建 Agent
2. 检查并创建初始话题
3. 显示访问地址
"""

import sys
from models.database import SessionLocal
from models.models import Agent, Topic
from services.topic_service import TopicService
from datetime import datetime

def check_agents(db):
    """检查并创建 Agent"""
    print("\n" + "=" * 60)
    print("1. 检查 Agent")
    print("=" * 60)
    
    agents = db.query(Agent).all()
    
    if agents:
        print(f"✅ 找到 {len(agents)} 个 Agent:")
        for agent in agents:
            print(f"   • {agent.name} ({agent.id})")
        return True
    else:
        print("⚠️  没有找到 Agent，正在创建...")
        
        # 创建两个默认 Agent
        import bcrypt
        
        agent1 = Agent(
            id="agent-1",
            name="Agent-1",
            token_hash=bcrypt.hashpw("token-agent-1-secret".encode(), bcrypt.gensalt()).decode()
        )
        agent2 = Agent(
            id="agent-2",
            name="Agent-2",
            token_hash=bcrypt.hashpw("token-agent-2-secret".encode(), bcrypt.gensalt()).decode()
        )
        
        db.add(agent1)
        db.add(agent2)
        db.commit()
        
        print("✅ 已创建 2 个 Agent:")
        print("   • Agent-1 (agent-1) - Token: token-agent-1-secret")
        print("   • Agent-2 (agent-2) - Token: token-agent-2-secret")
        return True


def check_topic(db):
    """检查并创建话题"""
    print("\n" + "=" * 60)
    print("2. 检查话题")
    print("=" * 60)
    
    topic_service = TopicService(db)
    active_topic = topic_service.get_active_topic()
    
    if active_topic:
        print(f"✅ 已存在活跃话题:")
        print(f"   标题: {active_topic.title}")
        print(f"   状态: {active_topic.status}")
        if active_topic.topic_description:
            desc = active_topic.topic_description[:100]
            print(f"   描述: {desc}{'...' if len(active_topic.topic_description) > 100 else ''}")
        return True
    
    print("⚠️  没有活跃话题，正在创建...")
    
    # 创建简单的默认话题
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    topics = [
        {
            "title": "人工智能的未来发展",
            "description": "探讨人工智能技术的发展趋势、应用场景和潜在影响。包括但不限于：机器学习、深度学习、自然语言处理、计算机视觉等领域的最新进展，以及AI在医疗、教育、金融等行业的应用前景。"
        },
        {
            "title": "可持续发展与环境保护",
            "description": "讨论全球气候变化、环境保护措施和可持续发展策略。探讨如何平衡经济发展与环境保护，包括清洁能源、循环经济、碳中和等话题，以及个人和企业在环保方面的责任。"
        },
        {
            "title": "数字化时代的教育变革",
            "description": "探讨在线教育、个性化学习和教育技术创新。讨论数字化工具如何改变传统教育模式，包括远程学习、AI辅助教学、虚拟现实在教育中的应用，以及如何培养适应未来的技能。"
        },
        {
            "title": "科技伦理与隐私保护",
            "description": "讨论数据隐私、算法偏见和技术伦理问题。探讨在大数据和AI时代如何保护个人隐私，如何确保算法的公平性和透明度，以及科技公司和政府在这方面的责任。"
        },
        {
            "title": "远程工作与未来办公",
            "description": "探讨远程办公的优势、挑战和最佳实践。讨论如何在远程环境中保持团队协作和生产力，包括工作生活平衡、数字化工具的使用、企业文化的维护等话题。"
        }
    ]
    
    # 随机选择一个话题
    import random
    selected = random.choice(topics)
    
    # 获取第一个 Agent 作为创建者
    first_agent = db.query(Agent).first()
    
    topic = topic_service.create_topic(
        title=selected["title"],
        topic_description=selected["description"]
    )
    
    print(f"✅ 话题创建成功:")
    print(f"   标题: {topic.title}")
    print(f"   描述: {selected['description'][:100]}...")
    return True


def show_access_info():
    """显示访问信息"""
    print("\n" + "=" * 60)
    print("3. 访问地址")
    print("=" * 60)
    
    print("\n🌐 前端页面:")
    print("   • 监控页面: http://localhost:8080/")
    print("   • 聊天界面: http://localhost:8080/index.html")
    print("   • 智能体模拟器: http://localhost:8080/simulator.html")
    print("   • 管理后台: http://localhost:8080/admin.html")
    
    print("\n📚 API 文档:")
    print("   • Swagger UI: http://localhost:8080/docs")
    print("   • API 文档: http://localhost:8080/api-docs")
    
    print("\n🤖 智能体认证信息:")
    print("   • Agent-1: agent-1 / token-agent-1-secret")
    print("   • Agent-2: agent-2 / token-agent-2-secret")


def main():
    """主函数"""
    print("\n🚀 快速启动 - 双智能体对话平台")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # 1. 检查 Agent
        if not check_agents(db):
            return 1
        
        # 2. 检查话题
        if not check_topic(db):
            return 1
        
        # 3. 显示访问信息
        show_access_info()
        
        print("\n" + "=" * 60)
        print("✅ 初始化完成！")
        print("=" * 60)
        
        print("\n💡 下一步:")
        print("   1. 访问模拟器: http://localhost:8080/simulator.html")
        print("   2. 添加智能体并启动")
        print("   3. 观察自动对话和评分")
        
        print("\n📝 提示:")
        print("   • 消息评分会自动触发")
        print("   • 双方同意关闭话题后会自动生成新话题")
        print("   • Token 达到阈值会自动生成摘要")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
