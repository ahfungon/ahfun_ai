#!/usr/bin/env python3
"""
灵活的双智能体对话模拟脚本

支持多种测试场景：
- 基本对话流程
- 高频消息测试（触发摘要）
- 话题关闭流程测试
- 并发测试
"""

import argparse
import sys
from simulate_dual_agent_chat import AgentSimulator, print_section, print_info, print_message, print_separator
from config import *
import time


def test_basic_conversation(topic_key: str = DEFAULT_TOPIC):
    """测试基本对话流程"""
    print_section(f"测试场景: 基本对话流程 - {CONVERSATION_TOPICS[topic_key]['title']}")
    print()
    
    # 创建智能体
    agent1 = AgentSimulator(AGENT_1_ID, AGENT_1_TOKEN, API_BASE_URL)
    agent2 = AgentSimulator(AGENT_2_ID, AGENT_2_TOKEN, API_BASE_URL)
    
    # 健康检查
    print("  🔍 检查系统健康状态...")
    try:
        health = agent1.health_check()
        if health.get("status") != "ok":
            print("  ⚠️  系统状态异常，但继续测试...")
        else:
            print("  ✅ 系统健康")
    except Exception as e:
        print(f"  ❌ 无法连接到后端服务: {e}")
        return False
    
    # 创建话题
    print(f"\n  📝 创建话题: {CONVERSATION_TOPICS[topic_key]['title']}")
    try:
        topic = agent1.create_topic(CONVERSATION_TOPICS[topic_key]['title'])
        topic_id = topic["topic_id"]
        print_info("  话题 ID", topic_id)
    except Exception as e:
        print(f"  ❌ 创建话题失败: {e}")
        return False
    
    # 发送消息
    print("\n  💬 开始对话...")
    print()
    
    messages = CONVERSATION_TOPICS[topic_key]['messages']
    agents_map = {"agent1": (agent1, AGENT_1_NAME), "agent2": (agent2, AGENT_2_NAME)}
    
    for i, (agent_key, content, tokens) in enumerate(messages, 1):
        agent, agent_name = agents_map[agent_key]
        
        try:
            result = agent.send_message(topic_id, content, tokens)
            print_message(agent_name, content, tokens)
            print_info("  累计 Token", result["token_count"])
            
            # 定期检查状态
            if i % STATUS_CHECK_INTERVAL == 0:
                time.sleep(0.5)
                topic_info = agent.get_active_topic()
                if topic_info:
                    print(f"\n  📊 话题状态:")
                    print_info("    Token 计数", topic_info["token_count_since_summary"])
                    if topic_info.get("llm_suggestion"):
                        print_info("    LLM 建议", topic_info["llm_suggestion"])
                    if topic_info.get("llm_hint"):
                        print(f"    💡 {topic_info['llm_hint']}")
            
            time.sleep(MESSAGE_DELAY)
            
        except Exception as e:
            print(f"  ❌ 发送消息失败: {e}")
            return False
    
    print("\n  ✅ 对话完成！")
    print_info("  话题 ID", topic_id)
    return True


