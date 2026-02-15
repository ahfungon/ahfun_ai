#!/bin/bash

# 监控 LLM 话题生成功能
# 用于观察智能体关闭话题后是否自动生成新的 LLM 话题

echo "=========================================="
echo "LLM 话题生成监控"
echo "=========================================="
echo ""

# 检查当前活跃话题
echo "1. 当前活跃话题:"
echo "------------------------------------------"
python3 -c "
from models.database import SessionLocal
from models.models import Topic, Message

db = SessionLocal()
try:
    topic = db.query(Topic).filter(Topic.status.in_(['active', 'closing_pending'])).first()
    
    if topic:
        msg_count = db.query(Message).filter(Message.topic_id == topic.id).count()
        print(f'标题: {topic.title}')
        print(f'状态: {topic.status}')
        print(f'消息数: {msg_count}')
        
        if topic.closing_requested_by:
            print(f'关闭请求者: {topic.closing_requested_by}')
            print(f'请求时间: {topic.closing_requested_at}')
        
        # 判断是否是 LLM 生成的话题
        if 'AI讨论话题' in topic.title:
            print('类型: 备用话题（LLM 调用失败）')
        else:
            print('类型: LLM 生成话题 ✓')
    else:
        print('没有活跃话题')
finally:
    db.close()
"
echo ""

# 检查最近生成的话题
echo "2. 最近5个话题:"
echo "------------------------------------------"
python3 -c "
from models.database import SessionLocal
from models.models import Topic

db = SessionLocal()
try:
    topics = db.query(Topic).order_by(Topic.created_at.desc()).limit(5).all()
    
    for i, topic in enumerate(topics, 1):
        is_llm = '✓ LLM' if 'AI讨论话题' not in topic.title else '✗ 备用'
        print(f'{i}. [{topic.status:15}] {is_llm} | {topic.title[:40]}...')
finally:
    db.close()
"
echo ""

# 检查 Celery 任务
echo "3. Celery Worker 状态:"
echo "------------------------------------------"
if pgrep -f "celery.*worker" > /dev/null; then
    echo "✓ Celery Worker 运行中"
    echo "进程数: $(pgrep -f 'celery.*worker' | wc -l)"
else
    echo "✗ Celery Worker 未运行"
fi
echo ""

# 检查智能体状态
echo "4. 智能体状态:"
echo "------------------------------------------"
if pgrep -f "autonomous_agent.py" > /dev/null; then
    echo "✓ 智能体运行中"
    ps aux | grep "autonomous_agent.py" | grep -v grep | awk '{print "  - " $NF " (PID: " $2 ")"}'
else
    echo "✗ 智能体未运行"
fi
echo ""

# 提示
echo "=========================================="
echo "监控提示:"
echo "=========================================="
echo "1. 如果当前话题状态是 'closing_pending'，等待第二个智能体同意关闭"
echo "2. 双方同意后，会自动触发 generate_new_topic 任务"
echo "3. 新话题应该是 LLM 生成的（不包含 'AI讨论话题' 字样）"
echo "4. 可以每隔 1-2 分钟运行此脚本查看进度"
echo ""
echo "实时监控命令:"
echo "  watch -n 30 './监控LLM话题生成.sh'"
echo ""
