#!/usr/bin/env python3
"""
自主智能体系统环境验证脚本

检查所有必需的组件和配置是否就绪
"""

import os
import sys
import yaml
import requests
from pathlib import Path
from colorama import Fore, Style, init

init(autoreset=True)

def print_header(text):
    """打印标题"""
    print(f"\n{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{text:^60}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}\n")

def print_check(name, status, message=""):
    """打印检查结果"""
    if status:
        icon = f"{Fore.GREEN}✅"
        status_text = f"{Fore.GREEN}通过"
    else:
        icon = f"{Fore.RED}❌"
        status_text = f"{Fore.RED}失败"
    
    print(f"{icon} {name:.<40} {status_text}{Style.RESET_ALL}")
    if message:
        print(f"   {Fore.YELLOW}→ {message}{Style.RESET_ALL}")

def check_files():
    """检查必需文件"""
    print_header("检查必需文件")
    
    files = {
        "主程序": "simulation_test/autonomous_agent.py",
        "配置文件": "simulation_test/agent_config.yaml",
        "启动脚本": "simulation_test/start_agents.sh",
        "使用指南": "simulation_test/AUTONOMOUS_AGENT_GUIDE.md",
        "快速开始": "simulation_test/README_AUTONOMOUS.md",
    }
    
    all_ok = True
    for name, path in files.items():
        exists = os.path.exists(path)
        print_check(name, exists, path if exists else f"文件不存在: {path}")
        all_ok = all_ok and exists
    
    return all_ok

def check_executable():
    """检查启动脚本是否可执行"""
    print_header("检查文件权限")
    
    script = "simulation_test/start_agents.sh"
    is_executable = os.access(script, os.X_OK)
    print_check("启动脚本可执行", is_executable, 
                script if is_executable else f"需要执行: chmod +x {script}")
    
    return is_executable

