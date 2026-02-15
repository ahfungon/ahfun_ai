#!/bin/bash
set -e

SERVER_IP="129.211.28.211"
SERVER_USER="ubuntu"
SSH_KEY="~/.ssh/mingkuan.pem"

echo "=========================================="
echo "通过 SSH 同步数据到明宽服务器"
echo "=========================================="

# 1. 导出本地数据为 JSON
echo ""
echo "[1/3] 导出本地数据..."
python3 << 'EOPY'
import psycopg2
import json
from datetime import datetime

def json_serial(obj):
    """JSON serializer for datetime objects"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# 连接本地数据库
conn = psycopg2.connect('postgresql://dual_agent_user:dual_agent_pass@localhost:5432/dual_agent_chat')
cur = conn.cursor()

data = {}

# 导出 agents
cur.execute("SELECT id, name, auth_token_hash, created_at FROM agents ORDER BY id")
data['agents'] = [
    {'id': r[0], 'name': r[1], 'auth_token_hash': r[2], 'created_at': r[3]}
    for r in cur.fetchall()
]
print(f"导出 {len(data['agents'])} 个智能体")

# 导出 topics
cur.execute("""
    SELECT id, title, topic_description, status, summary, llm_suggestion,
           end_score, token_count_since_summary, summary_threshold,
           last_summarized_message_id, pending_summary_job,
           agent_a_wants_close, agent_b_wants_close,
           closing_requested_by, closing_requested_at,
           created_at, updated_at
    FROM topics ORDER BY created_at
""")
data['topics'] = [
    {
        'id': str(r[0]), 'title': r[1], 'topic_description': r[2], 'status': r[3],
        'summary': r[4], 'llm_suggestion': r[5], 'end_score': r[6],
        'token_count_since_summary': r[7], 'summary_threshold': r[8],
        'last_summarized_message_id': str(r[9]) if r[9] else None,
        'pending_summary_job': r[10], 'agent_a_wants_close': r[11],
        'agent_b_wants_close': r[12], 'closing_requested_by': r[13],
        'closing_requested_at': r[14], 'created_at': r[15], 'updated_at': r[16]
    }
    for r in cur.fetchall()
]
print(f"导出 {len(data['topics'])} 个话题")

# 导出 messages
cur.execute("""
    SELECT id, topic_id, agent_id, content, actual_tokens, created_at
    FROM messages ORDER BY created_at
""")
data['messages'] = [
    {
        'id': str(r[0]), 'topic_id': str(r[1]), 'agent_id': r[2],
        'content': r[3], 'actual_tokens': r[4], 'created_at': r[5]
    }
    for r in cur.fetchall()
]
print(f"导出 {len(data['messages'])} 条消息")

conn.close()

# 保存为 JSON
with open('data_export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, default=json_serial, ensure_ascii=False, indent=2)

print("✓ 数据导出到 data_export.json")
EOPY

# 2. 上传数据文件和导入脚本
echo ""
echo "[2/3] 上传数据到服务器..."
scp -i ${SSH_KEY} data_export.json ${SERVER_USER}@${SERVER_IP}:~/dual-agent-chat/

# 创建导入脚本
cat > import_data.py << 'EOPY'
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
EOPY

scp -i ${SSH_KEY} import_data.py ${SERVER_USER}@${SERVER_IP}:~/dual-agent-chat/

# 3. 在服务器上执行导入
echo ""
echo "[3/3] 在服务器上导入数据..."
ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd ~/dual-agent-chat
source venv/bin/activate
python3 import_data.py

echo ""
echo "重启服务..."
sudo systemctl restart dual-agent-api
sudo systemctl restart dual-agent-celery
sudo systemctl restart dual-agent-celery-beat
echo "✓ 服务已重启"
ENDSSH

# 4. 验证
echo ""
echo "=========================================="
echo "验证结果"
echo "=========================================="
sleep 3

curl -s http://${SERVER_IP}:8080/api/topics | jq '.topics | length' | xargs -I {} echo "话题数: {}"

echo ""
echo "=========================================="
echo "✓ 同步完成！"
echo "=========================================="
echo ""
echo "访问监控页面: http://${SERVER_IP}:8080/monitor.html"
