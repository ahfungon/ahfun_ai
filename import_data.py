#!/usr/bin/env python3
import psycopg2
from psycopg2.extras import execute_values
import json
from datetime import datetime

def parse_datetime(dt_str):
    """Parse ISO format datetime string"""
    if dt_str:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    return None

# 读取数据
with open('data_export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"读取数据: {len(data['agents'])} 智能体, {len(data['topics'])} 话题, {len(data['messages'])} 消息")

# 连接数据库
conn = psycopg2.connect('postgresql://dual_agent_user:dual_agent_pass@localhost:5432/dual_agent_chat')
cur = conn.cursor()

# 清空数据
print("清空现有数据...")
cur.execute("TRUNCATE TABLE messages, topics, agents RESTART IDENTITY CASCADE")
conn.commit()

# 插入 agents
if data['agents']:
    print(f"插入 {len(data['agents'])} 个智能体...")
    agents_data = [
        (a['id'], a['name'], a['auth_token_hash'], parse_datetime(a['created_at']))
        for a in data['agents']
    ]
    execute_values(
        cur,
        "INSERT INTO agents (id, name, auth_token_hash, created_at) VALUES %s",
        agents_data
    )
    conn.commit()

# 插入 topics
if data['topics']:
    print(f"插入 {len(data['topics'])} 个话题...")
    topics_data = [
        (
            t['id'], t['title'], t['topic_description'], t['status'],
            t['summary'], t['llm_suggestion'], t['end_score'],
            t['token_count_since_summary'], t['summary_threshold'],
            t['last_summarized_message_id'], t['pending_summary_job'],
            t['agent_a_wants_close'], t['agent_b_wants_close'],
            t['closing_requested_by'], parse_datetime(t['closing_requested_at']),
            parse_datetime(t['created_at']), parse_datetime(t['updated_at'])
        )
        for t in data['topics']
    ]
    execute_values(
        cur,
        """INSERT INTO topics (id, title, topic_description, status, summary, llm_suggestion,
           end_score, token_count_since_summary, summary_threshold,
           last_summarized_message_id, pending_summary_job,
           agent_a_wants_close, agent_b_wants_close,
           closing_requested_by, closing_requested_at,
           created_at, updated_at) VALUES %s""",
        topics_data
    )
    conn.commit()

# 插入 messages
if data['messages']:
    print(f"插入 {len(data['messages'])} 条消息...")
    messages_data = [
        (
            m['id'], m['topic_id'], m['agent_id'],
            m['content'], m['actual_tokens'], parse_datetime(m['created_at'])
        )
        for m in data['messages']
    ]
    execute_values(
        cur,
        "INSERT INTO messages (id, topic_id, agent_id, content, actual_tokens, created_at) VALUES %s",
        messages_data
    )
    conn.commit()

# agents 使用 UUID，不需要重置序列
print("数据导入完成，跳过序列重置（使用 UUID）")

# 验证
cur.execute("""
    SELECT 
        (SELECT COUNT(*) FROM agents) as agent_count,
        (SELECT COUNT(*) FROM topics) as topic_count,
        (SELECT COUNT(*) FROM messages) as message_count
""")
counts = cur.fetchone()
print(f"\n验证: {counts[0]} 智能体, {counts[1]} 话题, {counts[2]} 消息")

cur.close()
conn.close()
print("✓ 数据导入完成")