def check_config():
    """检查配置文件"""
    print_header("检查配置文件")
    
    try:
        with open("simulation_test/agent_config.yaml", 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 检查智能体配置
        agents = config.get('agents', {})
        print_check("智能体配置", len(agents) > 0, 
                   f"找到 {len(agents)} 个智能体: {', '.join(agents.keys())}")
        
        # 检查 LLM 配置
        llm = config.get('llm', {})
        has_llm = 'api_key' in llm and 'api_url' in llm
        print_check("LLM 配置", has_llm, 
                   f"API URL: {llm.get('api_url', 'N/A')}")
        
        # 检查 API 配置
        api = config.get('api', {})
        has_api = 'base_url' in api
        print_check("API 配置", has_api, 
                   f"Base URL: {api.get('base_url', 'N/A')}")
        
        return len(agents) > 0 and has_llm and has_api
    
    except Exception as e:
        print_check("配置文件解析", False, str(e))
        return False

def check_environment():
    """检查环境变量"""
    print_header("检查环境变量")
    
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    has_deepseek = bool(deepseek_key)
    print_check("DEEPSEEK_API_KEY", has_deepseek, 
               f"已设置 ({len(deepseek_key)} 字符)" if has_deepseek else "未设置")
    
    if not has_deepseek:
        print(f"\n{Fore.YELLOW}💡 提示: 设置环境变量{Style.RESET_ALL}")
        print(f"   source .env")
        print(f"   export DEEPSEEK_API_KEY")
    
    return has_deepseek

def check_services():
    """检查后端服务"""
    print_header("检查后端服务")
    
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        is_healthy = response.status_code == 200
        print_check("后端服务", is_healthy, 
                   "服务运行正常" if is_healthy else f"状态码: {response.status_code}")
        
        if is_healthy:
            data = response.json()
            services = data.get('services', {})
            
            # 检查各个服务
            for service_name, service_info in services.items():
                status = service_info.get('status') == 'healthy'
                print_check(f"  {service_name}", status, 
                           service_info.get('message', ''))
        
        return is_healthy
    
    except requests.exceptions.ConnectionError:
        print_check("后端服务", False, "无法连接到 http://localhost:8000")
        print(f"\n{Fore.YELLOW}💡 提示: 启动后端服务{Style.RESET_ALL}")
        print(f"   ./start_services.sh")
        return False
    except Exception as e:
        print_check("后端服务", False, str(e))
        return False

def check_active_topic():
    """检查是否有活跃话题"""
    print_header("检查活跃话题")
    
    try:
        # 使用临时认证检查话题
        response = requests.get(
            "http://localhost:8000/api/topic/active",
            headers={
                "X-Agent-Id": "verify-script",
                "X-Auth-Token": "verify-token"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            topic = response.json()
            print_check("活跃话题", True, 
                       f"话题: {topic.get('title', 'N/A')}")
            return True
        elif response.status_code == 404:
            print_check("活跃话题", False, "没有活跃话题")
            print(f"\n{Fore.YELLOW}💡 提示: 创建话题{Style.RESET_ALL}")
            print(f"   python simulation_test/enhanced_simulator.py --rounds 5 --use-llm")
            return False
        else:
            print_check("活跃话题", False, f"状态码: {response.status_code}")
            return False
    
    except Exception as e:
        print_check("活跃话题", False, str(e))
        return False

def check_directories():
    """检查目录结构"""
    print_header("检查目录结构")
    
    dirs = {
        "状态目录": "simulation_test/.agent_state",
        "日志目录": "simulation_test/logs",
    }
    
    all_ok = True
    for name, path in dirs.items():
        exists = os.path.exists(path)
        if not exists:
            # 尝试创建
            try:
                os.makedirs(path, exist_ok=True)
                print_check(name, True, f"已创建: {path}")
            except Exception as e:
                print_check(name, False, f"创建失败: {e}")
                all_ok = False
        else:
            print_check(name, True, path)
    
    return all_ok

def print_summary(results):
    """打印总结"""
    print_header("验证总结")
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    print(f"总计: {total} 项检查")
    print(f"{Fore.GREEN}通过: {passed} 项{Style.RESET_ALL}")
    if failed > 0:
        print(f"{Fore.RED}失败: {failed} 项{Style.RESET_ALL}")
    
    print()
    
    if failed == 0:
        print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ 所有检查通过！系统已就绪！{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        print()
        print(f"{Fore.CYAN}🚀 下一步:{Style.RESET_ALL}")
        print(f"   cd simulation_test")
        print(f"   ./start_agents.sh")
        print()
        print(f"{Fore.CYAN}📚 查看文档:{Style.RESET_ALL}")
        print(f"   cat simulation_test/README_AUTONOMOUS.md")
        print(f"   cat 下一步操作指南.md")
    else:
        print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.RED}⚠️  有 {failed} 项检查失败，请先解决问题{Style.RESET_ALL}")
        print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}")
        print()
        print(f"{Fore.YELLOW}💡 常见问题解决:{Style.RESET_ALL}")
        print(f"   1. 后端服务未运行: ./start_services.sh")
        print(f"   2. 环境变量未设置: source .env && export DEEPSEEK_API_KEY")
        print(f"   3. 没有活跃话题: python simulation_test/enhanced_simulator.py --rounds 5")
        print(f"   4. 文件权限问题: chmod +x simulation_test/start_agents.sh")

def main():
    """主函数"""
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}自主智能体系统环境验证{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    results = {}
    
    # 执行所有检查
    results['files'] = check_files()
    results['executable'] = check_executable()
    results['config'] = check_config()
    results['environment'] = check_environment()
    results['services'] = check_services()
    results['directories'] = check_directories()
    
    # 只有在服务运行时才检查话题
    if results['services']:
        results['topic'] = check_active_topic()
    else:
        results['topic'] = False
    
    # 打印总结
    print_summary(results)
    
    # 返回退出码
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
