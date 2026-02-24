#!/usr/bin/env python3
"""测试 API Key 配置功能"""
import requests
import json

BASE_URL = "http://localhost:8080/api"

print("=" * 60)
print("测试 API Key 配置功能")
print("=" * 60)
print()

# 测试1: 获取当前 API Key 状态
print("测试1: 获取当前 API Key 状态")
print("-" * 60)
try:
    response = requests.get(f"{BASE_URL}/admin/config/api-key")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"是否已配置: {data['is_configured']}")
        print(f"掩码后的 Key: {data.get('masked_key', 'N/A')}")
        print(f"API URL: {data['api_url']}")
        print(f"模型: {data['model']}")
        print("✅ 测试通过")
    else:
        print(f"❌ 测试失败: {response.text}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

print()

# 测试2: 更新 API Key（使用测试 Key）
print("测试2: 更新 API Key（模拟）")
print("-" * 60)
print("⚠️  跳过实际更新测试（避免修改真实配置）")
print("如需测试，请手动调用:")
print(f"curl -X POST {BASE_URL}/admin/config/api-key \\")
print("  -H 'Content-Type: application/json' \\")
print("  -d '{\"api_key\": \"sk-test123456789012345678\"}'")

print()

# 测试3: 验证错误处理
print("测试3: 验证错误处理")
print("-" * 60)

test_cases = [
    ("空 API Key", {"api_key": ""}),
    ("无效格式（不以sk-开头）", {"api_key": "invalid-key"}),
    ("太短的 Key", {"api_key": "sk-short"}),
]

for desc, payload in test_cases:
    print(f"\n测试场景: {desc}")
    try:
        response = requests.post(
            f"{BASE_URL}/admin/config/api-key",
            json=payload
        )
        if response.status_code == 400:
            error = response.json()
            print(f"✅ 正确返回 400: {error['detail']}")
        else:
            print(f"⚠️  预期 400，实际 {response.status_code}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
