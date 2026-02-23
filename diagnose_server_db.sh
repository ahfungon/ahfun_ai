#!/bin/bash

echo "=========================================="
echo "诊断服务器数据库"
echo "=========================================="

ssh -i ~/.ssh/mingkuan.pem ubuntu@129.211.28.211 << 'ENDSSH'
cd ~/dual-agent-chat
source venv/bin/activate

# 检查数据库表
echo "检查数据库表..."
python3 << 'ENDPYTHON'
from models.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()

print(f"\n数据库表列表 ({len(tables)} 个):")
for table in sorted(tables):
    print(f"  - {table}")

# 检查 message_relevance_scores 表
if 'message_relevance_scores' in tables:
    print("\n✓ message_relevance_scores 表存在")
    
    # 查询记录数
    from sqlalchemy.orm import Session
    from models.models import MessageRelevanceScore
    
    with Session(engine) as session:
        count = session.query(MessageRelevanceScore).count()
        print(f"  记录数: {count}")
else:
    print("\n❌ message_relevance_scores 表不存在！")

# 检查 messages 表
from sqlalchemy.orm import Session
from models.models import Message

with Session(engine) as session:
    count = session.query(Message).count()
    print(f"\n消息总数: {count}")
    
    # 获取最近的消息
    messages = session.query(Message).order_by(Message.created_at.desc()).limit(3).all()
    print("\n最近的消息:")
    for msg in messages:
        print(f"  - ID: {msg.id[:8]}... Agent: {msg.agent_id[:12]}... 内容: {msg.content[:30]}...")

ENDPYTHON

ENDSSH
