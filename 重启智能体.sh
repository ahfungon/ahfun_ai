#!/bin/bash

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                    🔄 重启智能体"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. 停止旧的智能体
echo "【步骤 1】停止旧的智能体进程"
if ps aux | grep -q "[a]utonomous_agent.py"; then
    pkill -f 'autonomous_agent.py'
    sleep 2
    echo "✅ 已停止旧的智能体进程"
else
    echo "ℹ️  没有运行中的智能体"
fi
echo ""

# 2. 加载环境变量
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "✅ 已加载环境变量"
else
    echo "❌ .env 文件不存在"
    exit 1
fi
echo ""

# 3. 启动智能体
echo "【步骤 2】启动智能体"
echo "正在启动 Alice 和 Bob..."

# 启动 Alice
nohup python3 simulation_test/autonomous_agent.py --agent alice > simulation_test/logs/alice-output.log 2>&1 &
ALICE_PID=$!
echo "✅ Alice 已启动 (PID: $ALICE_PID)"

sleep 2

# 启动 Bob
nohup python3 simulation_test/autonomous_agent.py --agent bob > simulation_test/logs/bob-output.log 2>&1 &
BOB_PID=$!
echo "✅ Bob 已启动 (PID: $BOB_PID)"

echo ""
sleep 3

# 4. 验证智能体状态
echo "【步骤 3】验证智能体状态"
if ps -p $ALICE_PID > /dev/null 2>&1; then
    echo "✅ Alice 运行正常 (PID: $ALICE_PID)"
else
    echo "❌ Alice 启动失败"
    echo "   查看日志: tail -f simulation_test/logs/alice-output.log"
fi

if ps -p $BOB_PID > /dev/null 2>&1; then
    echo "✅ Bob 运行正常 (PID: $BOB_PID)"
else
    echo "❌ Bob 启动失败"
    echo "   查看日志: tail -f simulation_test/logs/bob-output.log"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                    ✅ 重启完成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "【监控命令】"
echo "  查看日志:"
echo "    tail -f simulation_test/logs/agent-alice.log"
echo "    tail -f simulation_test/logs/agent-bob.log"
echo ""
echo "  查看话题状态:"
echo "    python3 -c \"
from models.database import SessionLocal
from models.models import Topic

db = SessionLocal()
topic = db.query(Topic).filter(Topic.status.in_(['active', 'closing_pending'])).first()
if topic:
    print(f'话题: {topic.title}')
    print(f'状态: {topic.status}')
db.close()
\""
echo ""
