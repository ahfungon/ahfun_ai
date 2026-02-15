#!/bin/bash

echo "实时监控测试进度"
echo "按 Ctrl+C 退出"
echo ""

while true; do
    clear
    echo "========================================"
    echo "关闭话题协商测试 - 实时监控"
    echo "========================================"
    date
    echo ""
    
    # 检查智能体进程
    echo "【智能体状态】"
    ALICE_PID=$(ps aux | grep 'autonomous_agent.py.*alice' | grep -v grep | awk '{print $2}')
    BOB_PID=$(ps aux | grep 'autonomous_agent.py.*bob' | grep -v grep | awk '{print $2}')
    
    if [ -n "$ALICE_PID" ]; then
        echo "  ✓ Alice 运行中 (PID: $ALICE_PID)"
    else
        echo "  ❌ Alice 未运行"
    fi
    
    if [ -n "$BOB_PID" ]; then
        echo "  ✓ Bob 运行中 (PID: $BOB_PID)"
    else
        echo "  ❌ Bob 未运行"
    fi
    echo ""
    
    # 查询话题状态
    echo "【话题状态】"
    python3 -c "
from models.database import SessionLocal
from models.models import Topic, Message
import sys

db = SessionLocal()
topic = db.query(Topic).order_by(Topic.created_at.desc()).first()

if topic:
    msg_count = db.query(Message).filter(Message.topic_id == topic.id).count()
    
    print(f'  话题: {topic.title[:40]}...')
    print(f'  状态: {topic.status}')
    print(f'  消息数: {msg_count}')
    
    if topic.status == 'closing_pending':
        print(f'  请求方: {topic.closing_requested_by}')
        print(f'  ⏳ 等待另一方响应...')
    elif topic.status == 'closed':
        print(f'  ✅ 话题已关闭')
        print(f'  Agent A 同意: {topic.agent_a_wants_close}')
        print(f'  Agent B 同意: {topic.agent_b_wants_close}')
    
    # 显示最近的消息
    messages = db.query(Message).filter(Message.topic_id == topic.id).order_by(Message.created_at.desc()).limit(3).all()
    
    if messages:
        print('')
        print('  【最近消息】')
        for i, msg in enumerate(reversed(messages), 1):
            agent_name = msg.agent.name if msg.agent else 'Unknown'
            content = msg.content[:50].replace('\n', ' ')
            print(f'  {msg_count - len(messages) + i}. {agent_name}: {content}...')
else:
    print('  没有活跃话题')

db.close()
" 2>/dev/null
    
    echo ""
    echo "========================================"
    echo "每 5 秒刷新一次..."
    
    sleep 5
done
