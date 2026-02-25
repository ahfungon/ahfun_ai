#!/usr/bin/env python3
"""直接测试 MiniMax API 调用"""

import requests
import json
from models.database import SessionLocal
from services.system_config_service import SystemConfigService

def test_minimax_api():
    """测试 MiniMax API 的各种可能配置"""
    
    print("=" * 70)
    print("MiniMax API 直接测试")
    print("=" * 70)
    
    # 从数据库获取配置
    db = SessionLocal()
    try:
        service = SystemConfigService(db)
        api_key = service.get_config_value('minimax_api_key', '')
        
        if not api_key:
            print("❌ 错误：未配置 MiniMax API Key")
            return
        
        print(f"\n📋 使用的 API Key: {api_key[:20]}...{api_key[-10:]}")
        print(f"📋 API Key 长度: {len(api_key)} 字符")
        print(f"📋 API Key 开头: {api_key[:10]}")
        
    finally:
        db.close()
    
    # 测试配置列表
    test_configs = [
        {
            "name": "配置1: OpenAI 兼容格式 (api.minimax.io)",
            "base_url": "https://api.minimax.io/v1",
            "endpoint": "/chat/completions",
            "model": "MiniMax-M2.5",
            "format": "openai"
        },
        {
            "name": "配置2: 原生格式 (api.minimax.io)",
            "base_url": "https://api.minimax.io/v1",
            "endpoint": "/text/chatcompletion_v2",
            "model": "MiniMax-M2.5",
            "format": "native"
        },
        {
            "name": "配置3: 旧域名 OpenAI 格式 (api.minimax.chat)",
            "base_url": "https://api.minimax.chat/v1",
            "endpoint": "/chat/completions",
            "model": "MiniMax-M2.5",
            "format": "openai"
        },
        {
            "name": "配置4: 旧域名原生格式 (api.minimax.chat)",
            "base_url": "https://api.minimax.chat/v1",
            "endpoint": "/text/chatcompletion_v2",
            "model": "MiniMax-M2.5",
            "format": "native"
        },
        {
            "name": "配置5: 旧模型名称 (abab6.5-chat)",
            "base_url": "https://api.minimax.io/v1",
            "endpoint": "/chat/completions",
            "model": "abab6.5-chat",
            "format": "openai"
        },
    ]
    
    for i, config in enumerate(test_configs, 1):
        print(f"\n{'=' * 70}")
        print(f"测试 {i}/{len(test_configs)}: {config['name']}")
        print(f"{'=' * 70}")
        
        url = f"{config['base_url']}{config['endpoint']}"
        print(f"🔗 URL: {url}")
        print(f"🤖 Model: {config['model']}")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体
        if config['format'] == 'openai':
            payload = {
                "model": config['model'],
                "messages": [
                    {"role": "user", "content": "Say 'Hello' in one word"}
                ],
                "max_tokens": 10,
                "temperature": 0.7
            }
        else:  # native format
            payload = {
                "model": config['model'],
                "messages": [
                    {"role": "user", "content": "Say 'Hello' in one word"}
                ],
                "max_tokens": 10,
                "temperature": 0.7
            }
        
        try:
            print(f"📤 发送请求...")
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            print(f"📥 状态码: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ 成功！")
                try:
                    data = response.json()
                    print(f"📄 响应数据结构: {list(data.keys())}")
                    
                    if "choices" in data and data["choices"]:
                        content = data["choices"][0].get("message", {}).get("content", "")
                        print(f"💬 响应内容: {content}")
                        print(f"\n🎉 这个配置可以工作！")
                        print(f"✓ 推荐使用:")
                        print(f"  - Base URL: {config['base_url']}")
                        print(f"  - Endpoint: {config['endpoint']}")
                        print(f"  - Model: {config['model']}")
                        return config
                    else:
                        print(f"⚠️  响应格式异常: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                except json.JSONDecodeError:
                    print(f"⚠️  无法解析 JSON 响应: {response.text[:200]}")
            
            elif response.status_code == 401:
                print(f"❌ 认证失败 (401)")
                try:
                    error_data = response.json()
                    print(f"📄 错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except:
                    print(f"📄 错误响应: {response.text[:200]}")
            
            elif response.status_code == 404:
                print(f"❌ 端点不存在 (404)")
                print(f"📄 响应: {response.text[:200]}")
            
            else:
                print(f"❌ 请求失败 ({response.status_code})")
                print(f"📄 响应: {response.text[:200]}")
        
        except requests.exceptions.ConnectionError as e:
            print(f"❌ 连接失败: {str(e)[:100]}")
        
        except requests.exceptions.Timeout:
            print(f"❌ 请求超时")
        
        except Exception as e:
            print(f"❌ 未知错误: {str(e)[:100]}")
    
    print(f"\n{'=' * 70}")
    print("❌ 所有配置都失败了")
    print("=" * 70)
    print("\n建议:")
    print("1. 检查 API Key 是否正确")
    print("2. 检查网络连接")
    print("3. 访问 MiniMax 官方文档确认正确的 API 格式")
    print("4. 联系 MiniMax 技术支持")
    
    return None


def test_with_curl():
    """生成 curl 命令用于手动测试"""
    
    db = SessionLocal()
    try:
        service = SystemConfigService(db)
        api_key = service.get_config_value('minimax_api_key', '')
        
        if not api_key:
            print("❌ 错误：未配置 MiniMax API Key")
            return
        
        print("\n" + "=" * 70)
        print("手动测试命令 (curl)")
        print("=" * 70)
        
        print("\n测试 1: OpenAI 兼容格式")
        print("-" * 70)
        curl_cmd = f'''curl -X POST https://api.minimax.io/v1/chat/completions \\
  -H "Authorization: Bearer {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "model": "MiniMax-M2.5",
    "messages": [
      {{"role": "user", "content": "Say hello"}}
    ],
    "max_tokens": 10
  }}'
'''
        print(curl_cmd)
        
        print("\n测试 2: 原生格式")
        print("-" * 70)
        curl_cmd2 = f'''curl -X POST https://api.minimax.io/v1/text/chatcompletion_v2 \\
  -H "Authorization: Bearer {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "model": "MiniMax-M2.5",
    "messages": [
      {{"role": "user", "content": "Say hello"}}
    ],
    "max_tokens": 10
  }}'
'''
        print(curl_cmd2)
        
    finally:
        db.close()


if __name__ == "__main__":
    print("\n")
    
    # 运行测试
    working_config = test_minimax_api()
    
    # 生成 curl 命令
    test_with_curl()
    
    if working_config:
        print(f"\n{'=' * 70}")
        print("✅ 找到可用的配置！")
        print(f"{'=' * 70}")
        print(f"\n请更新系统配置:")
        print(f"  MiniMax API URL: {working_config['base_url']}")
        print(f"  MiniMax 模型: {working_config['model']}")
        print(f"\n然后重启 Worker 和刷新浏览器。")
    else:
        print(f"\n{'=' * 70}")
        print("❌ 未找到可用的配置")
        print(f"{'=' * 70}")
        print("\n请:")
        print("1. 检查上面的错误信息")
        print("2. 尝试运行上面的 curl 命令手动测试")
        print("3. 查看 MiniMax 官方文档")
