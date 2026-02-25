#!/usr/bin/env python3
"""检查总结功能状态"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from services.system_config_service import SystemConfigService
from models.models import Topic, SummaryJob

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

config_service = SystemConfigService(db)

# 获取总结阈值
threshold = config_service.get_config_value('summary_threshold', 8000)
print(f'📊 总结触发阈值: {threshold} tokens')
print()

# 检查话题的 token 计数
topics = db.query(Topic).filter(Topic.status == 'active').order_by(Topic.token_count_since_summary.desc()).limit(10).all()

print(f'📈 活跃话题 Token 计数（前10）:')
print('=' * 90)
print(f"{'话题标题':40} | {'Tokens':>8} | {'消息数':>5} | {'待处理':>6} | {'建议':>12}")
print('=' * 90)
for topic in topics:
    status_icon = '🔥' if topic.token_count_since_summary >= threshold else '📝'
    pending = '是' if topic.pending_summary_job else '否'
    title = topic.title[:38] if len(topic.title) > 38 else topic.title
    suggestion = topic.llm_suggestion or '-'
    print(f'{status_icon} {title:38} | {topic.token_count_since_summary:8} | {len(topic.messages):5} | {pending:>6} | {suggestion:>12}')

print()

# 检查是否有话题达到阈值
over_threshold = [t for t in topics if t.token_count_since_summary >= threshold]
if over_threshold:
    print(f'⚠️  有 {len(over_threshold)} 个话题达到或超过阈值')
    for t in over_threshold:
        print(f'   - {t.title[:50]} (Tokens: {t.token_count_since_summary}, 待处理: {t.pending_summary_job})')
else:
    print(f'✓ 没有话题达到阈值')

print()

# 检查总结任务
summary_jobs = db.query(SummaryJob).order_by(SummaryJob.created_at.desc()).limit(5).all()
if summary_jobs:
    print(f'📋 最近 5 个总结任务:')
    print('=' * 90)
    for job in summary_jobs:
        topic = db.query(Topic).filter(Topic.id == job.topic_id).first()
        topic_title = topic.title[:30] if topic else 'Unknown'
        print(f'  {job.status:10} | {topic_title:30} | 创建: {job.created_at.strftime("%m-%d %H:%M")}')
else:
    print('⚠️  没有找到总结任务记录')

db.close()
