#!/bin/bash

# 双智能体对话监控脚本

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 双智能体对话监控"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查智能体进程
echo "📊 智能体状态:"
echo ""

if pgrep -f "autonomous_agent.py --agent alice" > /dev/null; then
    echo "✅ Alice (分析型) - 运行中"
else
    echo "❌ Alice (分析型) - 未运行"
fi

if pgrep -f "autonomous_agent.py --agent bob" > /dev/null; then
    echo "✅ Bob (创造型) - 运行中"
else
    echo "❌ Bob (创造型) - 未运行"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 最近的对话 (最新 20 条)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 获取活跃话题
TOPIC_ID=$(curl -s http://localhost:8000/api/monitor/topic/active | python3 -c "import sys, json; print(json.load(sys.stdin)['topic_id'])" 2>/dev/null)

if [ -z "$TOPIC_ID" ]; then
    echo "❌ 无法获取活跃话题"
    exit 1
fi

# 获取最近消息
curl -s "http://localhost:8000/api/monitor/topic/${TOPIC_ID}/messages?limit=20" | \
python3 -c "
import sys, json
from datetime import datetime

data = json.load(sys.stdin)
messages = data['messages']

# 按时间排序（最新的在后面）
messages.sort(key=lambda x: x['created_at'])

for msg in messages[-20:]:
    # 解析时间
    created_at = msg['created_at'].replace('Z', '+00:00')
    dt = datetime.fromisoformat(created_at)
    time_str = dt.strftime('%H:%M:%S')
    
    # 获取智能体名称和内容
    agent_name = msg.get('agent_name', 'Unknown')
    content = msg['content']
    
    # 根据智能体设置颜色
    if 'Alice' in agent_name:
        color = '\033[36m'  # 青色
        icon = '🔍'
    elif 'Bob' in agent_name:
        color = '\033[35m'  # 紫色
        icon = '💡'
    else:
        color = '\033[37m'  # 白色
        icon = '💬'
    
    reset = '\033[0m'
    
    # 打印消息
    print(f'{color}[{time_str}] {icon} {agent_name}{reset}')
    
    # 打印内容（限制长度）
    lines = content.split('\n')
    for line in lines[:3]:  # 只显示前3行
        if line.strip():
            print(f'  {line[:100]}')
    
    if len(lines) > 3 or len(content) > 300:
        print(f'  ...')
    
    print()
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 统计信息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 统计消息数
curl -s "http://localhost:8000/api/monitor/topic/${TOPIC_ID}/messages?limit=1000" | \
python3 -c "
import sys, json

data = json.load(sys.stdin)
messages = data['messages']

alice_count = sum(1 for msg in messages if 'Alice' in msg.get('agent_name', ''))
bob_count = sum(1 for msg in messages if 'Bob' in msg.get('agent_name', ''))
total_count = len(messages)

print(f'总消息数: {total_count}')
print(f'Alice 发言: {alice_count}')
print(f'Bob 发言: {bob_count}')
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 提示:"
echo "  - 查看实时日志: tail -f simulation_test/logs/agent-*.log"
echo "  - 查看 Alice: tail -f simulation_test/logs/agent-alice.log"
echo "  - 查看 Bob: tail -f simulation_test/logs/agent-bob.log"
echo "  - 前端监控: http://localhost:8080/monitor.html"
echo "  - 停止智能体: pkill -f autonomous_agent.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
