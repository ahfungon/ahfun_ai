#!/usr/bin/env python3
"""诊断 MiniMax 配置和连接问题"""

import sys
import requests
from models.database import SessionLocal
from services.system_config_service import SystemConfigService

def diagnose_minimax():
    """诊断 MiniMax 配置"""
    print("=" * 60)
    print("MiniMax 配置诊断工具")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        service = SystemConfigService(db)
        
        # 1. 检查配置
        print("\n1️⃣ 检查系统配置")
        print("-" * 60)
        
        api_key = service.get_config_value('minimax_api_key', '')
        api_url = service.get_config_value('minimax_api_url', '')
        model = service.get_config_value('minimax_model', '')
        
        print(f"✓ MiniMax API Key: {'已配置 (' + api_key[:20] + '...)' if api_key else '❌ 未配置'}")
        print(f"✓ MiniMax API URL: {api_url}")
        print(f"✓ MiniMax Model: {model}")
        
        if not api_key:
            print("\n❌ 错误：MiniMax API Key 未配置！")
            print("请在系统配置页面配置 MiniMax API Key")
            return False
        
        # 2. 验证配置格式
        print("\n2️⃣ 验证配置格式")
        print("-" * 60)
        
        correct_url = "https://api.minimax.io/v1"
        correct_model = "MiniMax-M2.5"
        
        if api_url != correct_url:
            print(f"⚠️  API URL 不正确")
            print(f"   当前值: {api_url}")
            print(f"   应该是: {correct_url}")
        else:
            print(f"✓ API URL 正确")
        
        if model != correct_model and not model.startswith("MiniMax-"):
            print(f"⚠️  模型名称可能不正确")
            print(f"   当前值: {model}")
            print(f"   推荐值: {correct_model}")
        else:
            print(f"✓ 模型名称正确")
        
        # 3. 测试网络连接
        print("\n3️⃣ 测试网络连接")
        print("-" * 60)
        
        try:
            print(f"正在连接: {api_url}/chat/completions")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 10
            }
            
            response = requests.post(
                f"{api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            print(f"✓ HTTP 状态码: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ MiniMax API 调用成功！")
                data = response.json()
                if "choices" in data and data["choices"]:
                    content = data["choices"][0].get("message", {}).get("content", "")
                    print(f"✓ 响应内容: {content[:50]}...")
                return True
            
            elif response.status_code == 401:
                print("❌ 认证失败：API Key 无效或过期")
                print(f"   响应: {response.text[:200]}")
                return False
            
            elif response.status_code == 404:
                print("❌ 端点不存在：API URL 或端点路径错误")
                print(f"   响应: {response.text[:200]}")
                return False
            
            else:
                print(f"❌ API 调用失败")
                print(f"   响应: {response.text[:200]}")
                return False
        
        except requests.exceptions.ConnectionError as e:
            print(f"❌ 网络连接失败：无法连接到 {api_url}")
            print(f"   错误: {str(e)}")
            print("\n可能的原因：")
            print("   1. 网络连接问题")
            print("   2. 防火墙阻止")
            print("   3. API URL 错误")
            return False
        
        except requests.exceptions.Timeout:
            print(f"❌ 请求超时：连接到 {api_url} 超时")
            print("\n可能的原因：")
            print("   1. 网络速度慢")
            print("   2. API 服务响应慢")
            return False
        
        except Exception as e:
            print(f"❌ 未知错误: {str(e)}")
            return False
    
    finally:
        db.close()
    
    return False


def print_recommendations():
    """打印修复建议"""
    print("\n" + "=" * 60)
    print("修复建议")
    print("=" * 60)
    print("""
1. 检查系统配置
   - 访问: http://localhost:8080/system-config.html
   - 确认 MiniMax API URL: https://api.minimax.io/v1
   - 确认 MiniMax 模型: MiniMax-M2.5
   - 确认 MiniMax API Key 已配置

2. 验证 API Key
   - 登录 MiniMax 平台: https://platform.minimax.io
   - 检查 API Key 是否有效
   - 检查账户余额是否充足

3. 测试网络连接
   - 尝试访问: https://api.minimax.io
   - 检查防火墙设置
   - 如果在国内，可能需要特殊网络环境

4. 重启服务
   - 重启 Worker: pkill -f celery && python quick_start.py
   - 刷新浏览器: Ctrl+F5 或 Cmd+Shift+R

5. 查看详细日志
   - 浏览器控制台 (F12) -> Console 标签
   - 浏览器控制台 (F12) -> Network 标签
   - Worker 日志: tail -f logs/worker.log
""")


if __name__ == "__main__":
    print("\n")
    success = diagnose_minimax()
    
    if not success:
        print_recommendations()
        sys.exit(1)
    else:
        print("\n✅ 所有检查通过！MiniMax 配置正确。")
        sys.exit(0)
