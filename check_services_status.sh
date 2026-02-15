#!/bin/bash

# 服务状态检查脚本

echo "=========================================="
echo "双智能体对话平台 - 服务状态检查"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Redis
echo ""
echo "1. Redis 状态:"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ Redis 运行中${NC}"
else
    echo -e "   ${RED}✗ Redis 未运行${NC}"
fi

# 2. PostgreSQL
echo ""
echo "2. PostgreSQL 状态:"
if psql -h localhost -U postgres -d postgres -c "SELECT 1" > /dev/null 2>&1 || psql -h localhost -U $USER -d postgres -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ PostgreSQL 运行中${NC}"
else
    echo -e "   ${RED}✗ PostgreSQL 未运行${NC}"
fi

# 3. FastAPI
echo ""
echo "3. FastAPI 状态:"
API_PID=$(pgrep -f "uvicorn main:app" | head -1)
if [ -n "$API_PID" ]; then
    echo -e "   ${GREEN}✓ FastAPI 运行中 (PID: $API_PID)${NC}"
else
    echo -e "   ${RED}✗ FastAPI 未运行${NC}"
fi

# 4. Celery Worker
echo ""
echo "4. Celery Worker 状态:"
WORKER_COUNT=$(pgrep -f "celery.*worker" | wc -l)
if [ $WORKER_COUNT -gt 0 ]; then
    echo -e "   ${GREEN}✓ Celery Worker 运行中 ($WORKER_COUNT 进程)${NC}"
else
    echo -e "   ${RED}✗ Celery Worker 未运行${NC}"
fi

# 5. Celery Beat
echo ""
echo "5. Celery Beat 状态:"
BEAT_PID=$(pgrep -f "celery.*beat" | head -1)
if [ -n "$BEAT_PID" ]; then
    echo -e "   ${GREEN}✓ Celery Beat 运行中 (PID: $BEAT_PID)${NC}"
else
    echo -e "   ${RED}✗ Celery Beat 未运行${NC}"
fi

# 6. 智能体
echo ""
echo "6. 智能体状态:"
ALICE_PID=$(pgrep -f "autonomous_agent.py --agent alice" | head -1)
BOB_PID=$(pgrep -f "autonomous_agent.py --agent bob" | head -1)

if [ -n "$ALICE_PID" ]; then
    echo -e "   ${GREEN}✓ Agent-Alice 运行中 (PID: $ALICE_PID)${NC}"
else
    echo -e "   ${YELLOW}○ Agent-Alice 未运行${NC}"
fi

if [ -n "$BOB_PID" ]; then
    echo -e "   ${GREEN}✓ Agent-Bob 运行中 (PID: $BOB_PID)${NC}"
else
    echo -e "   ${YELLOW}○ Agent-Bob 未运行${NC}"
fi

# 7. Redis 队列状态
echo ""
echo "7. Redis 队列状态:"
python3 << 'PYEOF'
import redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    queues = ['default', 'summary_jobs', 'periodic_tasks']
    for queue in queues:
        length = r.llen(queue)
        status = "✓" if length < 10 else "⚠"
        print(f"   {status} {queue}: {length} tasks")
except Exception as e:
    print(f"   ✗ 无法连接 Redis: {e}")
PYEOF

# 8. 数据库状态
echo ""
echo "8. 数据库状态:"
python3 << 'PYEOF'
from models.database import SessionLocal
from models.models import Topic, Message, MessageRelevanceScore
from sqlalchemy import func

try:
    db = SessionLocal()
    
    # Active topics
    active_count = db.query(func.count(Topic.id)).filter(Topic.status == 'active').scalar()
    print(f"   活跃话题: {active_count}")
    
    # Total messages
    msg_count = db.query(func.count(Message.id)).scalar()
    print(f"   总消息数: {msg_count}")
    
    # Total scores
    score_count = db.query(func.count(MessageRelevanceScore.id)).scalar()
    print(f"   评分记录: {score_count}")
    
    # Pending summaries
    pending_count = db.query(func.count(Topic.id)).filter(Topic.pending_summary_job == True).scalar()
    if pending_count > 0:
        print(f"   ⚠ 待处理总结: {pending_count}")
    else:
        print(f"   ✓ 无待处理总结")
    
    db.close()
except Exception as e:
    print(f"   ✗ 数据库查询失败: {e}")
PYEOF

echo ""
echo "=========================================="
echo "检查完成"
echo "=========================================="
