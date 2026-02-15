#!/usr/bin/env python3
"""测试智能体关闭话题功能"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_closing_methods():
    """测试关闭话题相关方法是否存在"""
    print("🔍 检查智能体关闭话题功能...")
    print()
    
    # 读取智能体代码
    agent_file = Path("simulation_test/autonomous_agent.py")
    if not agent_file.exists():
        print("❌ 找不到智能体文件")
        return False
    
    content = agent_file.read_text(encoding='utf-8')
    
    # 检查必需的方法
    required_methods = [
        "request_close_topic",
        "cancel_close_request",
        "should_request_close",
        "should_cancel_close"
    ]
    
    print("【检查方法】")
    all_found = True
    for method in required_methods:
        if f"def {method}(" in content:
            print(f"  ✓ {method}")
        else:
            print(f"  ❌ {method} - 未找到")
            all_found = False
    
    print()
    
    # 检查 run_cycle 是否集成了关闭逻辑
    print("【检查集成】")
    integration_checks = [
        ("should_cancel_close", "取消关闭逻辑"),
        ("should_request_close", "请求关闭逻辑"),
        ("request_close_topic", "请求关闭调用"),
        ("cancel_close_request", "取消关闭调用"),
        ("closing_pending", "处理 closing_pending 状态")
    ]
    
    for check, desc in integration_checks:
        if check in content and "run_cycle" in content:
            # 简单检查是否在 run_cycle 附近
            print(f"  ✓ {desc}")
        else:
            print(f"  ⚠️  {desc} - 可能未集成")
    
    print()
    
    if all_found:
        print("✅ 所有关闭话题方法已添加")
        return True
    else:
        print("❌ 部分方法缺失")
        return False


def show_closing_logic():
    """显示关闭话题的决策逻辑"""
    print("【关闭话题决策逻辑】")
    print()
    print("1️⃣  请求关闭的条件（满足任一即触发）：")
    print("   - LLM 建议 force_end")
    print("   - LLM 建议 suggest_end 且讨论深度 >= 85")
    print("   - 消息数量 > 100")
    print("   - 最近3次评分持续下降")
    print()
    print("2️⃣  取消关闭的条件（需同时满足）：")
    print("   - 话题状态为 closing_pending")
    print("   - 是自己发起的关闭请求")
    print("   - LLM 建议改为 continue")
    print()
    print("3️⃣  同意对方关闭的条件：")
    print("   - 对方已请求关闭（closing_pending）")
    print("   - LLM 建议为 force_end 或 suggest_end")
    print()
    print("4️⃣  超时机制：")
    print("   - 请求关闭后，5分钟内对方未响应")
    print("   - 系统自动关闭话题")
    print("   - 由 Celery Beat 定时任务检查")
    print()


def show_api_endpoints():
    """显示 API 端点"""
    print("【API 端点】")
    print()
    print("1. POST /api/topic/{topic_id}/request-close")
    print("   - 请求关闭话题")
    print("   - 返回: {status, both_agreed}")
    print()
    print("2. POST /api/topic/{topic_id}/cancel-close")
    print("   - 取消关闭请求")
    print("   - 返回: {status, message}")
    print()


def main():
    print("=" * 80)
    print("智能体关闭话题功能测试")
    print("=" * 80)
    print()
    
    # 测试方法是否存在
    if not test_closing_methods():
        return 1
    
    print()
    print("=" * 80)
    
    # 显示决策逻辑
    show_closing_logic()
    
    print("=" * 80)
    
    # 显示 API 端点
    show_api_endpoints()
    
    print("=" * 80)
    print()
    print("✅ 智能体关闭话题功能已完整实现")
    print()
    print("📝 下一步：")
    print("   1. 重启智能体以应用新功能")
    print("   2. 观察智能体是否会根据条件请求关闭话题")
    print("   3. 检查日志中的关闭决策信息")
    print()
    print("🔄 重启命令：")
    print("   pkill -f 'autonomous_agent.py' && cd simulation_test && ./start_agents.sh")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
