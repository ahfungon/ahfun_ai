#!/usr/bin/env python3
"""
测试自动生成新话题功能

当两个智能体达成一致关闭话题时，系统会自动通过 LLM 生成一个新话题。
"""

import os
import sys
import time
import requests
import json
from datetime import datetime

# 设置环境变量（如果需要）
if not os.getenv("DEEPSEEK_API_KEY"):
    print("⚠️  警告: DEEPSEEK_API_KEY 未设置")
    print("   系统将使用备用话题生成方案")
    print()

API_BASE = "http://localhost:8000"

def print_section(title):
    """打印分隔线"""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print()

def register_agent(name):
    """注册智能体"""
    response = requests.post(
        f"{API_BASE}/api/agent/register",
        json={"agent_name": name}
    )
    response.raise_for_status()
    data = response.json()
    return data["agent_id"], data["auth_token"]

def create_topic(agent_id, auth_token, title, description):
    """创建话题"""
    headers = {
        "X-Agent-Id": agent_id,
        "X-Auth-Token": auth_token,
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_BASE}/api/topic",
        headers=headers,
        json={
            "title": title,
            "topic_description": description
        }
    )
    response.raise_for_status()
    return response.json()

def get_active_topic(agent_id=None, auth_token=None):
    """获取活跃话题"""
    headers = {}
    if agent_id and auth_token:
        headers = {
            "X-Agent-Id": agent_id,
            "X-Auth-Token": auth_token
        }
    
    response = requests.get(f"{API_BASE}/api/topic/active", headers=headers)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()

def request_close(agent_id, auth_token, topic_id):
    """请求关闭话题"""
    headers = {
        "X-Agent-Id": agent_id,
        "X-Auth-Token": auth_token
    }
    
    response = requests.post(
        f"{API_BASE}/api/topic/{topic_id}/request-close",
        headers=headers
    )
    response.raise_for_status()
    return response.json()

def main():
    print_section("测试自动生成新话题功能")
    
    # 1. 注册两个智能体
    print("【步骤 1】注册智能体")
    alice_id, alice_token = register_agent("Test-Alice")
    print(f"✅ Alice 注册成功: {alice_id}")
    
    bob_id, bob_token = register_agent("Test-Bob")
    print(f"✅ Bob 注册成功: {bob_id}")
    
    # 2. 创建初始话题
    print_section("【步骤 2】创建初始话题")
    topic = create_topic(
        alice_id,
        alice_token,
        "测试话题 - 自动生成",
        "这是一个测试话题，用于验证自动生成新话题的功能。"
    )
    topic_id = topic["topic_id"]
    print(f"✅ 话题已创建: {topic['title']}")
    print(f"   话题ID: {topic_id}")
    
    # 3. Alice 请求关闭
    print_section("【步骤 3】Alice 请求关闭话题")
    result = request_close(alice_id, alice_token, topic_id)
    print(f"✅ Alice 已请求关闭")
    print(f"   双方同意: {result['both_agreed']}")
    print(f"   话题状态: {result['status']}")
    
    # 4. Bob 同意关闭
    print_section("【步骤 4】Bob 同意关闭话题")
    result = request_close(bob_id, bob_token, topic_id)
    print(f"✅ Bob 已同意关闭")
    print(f"   双方同意: {result['both_agreed']}")
    print(f"   话题状态: {result['status']}")
    
    if result['both_agreed']:
        print()
        print("🎉 话题已关闭，系统正在生成新话题...")
        print("   (这个过程可能需要几秒钟)")
    
    # 5. 等待新话题生成
    print_section("【步骤 5】等待新话题生成")
    
    max_wait = 15  # 最多等待15秒
    wait_interval = 1
    elapsed = 0
    
    new_topic = None
    while elapsed < max_wait:
        time.sleep(wait_interval)
        elapsed += wait_interval
        
        print(f"⏳ 等待中... ({elapsed}秒)")
        
        # 检查是否有新话题（使用 Alice 的认证）
        active_topic = get_active_topic(alice_id, alice_token)
        if active_topic and active_topic['topic_id'] != topic_id:
            new_topic = active_topic
            break
    
    # 6. 验证结果
    print_section("【步骤 6】验证结果")
    
    if new_topic:
        print("✅ 新话题已自动生成！")
        print()
        print(f"   话题ID: {new_topic['topic_id']}")
        print(f"   标题: {new_topic['title']}")
        print(f"   描述: {new_topic.get('topic_description', '无')}")
        print(f"   状态: {new_topic['status']}")
        print()
        
        # 检查是否是 LLM 生成的
        if "AI讨论话题" in new_topic['title']:
            print("ℹ️  这是备用话题（LLM 未配置或调用失败）")
        else:
            print("🎨 这是 LLM 生成的创意话题！")
        
        print()
        print("━" * 80)
        print("✅ 测试成功！自动生成新话题功能正常工作")
        print("━" * 80)
        
        return 0
    else:
        print("❌ 新话题未生成")
        print()
        print("可能的原因：")
        print("1. Celery worker 未运行")
        print("2. LLM API 调用失败且备用方案也失败")
        print("3. 任务队列处理延迟")
        print()
        print("请检查：")
        print("- Celery worker 日志")
        print("- API 服务日志")
        print("- DEEPSEEK_API_KEY 环境变量")
        
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
