#!/usr/bin/env python3
"""
同步本地数据到明宽服务器
"""
import psycopg2
from psycopg2.extras import execute_values
import sys

# 数据库配置
LOCAL_DB = "postgresql://dual_agent_user:dual_agent_pass@localhost:5432/dual_agent_chat"
REMOTE_DB = "postgresql://dual_agent_user:dual_agent_pass@129.211.28.211:5432/dual_agent_chat"

def main():
    print("=" * 50)
    print("同步数据到明宽服务器")
    print("=" * 50)
    
    try:
        # 连接本地数据库
        print("\n[1/4] 连接本地数据库...")
        local_conn = psycopg2.connect(LOCAL_DB)
        local_cur = local_conn.cursor()
        print("✓ 本地数据库连接成功")
        
        # 连接远程数据库
        print("\n[2/4] 连接远程数据库...")
        remote_conn = psycopg2.connect(REMOTE_DB)
        remote_cur = remote_conn.cursor()
        print("✓ 远程数据库连接成功")
        
        # 导出本地数据
        print("\n[3/4] 导出本地数据...")
        
        # 导出 agents
        local_cur.execute("SELECT id, name, auth_token_hash, created_at FROM agents ORDER BY id")
        agents = local_cur.fetchall()
        print(f"  - 智能体: {len(agents)} 条")
        
        # 导出 topics
        local_cur.execute("""
            SELECT id, title, topic_description, status, summary, llm_suggestion,
                   end_score, token_count_since_summary, summary_threshold,
                   last_summarized_message_id, pending_summary_job,
                   agent_a_wants_close, agent_b_wants_close,
                   closing_requested_by, closing_requested_at,
                   created_at, updated_at
            FROM topics ORDER BY created_at
        """)
        topics = local_cur.fetchall()
        print(f"  - 话题: {len(topics)} 条")
        
        # 导出 messages
        local_cur.execute("""
            SELECT id, topic_id, agent_id, content, actual_tokens, created_at
            FROM messages ORDER BY created_at
        """)
        messages = local_cur.fetchall()
        print(f"  - 消息: {len(messages)} 条")
        
        # 导入到远程数据库
        print("\n[4/4] 导入到远程数据库...")
        
        # 清空远程数据
        print("  - 清空现有数据...")
        remote_cur.execute("TRUNCATE TABLE messages, topics, agents RESTART IDENTITY CASCADE")
        remote_conn.commit()
        
        # 插入 agents
        if agents:
            print(f"  - 插入 {len(agents)} 个智能体...")
            execute_values(
                remote_cur,
                "INSERT INTO agents (id, name, auth_token_hash, created_at) VALUES %s",
                agents
            )
            remote_conn.commit()
        
        # 插入 topics
        if topics:
            print(f"  - 插入 {len(topics)} 个话题...")
            execute_values(
                remote_cur,
                """INSERT INTO topics (id, title, topic_description, status, summary, llm_suggestion,
                   end_score, token_count_since_summary, summary_threshold,
                   last_summarized_message_id, pending_summary_job,
                   agent_a_wants_close, agent_b_wants_close,
                   closing_requested_by, closing_requested_at,
                   created_at, updated_at) VALUES %s""",
                topics
            )
            remote_conn.commit()
        
        # 插入 messages
        if messages:
            print(f"  - 插入 {len(messages)} 条消息...")
            execute_values(
                remote_cur,
                "INSERT INTO messages (id, topic_id, agent_id, content, actual_tokens, created_at) VALUES %s",
                messages
            )
            remote_conn.commit()
        
        # 重置序列
        print("  - 重置序列...")
        remote_cur.execute("SELECT setval('agents_id_seq', COALESCE((SELECT MAX(id) FROM agents), 1))")
        remote_conn.commit()
        
        # 验证数据
        print("\n验证数据...")
        remote_cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM agents) as agent_count,
                (SELECT COUNT(*) FROM topics) as topic_count,
                (SELECT COUNT(*) FROM messages) as message_count
        """)
        counts = remote_cur.fetchone()
        print(f"  - 智能体: {counts[0]}")
        print(f"  - 话题: {counts[1]}")
        print(f"  - 消息: {counts[2]}")
        
        # 关闭连接
        local_cur.close()
        local_conn.close()
        remote_cur.close()
        remote_conn.close()
        
        print("\n" + "=" * 50)
        print("✓ 数据同步完成！")
        print("=" * 50)
        print("\n访问监控页面: http://129.211.28.211:8080/monitor.html")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
