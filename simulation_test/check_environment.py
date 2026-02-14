#!/usr/bin/env python3
"""
环境检查脚本

在运行测试之前，检查所有必要的服务和配置是否正确。
"""

import sys
import requests
from config import API_BASE_URL, AGENT_1_ID, AGENT_1_TOKEN


def print_status(check_name, success, message=""):
    """打印检查状态"""
    status = "✅" if success else "❌"
    print(f"{status} {check_name}", end="")
    if message:
        print(f": {message}")
    else:
        print()


def check_api_connection():
    """检查 API 连接"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200
    except Exception as e:
        return False


def check_health_endpoint():
    """检查健康检查端点"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("status") == "ok", data
        return False, None
    except Exception as e:
        return False, None


def check_authentication():
    """检查认证"""
    try:
        headers = {
            "X-Agent-Id": AGENT_1_ID,
            "X-Auth-Token": AGENT_1_TOKEN
        }
        response = requests.get(f"{API_BASE_URL}/api/topic/active", headers=headers, timeout=5)
        # 401 表示认证失败，404 表示认证成功但没有活跃话题
        return response.status_code in [200, 404]
    except Exception as e:
        return False


def check_dependencies():
    """检查 Python 依赖"""
    try:
        import requests
        return True
    except ImportError:
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  双智能体对话模拟测试 - 环境检查")
    print("="*60 + "\n")
    
    all_checks_passed = True
    
    # 检查 1: Python 依赖
    print("1. 检查 Python 依赖...")
    deps_ok = check_dependencies()
    print_status("   requests 库", deps_ok)
    if not deps_ok:
        print("   💡 运行: pip install -r requirements.txt")
        all_checks_passed = False
    print()
    
    # 检查 2: API 连接
    print("2. 检查后端 API 连接...")
    print(f"   API 地址: {API_BASE_URL}")
    api_ok = check_api_connection()
    print_status("   API 可访问", api_ok)
    if not api_ok:
        print("   💡 确保后端服务正在运行: python main.py")
        all_checks_passed = False
    print()
    
    # 检查 3: 健康检查
    if api_ok:
        print("3. 检查系统健康状态...")
        health_ok, health_data = check_health_endpoint()
        print_status("   健康检查端点", health_ok)
        
        if health_ok and health_data:
            services = health_data.get("services", {})
            for service, status in services.items():
                service_ok = status.get("status") == "healthy"
                print_status(f"   - {service}", service_ok, status.get("message", ""))
                if not service_ok:
                    all_checks_passed = False
        elif not health_ok:
            print("   ⚠️  健康检查失败，但可能不影响基本测试")
        print()
    else:
        print("3. 跳过健康检查（API 不可访问）\n")
        all_checks_passed = False
    
    # 检查 4: 认证
    if api_ok:
        print("4. 检查 Agent 认证...")
        print(f"   Agent ID: {AGENT_1_ID}")
        print(f"   Token: {AGENT_1_TOKEN[:20]}...")
        auth_ok = check_authentication()
        print_status("   认证", auth_ok)
        if not auth_ok:
            print("   💡 检查 config.py 中的 Agent ID 和 Token 是否正确")
            all_checks_passed = False
        print()
    else:
        print("4. 跳过认证检查（API 不可访问）\n")
        all_checks_passed = False
    
    # 总结
    print("="*60)
    if all_checks_passed:
        print("  ✅ 所有检查通过！可以开始测试。")
        print()
        print("  运行测试:")
        print("    python run_simulation.py")
        print("    或")
        print("    make test-basic")
    else:
        print("  ⚠️  部分检查未通过，请解决上述问题后再运行测试。")
        print()
        print("  常见问题:")
        print("    1. 后端服务未运行 → python main.py")
        print("    2. Redis 未运行 → docker run -d -p 6379:6379 redis")
        print("    3. 数据库未运行 → 检查 PostgreSQL 服务")
        print("    4. Token 不正确 → 检查 config.py 配置")
    print("="*60 + "\n")
    
    return 0 if all_checks_passed else 1


if __name__ == "__main__":
    sys.exit(main())