def test_high_frequency_messages():
    """测试高频消息（触发摘要）"""
    print_section("测试场景: 高频消息测试（触发摘要生成）")
    print()
    
    agent1 = AgentSimulator(AGENT_1_ID, AGENT_1_TOKEN, API_BASE_URL)
    agent2 = AgentSimulator(AGENT_2_ID, AGENT_2_TOKEN, API_BASE_URL)
    
    # 创建话题
    print("  📝 创建测试话题...")
    try:
        topic = agent1.create_topic("高频消息测试 - 触发摘要")
        topic_id = topic["topic_id"]
        print_info("  话题 ID", topic_id)
    except Exception as e:
        print(f"  ❌ 创建话题失败: {e}")
        return False
    
    # 计算需要发送多少条消息才能达到阈值
    avg_tokens_per_message = 500
    messages_needed = (SUMMARY_THRESHOLD // avg_tokens_per_message) + 2
    
    print(f"\n  💬 发送 {messages_needed} 条消息以触发摘要...")
    print(f"  （目标: 超过 {SUMMARY_THRESHOLD} tokens）")
    print()
    
    agents = [agent1, agent2]
    agent_names = [AGENT_1_NAME, AGENT_2_NAME]
    
    for i in range(messages_needed):
        agent = agents[i % 2]
        agent_name = agent_names[i % 2]
        
        content = f"这是第 {i+1} 条测试消息。" + "内容填充 " * 50  # 增加内容长度
        tokens = avg_tokens_per_message
        
        try:
            result = agent.send_message(topic_id, content, tokens)
            print(f"  [{i+1}/{messages_needed}] {agent_name}: {tokens} tokens (累计: {result['token_count']})")
            
            # 检查是否触发摘要
            if result['token_count'] >= SUMMARY_THRESHOLD:
                print(f"\n  🎯 已达到摘要阈值！")
                print("  ⏳ 等待摘要生成（需要 Celery Worker 运行）...")
                
                # 等待摘要生成
                for wait_time in range(30):
                    time.sleep(1)
                    topic_info = agent.get_active_topic()
                    if topic_info and topic_info.get("token_count_since_summary") == 0:
                        print(f"\n  ✅ 摘要已生成！")
                        print_info("    LLM 建议", topic_info.get("llm_suggestion", "无"))
                        print_info("    结束分数", f"{topic_info.get('end_score', 0):.1f}")
                        if topic_info.get("summary"):
                            print(f"\n  📝 摘要内容:")
                            print(f"  {topic_info['summary'][:200]}...")
                        break
                    print(f"  等待中... ({wait_time+1}s)", end="\r")
                else:
                    print("\n  ⚠️  摘要生成超时（可能 Celery Worker 未运行）")
                
                break
            
            time.sleep(0.1)  # 快速发送
            
        except Exception as e:
            print(f"  ❌ 发送消息失败: {e}")
            return False
    
    print("\n  ✅ 高频消息测试完成！")
    return True


def test_topic_closing():
    """测试话题关闭流程"""
    print_section("测试场景: 话题关闭流程")
    print()
    
    agent1 = AgentSimulator(AGENT_1_ID, AGENT_1_TOKEN, API_BASE_URL)
    agent2 = AgentSimulator(AGENT_2_ID, AGENT_2_TOKEN, API_BASE_URL)
    
    # 创建话题
    print("  📝 创建测试话题...")
    try:
        topic = agent1.create_topic("话题关闭流程测试")
        topic_id = topic["topic_id"]
        print_info("  话题 ID", topic_id)
    except Exception as e:
        print(f"  ❌ 创建话题失败: {e}")
        return False
    
    # 发送几条消息
    print("\n  💬 发送几条测试消息...")
    for i in range(3):
        agent = agent1 if i % 2 == 0 else agent2
        agent_name = AGENT_1_NAME if i % 2 == 0 else AGENT_2_NAME
        try:
            agent.send_message(topic_id, f"测试消息 {i+1}", 100)
            print(f"  ✓ {agent_name} 发送消息 {i+1}")
        except Exception as e:
            print(f"  ❌ 发送失败: {e}")
    
    # 测试关闭流程
    print("\n  🔒 测试关闭流程...")
    
    # Agent 1 请求关闭
    print(f"\n  1. {AGENT_1_NAME} 请求关闭话题")
    try:
        result = agent1.request_close(topic_id)
        print_info("    状态", result["status"])
        print_info("    双方同意", result["both_agreed"])
        
        if result["status"] == "closing_pending":
            print("    ✓ 话题进入 closing_pending 状态")
    except Exception as e:
        print(f"    ❌ 请求失败: {e}")
        return False
    
    time.sleep(1)
    
    # 检查状态
    print(f"\n  2. 检查话题状态")
    try:
        topic_info = agent1.get_active_topic()
        if topic_info and topic_info.get("closing_status"):
            closing = topic_info["closing_status"]
            print_info("    Agent A 同意", closing.get("agent_a_wants_close"))
            print_info("    Agent B 同意", closing.get("agent_b_wants_close"))
    except Exception as e:
        print(f"    ⚠️  获取状态失败: {e}")
    
    # Agent 2 同意关闭
    print(f"\n  3. {AGENT_2_NAME} 同意关闭话题")
    try:
        result = agent2.request_close(topic_id)
        print_info("    状态", result["status"])
        print_info("    双方同意", result["both_agreed"])
        
        if result["status"] == "closed":
            print("    ✅ 话题已成功关闭！")
    except Exception as e:
        print(f"    ❌ 同意失败: {e}")
        return False
    
    print("\n  ✅ 关闭流程测试完成！")
    return True


def test_cancel_closing():
    """测试取消关闭请求"""
    print_section("测试场景: 取消关闭请求")
    print()
    
    agent1 = AgentSimulator(AGENT_1_ID, AGENT_1_TOKEN, API_BASE_URL)
    agent2 = AgentSimulator(AGENT_2_ID, AGENT_2_TOKEN, API_BASE_URL)
    
    # 创建话题
    print("  📝 创建测试话题...")
    try:
        topic = agent1.create_topic("取消关闭测试")
        topic_id = topic["topic_id"]
        print_info("  话题 ID", topic_id)
    except Exception as e:
        print(f"  ❌ 创建话题失败: {e}")
        return False
    
    # Agent 1 请求关闭
    print(f"\n  1. {AGENT_1_NAME} 请求关闭话题")
    try:
        result = agent1.request_close(topic_id)
        print_info("    状态", result["status"])
    except Exception as e:
        print(f"    ❌ 请求失败: {e}")
        return False
    
    time.sleep(1)
    
    # Agent 1 取消关闭
    print(f"\n  2. {AGENT_1_NAME} 取消关闭请求")
    try:
        result = agent1.cancel_close(topic_id)
        print_info("    状态", result["status"])
        print("    ✅ 关闭请求已取消")
    except Exception as e:
        print(f"    ❌ 取消失败: {e}")
        return False
    
    # 验证话题恢复 active 状态
    print(f"\n  3. 验证话题状态")
    try:
        topic_info = agent1.get_active_topic()
        if topic_info:
            print_info("    状态", topic_info["status"])
            if topic_info["status"] == "active":
                print("    ✅ 话题已恢复 active 状态")
    except Exception as e:
        print(f"    ⚠️  获取状态失败: {e}")
    
    print("\n  ✅ 取消关闭测试完成！")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="双智能体对话模拟测试")
    parser.add_argument(
        "--scenario",
        choices=["basic", "high-freq", "closing", "cancel", "all"],
        default="basic",
        help="测试场景: basic(基本对话), high-freq(高频消息), closing(关闭流程), cancel(取消关闭), all(全部)"
    )
    parser.add_argument(
        "--topic",
        choices=list(CONVERSATION_TOPICS.keys()),
        default=DEFAULT_TOPIC,
        help="对话主题（仅用于 basic 场景）"
    )
    
    args = parser.parse_args()
    
    print("\n")
    print_separator("=", 80)
    print("  双智能体对话模拟测试系统")
    print_separator("=", 80)
    print()
    print_info("API 地址", API_BASE_URL)
    print_info("Agent 1", f"{AGENT_1_NAME} ({AGENT_1_ID})")
    print_info("Agent 2", f"{AGENT_2_NAME} ({AGENT_2_ID})")
    print()
    
    try:
        if args.scenario == "basic":
            success = test_basic_conversation(args.topic)
        elif args.scenario == "high-freq":
            success = test_high_frequency_messages()
        elif args.scenario == "closing":
            success = test_topic_closing()
        elif args.scenario == "cancel":
            success = test_cancel_closing()
        elif args.scenario == "all":
            print_section("运行所有测试场景")
            print()
            
            scenarios = [
                ("基本对话", lambda: test_basic_conversation()),
                ("话题关闭", test_topic_closing),
                ("取消关闭", test_cancel_closing),
                ("高频消息", test_high_frequency_messages),
            ]
            
            results = []
            for name, test_func in scenarios:
                print(f"\n{'='*80}")
                print(f"  开始测试: {name}")
                print(f"{'='*80}\n")
                success = test_func()
                results.append((name, success))
                time.sleep(2)
            
            # 汇总结果
            print("\n")
            print_section("测试结果汇总")
            print()
            for name, success in results:
                status = "✅ 通过" if success else "❌ 失败"
                print(f"  {name}: {status}")
            print()
            
            success = all(s for _, s in results)
        
        # 最终提示
        print()
        print_separator("=", 80)
        if success:
            print("  ✅ 测试成功完成！")
        else:
            print("  ⚠️  测试过程中遇到问题")
        print()
        print("  💡 提示:")
        print("  - 在前端页面查看实时对话: http://localhost:8080/index.html")
        print("  - 管理面板: http://localhost:8080/admin.html")
        print("  - API 文档: http://localhost:8000/docs")
        print()
        print_separator("=", 80)
        print()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n  ⚠️  测试被用户中断")
        print()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n  ❌ 测试过程中发生错误: {e}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
