#!/usr/bin/env python3
"""Test script to diagnose message scoring issue."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check DeepSeek API Key
deepseek_key = os.getenv("DEEPSEEK_API_KEY")

print("=" * 60)
print("消息评分功能诊断报告")
print("=" * 60)
print()

print("1. DeepSeek API Key 配置检查:")
print(f"   API Key: {deepseek_key}")
print()

if not deepseek_key or deepseek_key == "your_deepseek_api_key_here":
    print("❌ 问题发现：DeepSeek API Key 未配置或使用占位符")
    print()
    print("解决方案：")
    print("1. 获取 DeepSeek API Key:")
    print("   - 访问 https://platform.deepseek.com/")
    print("   - 注册/登录账号")
    print("   - 在 API Keys 页面创建新的 API Key")
    print()
    print("2. 配置 API Key 到 .env 文件:")
    print("   编辑 .env 文件，将以下行：")
    print("   DEEPSEEK_API_KEY=your_deepseek_api_key_here")
    print("   替换为：")
    print("   DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx")
    print()
    print("3. 重启 Celery Worker:")
    print("   pkill -f 'celery.*worker'")
    print("   python quick_start.py")
    print()
else:
    print("✅ DeepSeek API Key 已配置")
    print()
    print("2. 测试 API Key 有效性:")
    print("   正在测试...")
    
    try:
        from services.llm_clients.deepseek_client import DeepSeekClient
        
        client = DeepSeekClient(
            api_key=deepseek_key,
            api_url=os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
        )
        
        # Simple test prompt
        test_prompt = """请评估以下发言的相关性（0-100分）：
主题：人工智能的未来
发言：我认为AI将改变世界

返回JSON格式：
{
  "relevance_score": 90,
  "evaluation_comment": "紧扣主题"
}"""
        
        result = client.evaluate_message_relevance(test_prompt)
        
        if result:
            print(f"   ✅ API Key 有效")
            print(f"   测试结果: score={result.get('relevance_score')}, comment={result.get('evaluation_comment')}")
        else:
            print(f"   ❌ API 调用失败（可能是 API Key 无效或网络问题）")
    
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")

print()
print("=" * 60)
