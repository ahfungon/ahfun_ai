#!/usr/bin/env python3
"""检查最近消息的评分情况"""
import sys
sys.path.insert(0, '.')
from models.database import SessionLocal
from models.models import Message, MessageRelevanceScore
from sqlalchemy import desc
from datetime import datetime, timedelta

db = SessionLocal()

# 最近10分钟的消息
ten_min_ago = datetime.utcnow() - timedelta(minutes=10)
recent = db.query(
    Message.id,
    Message.created_at,
    MessageRelevanceScore.relevance_score,
    MessageRelevanceScore.evaluated_at
).outerjoin(
    MessageRelevanceScore, Message.id == MessageRelevanceScore.message_id
).filter(
    Message.created_at >= ten_min_ago
).order_by(desc(Message.created_at)).limit(20).all()

print('最近10分钟的消息评分情况:')
print(f'{"创建时间":<20} {"评分":<8} {"评分时间":<20} {"延迟(秒)"}')
print('-' * 70)

scored = 0
unscored = 0
for m in recent:
    created = m.created_at.strftime('%H:%M:%S') if m.created_at else 'N/A'
    score = f'{m.relevance_score:.1f}' if m.relevance_score is not None else '未评分'
    evaluated = m.evaluated_at.strftime('%H:%M:%S') if m.evaluated_at else '-'
    
    if m.relevance_score is not None:
        scored += 1
        delay = (m.evaluated_at - m.created_at).total_seconds() if m.evaluated_at and m.created_at else 0
        print(f'{created:<20} {score:<8} {evaluated:<20} {delay:.1f}')
    else:
        unscored += 1
        print(f'{created:<20} {score:<8} {evaluated:<20} -')

print(f'\n统计: 已评分 {scored}/{scored+unscored} ({scored/(scored+unscored)*100:.1f}%)')

db.close()
