#!/usr/bin/env python3
"""
初始化 Agent 数据

创建两个测试用的 Agent 记录
"""

from models.database import SessionLocal
from models.models import Agent
from utils.auth_utils import hash_token


def init_agents():
    """初始化 Agent 数据"""
    db = SessionLocal()
    
    try:
        # 检查是否已存在
        existing_agents = db.query(Agent).all()
        if existing_agents:
            print("Agent 已存在:")
            for agent in existing_agents:
                print(f"  - {agent.id}: {agent.name}")
            return
        
        # 创建 Agent 1
        agent1_token = "token-agent-1-secret"
        agent1 = Agent(
            id="agent-1",
            name="Agent-1",
            auth_token_hash=hash_token(agent1_token)
        )
        db.add(agent1)
        
        # 创建 Agent 2
        agent2_token = "token-agent-2-secret"
        agent2 = Agent(
            id="agent-2",
            name="Agent-2",
            auth_token_hash=hash_token(agent2_token)
        )
        db.add(agent2)
        
        db.commit()
        
        print("✅ Agent 创建成功!")
        print()
        print("Agent 信息:")
        print(f"  Agent 1:")
        print(f"    ID: agent-1")
        print(f"    Name: Agent-1")
        print(f"    Token: {agent1_token}")
        print()
        print(f"  Agent 2:")
        print(f"    ID: agent-2")
        print(f"    Name: Agent-2")
        print(f"    Token: {agent2_token}")
        print()
        print("现在可以运行测试了！")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 创建 Agent 失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_agents()
