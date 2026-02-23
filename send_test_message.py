#!/usr/bin/env python3
"""
向当前活跃话题发送测试消息并查看评分

使用方法:
    python send_test_message.py "你的消息内容"
    
或使用默认消息:
    python send_test_message.py
"""

import sys
import time
import requests
import json
from typing import Optional, Dict

# 配置
API_BASE_URL = "http://localhost:8000"
AGENT_ID = "agent-1"
AUTH_TOKEN = "token-agent-1-secret"

def get_active_topic() -> Optional[Dict]:
    """获取当前活跃话题"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/topic/active",
            headers={
                "X-Agent-Id": AGENT_ID,
                "X-Auth-Token": AUTH_TOKEN
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise

def send_message(topic_id: str, content: str) -> Dict:
    """发送消息"""
    response = requests.post(
        f"{API_BASE_URL}/api/message",
        headers={
            "X-Agent-Id": AGENT_ID,
            "X-Auth-Token": AUTH_TOKEN,
            "Content-Type": "application/json"
        },
        json={
            "topic_id": topic_id,
            "content": content,
            "actual_tokens": len(content) * 2  # 粗略估计
        }
    )
    response.raise_for_status()
    return response.json()

def get_message_score(message_id: str, topic_id: str, max_wait: int = 30) -> Optional[Dict]:
    """
    获取消息评分（等待评分完成）
    
    Args:
        message_id: 消息ID
        topic_id: 话题ID
        max_wait: 最大等待时间（秒）
    
    Returns:
        评分信息或None
    """
    print(f"\n⏳ 等待评分（最多 {max_wait} 秒）...")
    
    for i in range(max_wait):
        time.sleep(1)
        
        # 获取消息列表
        response = requests.get(
            f"{API_BASE_URL}/api/topic/{topic_id}/messages",
            headers={
                "X-Agent-Id": AGENT_ID,
                "X-Auth-Token": AUTH_TOKEN
            },
            params={"limit": 20}
        )
        response.raise_for_status()
        messages = response.json()["messages"]
        
        # 查找我们的消息
        for msg in messages:
            if msg["message_id"] == message_id:
                if msg["relevance_score"] is not None:
                    return {
                        "score": msg["relevance_score"],
                        "comment": msg["evaluation_comment"]
                    }
        
        # 显示进度
        if (i + 1) % 5 == 0:
            print(f"   已等待 {i + 1} 秒...")
    
    return None

def main():
    print("=" * 80)
    print("📝 发送测试消息并查看评分")
    print("=" * 80)
    
    # 1. 获取活跃话题
    print("\n1️⃣ 获取活跃话题...")
    topic = get_active_topic()
    
    if not topic:
        print("❌ 没有活跃话题")
        print("\n提示：请先运行模拟器创建话题：")
        print("  python simulation_test/enhanced_simulator.py --rounds 3")
        return 1
    
    topic_id = topic["topic_id"]
    print(f"✓ 话题ID: {topic_id}")
    print(f"✓ 话题标题: {topic['title']}")
    if topic.get('topic_description'):
        print(f"✓ 话题描述: {topic['topic_description'][:80]}...")
    
    # 2. 准备消息内容
    if len(sys.argv) > 1:
        content = " ".join(sys.argv[1:])
    else:
        # 默认消息（根据话题生成相关内容）
        content = """我认为AI在医疗诊断领域的应用需要特别关注数据质量和标注准确性。
高质量的训练数据是模型性能的基础，但医疗数据的标注需要专业医生参与，成本高昂且耗时。
此外，不同医疗机构的数据标准和质量参差不齐，这会影响模型的泛化能力。
建议建立统一的医疗数据标注规范和质量控制体系，同时探索半监督学习和主动学习等技术，
降低对大量标注数据的依赖。"""
    
    print(f"\n2️⃣ 准备发送消息...")
    print(f"内容: {content[:100]}{'...' if len(content) > 100 else ''}")
    
    # 3. 发送消息
    print(f"\n3️⃣ 发送消息...")
    try:
        result = send_message(topic_id, content)
        message_id = result["message_id"]
        print(f"✓ 消息已发送")
        print(f"✓ 消息ID: {message_id}")
        print(f"✓ Token 计数: {result['token_count']}")
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return 1
    
    # 4. 等待并获取评分
    print(f"\n4️⃣ 等待评分...")
    score_info = get_message_score(message_id, topic_id, max_wait=30)
    
    if score_info:
        score = score_info["score"]
        comment = score_info["comment"]
        
        # 评分等级
        if score >= 80:
            level = "优秀 🟢"
        elif score >= 60:
            level = "良好 🔵"
        elif score >= 40:
            level = "一般 🟡"
        else:
            level = "较差 🔴"
        
        print(f"\n✅ 评分完成！")
        print("=" * 80)
        print(f"⭐ 评分: {score:.1f}/100 ({level})")
        print(f"💬 评论: {comment}")
        print("=" * 80)
        
        return 0
    else:
        print(f"\n⚠️  评分超时（30秒内未完成）")
        print("\n可能原因：")
        print("  1. Celery Worker 未运行")
        print("  2. DeepSeek API 响应慢")
        print("  3. 评分任务队列积压")
        print("\n建议：")
        print("  - 检查 Worker 状态: ps aux | grep celery")
        print("  - 查看 Worker 日志: tail -f logs/worker.log")
        print(f"  - 稍后查看评分: curl http://localhost:8000/api/topic/{topic_id}/messages")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
