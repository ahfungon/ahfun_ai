#!/bin/bash

# 实时监控脚本 - 显示智能体对话进度

while true; do
    clear
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "                    📊 智能体对话实时监控"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    date "+%Y-%m-%d %H:%M:%S"
    echo ""
    
    # 检查智能体进程
    echo "【智能体状态】"
    if ps aux | grep -q "[a]utonomous_agent.py.*alice"; then
        ALICE_PID=$(ps aux | grep "[a]utonomous_agent.py.*alice" | awk '{print $2}')
        echo "  ✅ Alice 运行中 (PID: $ALICE_PID)"
    else
        echo "  ❌ Alice 未运行"
    fi
    
    if ps aux | grep -q "[a]utonomous_agent.py.*bob"; then
        BOB_PID=$(ps aux | grep "[a]utonomous_agent.py.*bob" | awk '{print $2}')
        echo "  ✅ Bob 运行中 (PID: $BOB_PID)"
    else
        echo "  ❌ Bob 未运行"
    fi
    echo ""
    
    # 查询话题和消息
    python3 << 'EOF'
from models.database import SessionLocal
from models.models import Topic, Message, Agent
from datetime import datetime

db = SessionLocal()

# 获取最新话题
topic = db.query(Topic).order_by(Topic.created_at.desc()).first()

if topic:
    print("【当前话题】")
    print(f"  标题: {topic.title}")
    print(f"  状态: {topic.status}")
    print(f"  话题ID: {topic.id[:8]}...")
    
    if topic.status == "closing_pending":
        print(f"  请求方: {topic.closing_requested_by[:12]}...")
    
    if topic.status == "closed":
        print("  ⚠️  话题已关闭，等待新话题生成...")
    
    print()
    
    # 获取消息
    messages = db.query(Message).filter(Message.topic_id == topic.id).order_by(Message.created_at).all()
    
    print(f"【消息列表】(共 {len(messages)} 条)")
    
    if messages:
        for i, msg in enumerate(messages, 1):
            agent = db.query(Agent).filter(Agent.id == msg.agent_id).first()
            agent_name = agent.name if agent else "Unknown"
            
            # 时间
            time_str = msg.created_at.strftime("%H:%M:%S")
            
            # 内容预览
            content = msg.content.replace('\n', ' ')
            if len(content) > 80:
                content = content[:80] + "..."
            
            # 检查是否包含关闭意愿
            close_keywords = ["结束", "关闭", "同意", "差不多"]
            has_close_intent = any(kw in msg.content for kw in close_keywords)
            marker = "🔴" if has_close_intent else "  "
            
            print(f"  {marker} {i}. [{time_str}] {agent_name}:")
            print(f"     {content}")
        
        print()
        print("  提示: 🔴 表示包含关闭意愿的发言")
    else:
        print("  暂无消息")
    
    print()
    
    # 显示进度
    if len(messages) < 4:
        remaining = 4 - len(messages)
        print(f"【进度】还需 {remaining} 条消息后触发关闭协商")
    elif topic.status == "active":
        print("【进度】已达到 4 条消息，等待智能体提出关闭...")
    elif topic.status == "closing_pending":
        print("【进度】第一个智能体已请求关闭，等待第二个智能体同意...")
    elif topic.status == "closed":
        print("【进度】话题已关闭，等待新话题生成...")
    
else:
    print("【当前话题】")
    print("  暂无活跃话题")

db.close()
EOF
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  按 Ctrl+C 退出监控 | 每 5 秒自动刷新"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    sleep 5
done
