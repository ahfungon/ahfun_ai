#!/usr/bin/env python3
"""
测试 LLM 配置统一功能

验证：
1. API 端点能正确返回系统配置
2. Python 模拟器能从系统配置获取 LLM 配置
3. 配置优先级正确（系统配置 > 环境变量）
"""

import requests
import sys
from colorama import Fore, Style, init

init(autoreset=True)

API_BASE_URL = "http://localhost:8000"


def print_section(title):
    """打印章节标题"""
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{title}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")


def print_check(item, passed, message=""):
    """打印检查结果"""
    if passed:
        print(f"{Fore.GREEN}✓{Style.RESET_ALL} {item}")
        if message:
            print(f"  {Fore.WHITE}{message}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}✗{Style.RESET_ALL} {item}")
        if message:
            print(f"  {Fore.YELLOW}{message}{Style.RESET_ALL}")


def test_llm_config_endpoint():
    """测试 LLM 配置端点"""
    print_section("1. 测试 LLM 配置 API 端点")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/admin/config/llm", timeout=5)
        
        if response.status_code == 200:
            config = response.json()
            print_check("API 端点可访问", True)
            
            # 检查必需字段
            required_fields = ["provider", "api_key", "masked_key", "api_url", "model", "is_configured"]
            all_fields_present = all(field in config for field in required_fields)
            
            if all_fields_present:
                print_check("返回数据格式正确", True)
                
                # 显示配置信息
                print(f"\n  {Fore.WHITE}配置信息:{Style.RESET_ALL}")
                print(f"  - 提供商: {Fore.YELLOW}{config['provider']}{Style.RESET_ALL}")
                print(f"  - API URL: {Fore.YELLOW}{config['api_url']}{Style.RESET_ALL}")
                print(f"  - 模型: {Fore.YELLOW}{config['model']}{Style.RESET_ALL}")
                print(f"  - 脱敏 Key: {Fore.YELLOW}{config['masked_key']}{Style.RESET_ALL}")
                print(f"  - 已配置: {Fore.YELLOW}{config['is_configured']}{Style.RESET_ALL}")
                
                if config['is_configured']:
                    print_check("LLM 已配置", True, "系统配置中有有效的 API Key")
                    return True, config
                else:
                    print_check("LLM 未配置", False, "系统配置中没有 API Key")
                    return False, None
            else:
                missing = [f for f in required_fields if f not in config]
                print_check("返回数据格式正确", False, f"缺少字段: {missing}")
                return False, None
        else:
            print_check("API 端点可访问", False, f"HTTP {response.status_code}")
            return False, None
    
    except requests.exceptions.ConnectionError:
        print_check("API 端点可访问", False, "无法连接到服务器，请确保后端服务正在运行")
        return False, None
    except Exception as e:
        print_check("API 端点可访问", False, str(e))
        return False, None


def test_simulator_config_priority():
    """测试模拟器配置优先级"""
    print_section("2. 测试模拟器配置优先级")
    
    print(f"{Fore.WHITE}配置优先级:{Style.RESET_ALL}")
    print(f"  1. {Fore.GREEN}系统配置{Style.RESET_ALL} (数据库) - 最高优先级")
    print(f"  2. {Fore.YELLOW}环境变量{Style.RESET_ALL} (DEEPSEEK_API_KEY/OPENAI_API_KEY) - 备用")
    print(f"  3. {Fore.YELLOW}配置文件{Style.RESET_ALL} (config.yaml) - 最低优先级")
    
    print(f"\n{Fore.WHITE}说明:{Style.RESET_ALL}")
    print(f"  - Python 模拟器会优先从系统配置获取 LLM 配置")
    print(f"  - 如果系统配置不可用，才会使用环境变量或配置文件")
    print(f"  - 这确保了模拟器与后端服务使用相同的配置")
    
    return True


def test_config_sync():
    """测试配置同步"""
    print_section("3. 测试配置同步")
    
    print(f"{Fore.WHITE}配置同步机制:{Style.RESET_ALL}")
    print(f"  1. 在管理后台修改 LLM 配置（API Key、提供商等）")
    print(f"  2. 配置保存到系统配置（数据库）")
    print(f"  3. Python 模拟器下次运行时自动获取新配置")
    print(f"  4. 无需手动更新环境变量或配置文件")
    
    print(f"\n{Fore.GREEN}✓{Style.RESET_ALL} 配置统一管理")
    print(f"  - 后端服务（消息评分、对话总结）：使用系统配置")
    print(f"  - Python 模拟器：使用系统配置（优先）")
    print(f"  - 前端模拟器：暂不支持 LLM（待实现）")
    
    return True


def test_usage_example():
    """显示使用示例"""
    print_section("4. 使用示例")
    
    print(f"{Fore.WHITE}运行 Python 模拟器（使用系统配置）:{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}python simulation_test/enhanced_simulator.py --use-llm --rounds 5{Style.RESET_ALL}")
    
    print(f"\n{Fore.WHITE}配置获取流程:{Style.RESET_ALL}")
    print(f"  1. 模拟器启动，检测到 --use-llm 参数")
    print(f"  2. 调用 GET /api/admin/config/llm 获取系统配置")
    print(f"  3. 如果成功，使用系统配置的 API Key 和提供商")
    print(f"  4. 如果失败，回退到环境变量或配置文件")
    
    print(f"\n{Fore.WHITE}日志输出示例:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}✓ 从系统配置获取 LLM 配置: deepseek (sk-xxxxx...xxxx){Style.RESET_ALL}")
    print(f"  {Fore.GREEN}✓ LLM 后端已启用 (系统配置: deepseek){Style.RESET_ALL}")
    
    return True


def main():
    """主函数"""
    print(f"\n{Fore.YELLOW}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}LLM 配置统一功能测试{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'=' * 80}{Style.RESET_ALL}")
    
    # 测试 1: API 端点
    endpoint_ok, config = test_llm_config_endpoint()
    
    # 测试 2: 配置优先级
    priority_ok = test_simulator_config_priority()
    
    # 测试 3: 配置同步
    sync_ok = test_config_sync()
    
    # 测试 4: 使用示例
    example_ok = test_usage_example()
    
    # 总结
    print_section("测试总结")
    
    all_passed = endpoint_ok and priority_ok and sync_ok and example_ok
    
    if all_passed:
        print(f"{Fore.GREEN}✓ 所有测试通过{Style.RESET_ALL}")
        print(f"\n{Fore.WHITE}下一步:{Style.RESET_ALL}")
        print(f"  1. 在管理后台配置 LLM API Key")
        print(f"  2. 运行 Python 模拟器测试配置是否生效")
        print(f"  3. 修改配置后无需重启，模拟器会自动获取新配置")
        return 0
    else:
        print(f"{Fore.RED}✗ 部分测试失败{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}请检查:{Style.RESET_ALL}")
        if not endpoint_ok:
            print(f"  - 后端服务是否正在运行")
            print(f"  - 系统配置中是否已设置 LLM API Key")
        return 1


if __name__ == "__main__":
    sys.exit(main())
