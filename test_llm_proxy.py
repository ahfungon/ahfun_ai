#!/usr/bin/env python3
"""
测试 LLM 代理端点
"""
import requests
import json

def test_llm_proxy():
    """测试 LLM 代理端点"""
    
    print("=" * 60)
    print("测试 LLM 代理端点")
    print("=" * 60)
    
    # 测试 DeepSeek
    print("\n1. 测试 DeepSeek 代理...")
    try:
        response = requests.post(
            "http://localhost:8080/api/admin/llm/proxy",
            json={
                "provider": "deepseek",
                "messages": [
                    {"role": "user", "content": "你好，请用一句话介绍你自己。"}
                ],
                "temperature": 0.7,
                "max_tokens": 100
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ DeepSeek 代理成功")
            print(f"   响应: {data.get('content', '')[:100]}...")
            print(f"   Token 使用: {data.get('usage', {})}")
        else:
            print(f"❌ DeepSeek 代理失败: {response.status_code}")
            print(f"   错误: {response.text}")
    except Exception as e:
        print(f"❌ DeepSeek 代理异常: {e}")
    
    # 测试 MiniMax
    print("\n2. 测试 MiniMax 代理...")
    try:
        response = requests.post(
            "http://localhost:8080/api/admin/llm/proxy",
            json={
                "provider": "minimax",
                "messages": [
                    {"role": "user", "content": "你好，请用一句话介绍你自己。"}
                ],
                "temperature": 0.7,
                "max_tokens": 100
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ MiniMax 代理成功")
            print(f"   响应: {data.get('content', '')[:100]}...")
            print(f"   Token 使用: {data.get('usage', {})}")
        else:
            print(f"❌ MiniMax 代理失败: {response.status_code}")
            print(f"   错误: {response.text}")
    except Exception as e:
        print(f"❌ MiniMax 代理异常: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_llm_proxy()
