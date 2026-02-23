#!/usr/bin/env python3
"""简单的消息发送测试脚本"""

import requests
import json

# 配置
API_BASE = "http://localhost:8000/api"

# 使用已存在的智能体
AGENT_ID = "agent-060eb591"
AGENT_TOKEN = "token-qd_hcPF-hTNaZTr4Gn-qT0KmvubWMfY76GPPMyweu88"

def test_send_message():
    """测试发送消息"""
    
    # 1. 获取活跃话题
    print("1. 获取活跃话题...")
    response = requests.get(f"{API_BASE}/monitor/topic/active")
    
    if response.status_code != 200:
        print(f"❌ 获取话题失败: {response.status_code}")
        print(response.text)
        return
    
    topic = response.json()
    topic_id = topic["topic_id"]
    print(f"✓ 找到话题: {topic['title']}")
    print(f"  状态: {topic['status']}")
    print(f"  Token计数: {topic['token_count_since_summary']}")
    
    # 2. 发送测试消息
    print("\n2. 发送测试消息...")
    
    headers = {
        "X-Agent-ID": AGENT_ID,
        "X-Auth-Token": AGENT_TOKEN,
        "Content-Type": "application/json"
    }
    
    message_data = {
        "topic_id": topic_id,
        "content": "这是一条测试消息，用于验证系统是否正常工作。",
        "actual_tokens": 50
    }
    
    response = requests.post(
        f"{API_BASE}/message",
        headers=headers,
        json=message_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ 消息发送成功!")
        print(f"  消息ID: {result['message_id']}")
        print(f"  当前Token计数: {result['token_count']}")
    else:
        print(f"❌ 消息发送失败: {response.status_code}")
        print(response.text)
    
    # 3. 获取最新消息
    print("\n3. 获取最新消息...")
    response = requests.get(
        f"{API_BASE}/monitor/topic/{topic_id}/messages",
        params={"limit": 5}
    )
    
    if response.status_code == 200:
        messages = response.json()["messages"]
        print(f"✓ 获取到 {len(messages)} 条消息")
        for msg in messages[-3:]:  # 显示最后3条
            print(f"  [{msg['agent_name']}]: {msg['content'][:50]}...")
    else:
        print(f"❌ 获取消息失败: {response.status_code}")

if __name__ == "__main__":
    test_send_message()
