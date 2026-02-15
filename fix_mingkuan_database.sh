#!/bin/bash
set -e

SERVER_IP="129.211.28.211"
SERVER_USER="ubuntu"
SSH_KEY="~/.ssh/mingkuan.pem"

echo "=========================================="
echo "修复明宽服务器数据库"
echo "=========================================="

# 1. 在服务器上运行 Alembic 迁移创建表结构
echo ""
echo "[1/3] 在服务器上创建数据库表结构..."
ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd ~/dual-agent-chat
source venv/bin/activate

# 检查 Alembic 是否初始化
if [ -d "alembic" ]; then
    echo "运行 Alembic 迁移..."
    alembic upgrade head
    echo "✓ 数据库表结构创建完成"
else
    echo "✗ Alembic 未初始化"
    exit 1
fi

# 验证表是否创建
echo ""
echo "验证表结构..."
PGPASSWORD='dual_agent_pass' psql -h localhost -U dual_agent_user -d dual_agent_chat -c "\dt"
ENDSSH

# 2. 导出本地数据（仅数据，不包含表结构）
echo ""
echo "[2/3] 导出本地数据..."
python3 << 'EOPY'
import psycopg2
import json

# 连接本地数据库
conn = psycopg2.connect('postgresql://dual_agent_user:dual_agent_pass@localhost:5432/dual_agent_chat')
cur = conn.cursor()

# 导出 agents
cur.execute("SELECT id, name, auth_token_hash, created_at FROM agents ORDER BY id")
agents = cur.fetchall()
print(f"导出 {len(agents)} 个智能体")

# 导出 topics
cur.execute("""
    SELECT id, title, topic_description, status, summary, llm_suggestion, 
           end_score, token_count_since_summary, summary_threshold, 
           last_summarized_message_id, pending_summary_job,
           agent_a_wants_close, agent_b_wants_close, 
           closing_requested_by, closing_requested_at,
           created_at, updated_at 
    FROM topics ORDER BY id
""")
topics = cur.fetchall()
print(f"导出 {len(topics)} 个话题")

# 导出 messages
cur.execute("""
    SELECT id, topic_id, agent_id, content, actual_tokens, created_at 
    FROM messages ORDER BY id
""")
messages = cur.fetchall()
print(f"导出 {len(messages)} 条消息")

conn.close()

# 生成 SQL 插入语句
with open('data_export.sql', 'w', encoding='utf-8') as f:
    f.write("-- 清空现有数据\n")
    f.write("TRUNCATE TABLE messages, topics, agents RESTART IDENTITY CASCADE;\n\n")
    
    # 插入 agents
    f.write("-- 插入智能体\n")
    for agent in agents:
        token_hash = agent[2].replace("'", "''") if agent[2] else ''
        f.write(f"INSERT INTO agents (id, name, auth_token_hash, created_at) VALUES ({agent[0]}, '{agent[1]}', '{token_hash}', '{agent[3]}');\n")
    
    # 插入 topics
    f.write("\n-- 插入话题\n")
    for topic in topics:
        title = topic[1].replace("'", "''") if topic[1] else ''
        desc = topic[2].replace("'", "''") if topic[2] else ''
        summary = topic[4].replace("'", "''") if topic[4] else ''
        llm_sugg = topic[5].replace("'", "''") if topic[5] else ''
        
        f.write(f"""INSERT INTO topics (id, title, topic_description, status, summary, llm_suggestion, 
                end_score, token_count_since_summary, summary_threshold, 
                last_summarized_message_id, pending_summary_job,
                agent_a_wants_close, agent_b_wants_close, 
                closing_requested_by, closing_requested_at,
                created_at, updated_at) 
                VALUES ('{topic[0]}', '{title}', '{desc}', '{topic[3]}', '{summary}', '{llm_sugg}',
                {topic[6] if topic[6] else 'NULL'}, {topic[7]}, {topic[8]},
                {f"'{topic[9]}'" if topic[9] else 'NULL'}, {topic[10]},
                {topic[11]}, {topic[12]},
                {f"'{topic[13]}'" if topic[13] else 'NULL'}, {f"'{topic[14]}'" if topic[14] else 'NULL'},
                '{topic[15]}', '{topic[16]}');\n""")
    
    # 插入 messages
    f.write("\n-- 插入消息\n")
    for msg in messages:
        content = msg[3].replace("'", "''") if msg[3] else ''
        f.write(f"""INSERT INTO messages (id, topic_id, agent_id, content, actual_tokens, created_at) 
                VALUES ('{msg[0]}', '{msg[1]}', {msg[2]}, '{content}', {msg[4] if msg[4] else 'NULL'}, '{msg[5]}');\n""")
    
    # 重置序列（agents 使用整数 ID，不需要重置 UUID）
    f.write("\n-- 重置序列\n")
    f.write("SELECT setval('agents_id_seq', COALESCE((SELECT MAX(id) FROM agents), 1));\n")

print("\n✓ 数据导出到 data_export.sql")
EOPY

# 3. 上传并导入数据
echo ""
echo "[3/3] 上传并导入数据到服务器..."
scp -i ${SSH_KEY} data_export.sql ${SERVER_USER}@${SERVER_IP}:~/dual-agent-chat/

ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd ~/dual-agent-chat

echo "导入数据..."
PGPASSWORD='dual_agent_pass' psql -h localhost -U dual_agent_user -d dual_agent_chat -f data_export.sql

echo ""
echo "验证数据..."
PGPASSWORD='dual_agent_pass' psql -h localhost -U dual_agent_user -d dual_agent_chat -c "
SELECT 
    (SELECT COUNT(*) FROM agents) as agent_count,
    (SELECT COUNT(*) FROM topics) as topic_count,
    (SELECT COUNT(*) FROM messages) as message_count;
"

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
echo "验证修复结果"
echo "=========================================="
sleep 3

echo ""
echo "检查 API 健康状态..."
curl -s http://${SERVER_IP}:8080/api/health | jq .

echo ""
echo "检查话题列表..."
curl -s http://${SERVER_IP}:8080/api/topics | jq '.topics | length' | xargs -I {} echo "话题数: {}"

echo ""
echo "=========================================="
echo "修复完成！"
echo "=========================================="
echo ""
echo "访问监控页面: http://${SERVER_IP}:8080/monitor.html"
