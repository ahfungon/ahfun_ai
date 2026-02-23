#!/usr/bin/env python3
"""测试服务器消息查询"""

import requests

# 测试获取消息
topic_id = "fe6f0ca0-03e9-4aee-bef4-203afe91146f"

print("测试1: 获取话题信息")
response = requests.get(f"http://129.211.28.211:8080/api/monitor/topic/active")
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"话题: {data['title']}")
    print(f"Token计数: {data['token_count_since_summary']}")
else:
    print(f"错误: {response.text}")

print("\n测试2: 获取消息列表")
response = requests.get(f"http://129.211.28.211:8080/api/monitor/topic/{topic_id}/messages?limit=5")
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"消息数量: {len(data['messages'])}")
    for msg in data['messages']:
        print(f"  - {msg['agent_name']}: {msg['content'][:50]}...")
else:
    print(f"错误: {response.text}")

print("\n测试3: 获取统计信息")
response = requests.get(f"http://129.211.28.211:8080/api/admin/stats")
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"消息总数: {data['messages']['total']}")
    print(f"智能体总数: {data['agents']['total']}")
else:
    print(f"错误: {response.text}")
