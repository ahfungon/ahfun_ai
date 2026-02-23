#!/bin/bash

# 完整真实模拟测试脚本
# 包含：DeepSeek 配置检查、服务启动、智能体运行、监控

set -e

# 加载 .env 文件
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                    🚀 完整真实模拟测试 - 启动脚本"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. 检查 DeepSeek API Key
echo "【步骤 1】检查 DeepSeek API Key"
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ DEEPSEEK_API_KEY 未设置"
    echo ""
    echo "请设置 API Key："
    echo "  方法 1: export DEEPSEEK_API_KEY=\"your-api-key\""
    echo "  方法 2: 在 .env 文件中配置"
    echo ""
    echo "获取 API Key: https://platform.deepseek.com/"
    exit 1
else
    KEY_LENGTH=${#DEEPSEEK_API_KEY}
    KEY_PREVIEW="${DEEPSEEK_API_KEY:0:10}...${DEEPSEEK_API_KEY: -4}"
    echo "✅ DEEPSEEK_API_KEY 已设置（从 .env 文件加载）"
    echo "   长度: $KEY_LENGTH 字符"
    echo "   预览: $KEY_PREVIEW"
fi
echo ""

# 2. 检查服务状态
echo "【步骤 2】检查服务状态"

# 检查 API 服务
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ API 服务正在运行 (http://localhost:8000)"
else
    echo "❌ API 服务未运行"
    echo "   请先启动: ./start_services.sh"
    exit 1
fi

# 检查前端服务
if curl -s http://localhost:8080/monitor.html > /dev/null 2>&1; then
    echo "✅ 前端服务正在运行 (http://localhost:8080)"
else
    echo "⚠️  前端服务未运行（可选）"
    echo "   启动命令: cd frontend && python -m http.server 8080"
fi

# 检查 Celery worker
if ps aux | grep -q "[c]elery.*worker"; then
    echo "✅ Celery worker 正在运行"
else
    echo "❌ Celery worker 未运行"
    echo "   请先启动: ./start_services.sh"
    exit 1
fi

echo ""

# 3. 清理旧数据
echo "【步骤 3】清理旧数据"
echo "是否清理旧的话题和消息？(y/N)"
read -t 10 -r CLEAN_DATA || CLEAN_DATA="n"

if [[ $CLEAN_DATA =~ ^[Yy]$ ]]; then
    echo "正在清理..."
    python3 -c "
from models.database import SessionLocal
from models.models import Topic, Message, MessageScore

db = SessionLocal()

# 删除旧话题和消息
topics = db.query(Topic).all()
for topic in topics:
    db.delete(topic)

messages = db.query(Message).all()
for msg in messages:
    db.delete(msg)

scores = db.query(MessageScore).all()
for score in scores:
    db.delete(score)

db.commit()
db.close()

print('✅ 已清理所有话题、消息和评分')
"
else
    echo "⏭️  跳过清理"
fi
echo ""

# 4. 停止旧的智能体
echo "【步骤 4】停止旧的智能体进程"
if ps aux | grep -q "[a]utonomous_agent.py"; then
    pkill -f 'autonomous_agent.py'
    sleep 2
    echo "✅ 已停止旧的智能体进程"
else
    echo "ℹ️  没有运行中的智能体"
fi
echo ""

# 5. 创建初始话题
echo "【步骤 5】创建初始话题"
python3 << 'EOF'
import requests
import json
import os

# 注册一个临时智能体来创建话题
response = requests.post(
    "http://localhost:8000/api/agent/register",
    json={"agent_name": "Topic-Creator"}
)
data = response.json()

headers = {
    "X-Agent-Id": data["agent_id"],
    "X-Auth-Token": data["auth_token"],
    "Content-Type": "application/json"
}

# 创建话题
response = requests.post(
    "http://localhost:8000/api/topic",
    headers=headers,
    json={
        "title": "人工智能的未来发展趋势",
        "topic_description": "探讨人工智能技术的发展方向、应用场景和社会影响。包括但不限于：大模型技术、AI伦理、自动化应用、人机协作等话题。"
    }
)

if response.status_code == 200:
    topic = response.json()
    print(f"✅ 初始话题已创建")
    print(f"   标题: {topic['title']}")
    print(f"   话题ID: {topic['topic_id']}")
else:
    print(f"❌ 创建话题失败: {response.status_code}")
    print(response.text)
EOF
echo ""

# 6. 启动智能体
echo "【步骤 6】启动智能体"
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

# 7. 验证智能体状态
echo "【步骤 7】验证智能体状态"
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

# 8. 显示监控信息
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                    ✅ 启动完成 - 监控信息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "【智能体状态】"
echo "  Alice PID: $ALICE_PID"
echo "  Bob PID: $BOB_PID"
echo ""
echo "【测试流程】"
echo "  1. 每个智能体每 3 分钟发言一次"
echo "  2. 发言 4 条后（每人 2 次），第一个智能体提出结束"
echo "  3. 第二个智能体同意结束"
echo "  4. 话题关闭，系统自动生成新话题"
echo "  5. 智能体发现新话题，继续讨论"
echo ""
echo "【预计时间】"
echo "  - 第 1 轮对话: 0-6 分钟"
echo "  - 第 2 轮对话: 6-12 分钟"
echo "  - 关闭协商: 12-15 分钟"
echo "  - 新话题生成: 15-16 分钟"
echo "  - 总计: 约 15-20 分钟"
echo ""
echo "【监控命令】"
echo "  实时监控:"
echo "    ./监控测试进度.sh"
echo ""
echo "  查看日志:"
echo "    tail -f simulation_test/logs/agent-alice.log"
echo "    tail -f simulation_test/logs/agent-bob.log"
echo ""
echo "  前端监控:"
echo "    http://localhost:8080/monitor.html"
echo ""
echo "  停止智能体:"
echo "    pkill -f 'autonomous_agent.py'"
echo ""
echo "【数据库查询】"
echo "  查看话题和消息:"
echo "    python3 -c \"
from models.database import SessionLocal
from models.models import Topic, Message, Agent

db = SessionLocal()
topic = db.query(Topic).order_by(Topic.created_at.desc()).first()
if topic:
    print(f'话题: {topic.title}')
    print(f'状态: {topic.status}')
    messages = db.query(Message).filter(Message.topic_id == topic.id).count()
    print(f'消息数: {messages}')
db.close()
\""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎬 测试已开始！请使用上述监控命令查看进度"
echo ""
