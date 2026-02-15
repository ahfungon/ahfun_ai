#!/bin/bash

echo "=================================="
echo "快速测试关闭话题协商功能"
echo "=================================="
echo ""

# 1. 停止旧的智能体
echo "1️⃣  停止旧的智能体..."
pkill -f 'autonomous_agent.py' 2>/dev/null
sleep 2
echo "   ✓ 已停止"
echo ""

# 2. 启动两个智能体（后台）
echo "2️⃣  启动智能体（Alice 和 Bob）..."
cd simulation_test

# 启动 Alice
nohup python3 autonomous_agent.py --agent alice > /dev/null 2>&1 &
ALICE_PID=$!
echo "   ✓ Alice 已启动 (PID: $ALICE_PID)"

# 启动 Bob
nohup python3 autonomous_agent.py --agent bob > /dev/null 2>&1 &
BOB_PID=$!
echo "   ✓ Bob 已启动 (PID: $BOB_PID)"

cd ..
sleep 3
echo ""

# 3. 显示监控命令
echo "3️⃣  监控命令："
echo ""
echo "   查看 Alice 日志："
echo "   tail -f simulation_test/logs/agent-alice.log"
echo ""
echo "   查看 Bob 日志："
echo "   tail -f simulation_test/logs/agent-bob.log"
echo ""
echo "   查看话题状态："
echo "   python3 -c \"
from models.database import SessionLocal
from models.models import Topic, Message

db = SessionLocal()
topic = db.query(Topic).order_by(Topic.created_at.desc()).first()

if topic:
    msg_count = db.query(Message).filter(Message.topic_id == topic.id).count()
    print(f'话题: {topic.title}')
    print(f'状态: {topic.status}')
    print(f'消息数: {msg_count}')
    print(f'Agent A 想关闭: {topic.agent_a_wants_close}')
    print(f'Agent B 想关闭: {topic.agent_b_wants_close}')
else:
    print('没有话题')

db.close()
\""
echo ""

# 4. 预期流程
echo "4️⃣  预期流程："
echo "   - 消息 1-4: 正常讨论"
echo "   - 消息 5: 第一个智能体提出结束（发言中包含'可以结束了'）"
echo "   - 系统自动调用 request-close，状态变为 closing_pending"
echo "   - 消息 6: 第二个智能体同意（发言中包含'同意结束'）"
echo "   - 系统自动调用 request-close，状态变为 closed"
echo ""

# 5. 停止命令
echo "5️⃣  停止智能体："
echo "   pkill -f 'autonomous_agent.py'"
echo ""

echo "=================================="
echo "✅ 测试环境已准备就绪"
echo "=================================="
