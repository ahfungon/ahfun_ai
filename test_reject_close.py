#!/usr/bin/env python3
"""测试拒绝关闭功能"""

import requests
import json
import sys
from pathlib import Path

API_BASE = "http://localhost:8000"

def load_agent_state(agent_key):
    """加载智能体状态"""
    state_file = Path(f"simulation_test/.agent_state/agent-{agent_key}.json")
    if not state_file.exists():
        print(f"❌ 找不到智能体状态文件: {state_file}")
        return None
    
    with open(state_file, 'r') as f:
        return json.load(f)

def get_headers(agent_state):
    """获取请求头"""
    return {
        "X-Agent-Id": agent_state['agent_id'],
        "X-Auth-Token": agent_state['auth_token']
    }

def get_active_topic(headers):
    """获取活跃话题"""
    response = requests.get(f"{API_BASE}/api/topic/active", headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

def test_reject_close():
    """测试拒绝关闭功能"""
    print("=" * 80)
    print("测试拒绝关闭功能")
    print("=" * 80)
    print()
    
    # 加载智能体状态
    print("📋 加载智能体状态...")
    alice_state = load_agent_state("alice")
    bob_state = load_agent_state("bob")
    
    if not alice_state or not bob_state:
        print("❌ 无法加载智能体状态")
        return 1
    
    alice_headers = get_headers(alice_state)
    bob_headers = get_headers(bob_state)
    
    print(f"  ✓ Alice: {alice_state['agent_id']}")
    print(f"  ✓ Bob: {bob_state['agent_id']}")
    print()
    
    # 获取活跃话题
    print("🔍 获取活跃话题...")
    topic = get_active_topic(alice_headers)
    
    if not topic:
        print("  ❌ 没有活跃话题")
        return 1
    
    topic_id = topic['topic_id']
    print(f"  ✓ 话题ID: {topic_id}")
    print(f"  ✓ 标题: {topic['title']}")
    print(f"  ✓ 当前状态: {topic['status']}")
    print()
    
    # 测试 1: Alice 请求关闭
    print("【测试 1】Alice 请求关闭")
    response = requests.post(
        f"{API_BASE}/api/topic/{topic_id}/request-close",
        headers=alice_headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"  ✓ 状态: {result['status']}")
        print(f"  ✓ 双方同意: {result['both_agreed']}")
        
        if result['status'] != 'closing_pending':
            print(f"  ❌ 预期状态为 closing_pending，实际为 {result['status']}")
            return 1
    else:
        print(f"  ❌ 请求失败: {response.status_code}")
        print(f"  {response.text}")
        return 1
    
    print()
    
    # 测试 2: Bob 拒绝关闭
    print("【测试 2】Bob 拒绝关闭")
    response = requests.post(
        f"{API_BASE}/api/topic/{topic_id}/reject-close",
        headers=bob_headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"  ✓ 状态: {result['status']}")
        print(f"  ✓ 消息: {result['message']}")
    else:
        print(f"  ❌ 请求失败: {response.status_code}")
        print(f"  {response.text}")
        return 1
    
    print()
    
    # 验证话题状态
    print("【验证】检查话题状态")
    topic = get_active_topic(alice_headers)
    
    if topic and topic['topic_id'] == topic_id:
        print(f"  ✓ 话题状态: {topic['status']}")
        
        if topic['status'] != 'active':
            print(f"  ❌ 预期状态为 active，实际为 {topic['status']}")
            return 1
        
        print(f"  ✓ 话题已恢复为 active 状态")
    else:
        print("  ❌ 无法获取话题或话题ID不匹配")
        return 1
    
    print()
    print("=" * 80)
    print("✅ 所有测试通过！")
    print("=" * 80)
    print()
    print("📝 测试总结：")
    print("  1. Alice 成功请求关闭 → closing_pending")
    print("  2. Bob 成功拒绝关闭 → active")
    print("  3. 话题状态正确恢复")
    print()
    
    return 0

def test_api_endpoint_exists():
    """测试 API 端点是否存在"""
    print("🔍 检查 API 端点...")
    
    # 尝试访问端点（不带认证，应该返回 401）
    response = requests.post(f"{API_BASE}/api/topic/test-id/reject-close")
    
    if response.status_code == 401:
        print("  ✓ reject-close 端点存在")
        return True
    elif response.status_code == 404:
        print("  ❌ reject-close 端点不存在")
        return False
    else:
        print(f"  ⚠️  意外的状态码: {response.status_code}")
        return True  # 端点存在，只是其他错误

def main():
    print()
    
    # 检查端点
    if not test_api_endpoint_exists():
        print()
        print("❌ API 端点不存在，请确保服务已重启")
        return 1
    
    print()
    
    # 运行测试
    try:
        return test_reject_close()
    except requests.exceptions.ConnectionError:
        print()
        print("❌ 无法连接到服务器")
        print("请确保服务正在运行: ./start_services.sh")
        return 1
    except Exception as e:
        print()
        print(f"❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
