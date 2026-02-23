#!/usr/bin/env python3
"""
双智能体对话模拟测试脚本

模拟两个智能体通过后端 API 进行完整的话题讨论流程：
1. 创建话题
2. 交替发送消息
3. 监控 Token 计数和摘要生成
4. 模拟话题关闭流程
"""

import requests
import time
import json
from typing import Dict, Optional
from datetime import datetime


class AgentSimulator:
    """智能体模拟器"""
    
    def __init__(self, agent_id: str, token: str, api_base_url: str = "http://localhost:8000"):
        """
        初始化智能体模拟器
        
        Args:
            agent_id: 智能体 ID
            token: 认证 Token
            api_base_url: API 基础 URL
        """
        self.agent_id = agent_id
        self.token = token
        self.api_base_url = api_base_url.rstrip('/')
        self.headers = {
            "X-Agent-Id": agent_id,
            "X-Auth-Token": token,
            "Content-Type": "application/json"
        }
    
    def health_check(self) -> Dict:
        """健康检查"""
        url = f"{self.api_base_url}/api/health"
        response = requests.get(url)
        return response.json()
    
    def create_topic(self, title: str) -> Dict:
        """创建新话题"""
        url = f"{self.api_base_url}/api/topic"
        data = {"title": title}
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_active_topic(self) -> Optional[Dict]:
        """获取当前活跃话题"""
        url = f"{self.api_base_url}/api/topic/active"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    
    def send_message(self, topic_id: str, content: str, actual_tokens: int) -> Dict:
        """发送消息"""
        url = f"{self.api_base_url}/api/message"
        data = {
            "topic_id": topic_id,
            "content": content,
            "actual_tokens": actual_tokens
        }
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_messages(self, topic_id: str, limit: int = 20) -> Dict:
        """获取话题消息"""
        url = f"{self.api_base_url}/api/topic/{topic_id}/messages"
        params = {"limit": limit}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def request_close(self, topic_id: str) -> Dict:
        """请求关闭话题"""
        url = f"{self.api_base_url}/api/topic/{topic_id}/request-close"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def cancel_close(self, topic_id: str) -> Dict:
        """取消关闭请求"""
        url = f"{self.api_base_url}/api/topic/{topic_id}/cancel-close"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_summary_history(self, topic_id: str, limit: int = 10) -> Dict:
        """获取摘要历史"""
        url = f"{self.api_base_url}/api/topic/{topic_id}/summary-history"
        params = {"limit": limit}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()


def print_separator(char="=", length=80):
    """打印分隔线"""
    print(char * length)


def print_section(title: str):
    """打印章节标题"""
    print_separator()
    print(f"  {title}")
    print_separator()


def print_info(label: str, value):
    """打印信息"""
    print(f"  {label}: {value}")


def print_message(agent_name: str, content: str, tokens: int):
    """打印消息"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n  [{timestamp}] {agent_name}:")
    print(f"  > {content}")
    print(f"  (Tokens: {tokens})")


def simulate_conversation():
    """模拟完整的对话流程"""
    
    # 配置
    API_BASE_URL = "http://localhost:8000"
    AGENT_1_ID = "agent-1"
    AGENT_1_TOKEN = "token-agent-1-secret"
    AGENT_2_ID = "agent-2"
    AGENT_2_TOKEN = "token-agent-2-secret"
    
    # 创建智能体模拟器
    agent1 = AgentSimulator(AGENT_1_ID, AGENT_1_TOKEN, API_BASE_URL)
    agent2 = AgentSimulator(AGENT_2_ID, AGENT_2_TOKEN, API_BASE_URL)
    
    print("\n")
    print_section("双智能体对话模拟测试")
    print()
    
    # 步骤 1: 健康检查
    print_section("步骤 1: 系统健康检查")
    try:
        health = agent1.health_check()
        print_info("系统状态", health.get("status", "unknown"))
        for service, status in health.get("services", {}).items():
            print_info(f"  - {service}", status.get("status", "unknown"))
        print()
    except Exception as e:
        print(f"  ❌ 健康检查失败: {e}")
        print("  请确保后端服务正在运行！")
        return
    
    # 步骤 2: 创建话题
    print_section("步骤 2: 创建新话题")
    try:
        topic_title = "人工智能在医疗领域的应用前景"
        print_info("话题标题", topic_title)
        topic = agent1.create_topic(topic_title)
        topic_id = topic["topic_id"]
        print_info("话题 ID", topic_id)
        print_info("状态", topic["status"])
        print()
    except Exception as e:
        print(f"  ❌ 创建话题失败: {e}")
        return
    
    # 步骤 3: 模拟对话
    print_section("步骤 3: 模拟智能体对话")
    print()
    
    # 预定义的对话内容（模拟真实对话）
    conversation = [
        (agent1, "Agent-1", "我认为人工智能在医疗领域有巨大的应用潜力，特别是在疾病诊断方面。通过深度学习模型分析医学影像，可以帮助医生更准确地识别病变。", 150),
        (agent2, "Agent-2", "确实如此。除了影像诊断，AI 在个性化治疗方案制定上也很有前景。通过分析患者的基因数据、病史和生活习惯，可以为每个患者量身定制最优治疗方案。", 180),
        (agent1, "Agent-1", "对，而且 AI 还能在药物研发中发挥重要作用。传统药物研发周期长、成本高，AI 可以通过模拟和预测大大缩短这个过程，降低失败率。", 160),
        (agent2, "Agent-2", "不过我们也要注意 AI 医疗的伦理问题。比如数据隐私保护、算法偏见、医疗责任归属等。这些问题如果处理不当，可能会带来严重后果。", 170),
        (agent1, "Agent-1", "你说得对。数据隐私确实是个大问题。医疗数据非常敏感，必须建立严格的数据保护机制，确保患者信息不被滥用。同时也要保证数据的可用性，这是个平衡的艺术。", 190),
        (agent2, "Agent-2", "另外，算法的可解释性也很重要。医生需要理解 AI 是如何得出诊断结论的，而不是盲目相信一个黑盒系统。这对建立医患信任关系至关重要。", 175),
        (agent1, "Agent-1", "从技术角度看，我们还需要解决数据质量和标准化的问题。不同医院的数据格式、标注标准可能不同，这会影响 AI 模型的训练效果和泛化能力。", 165),
        (agent2, "Agent-2", "是的，建立统一的医疗数据标准和共享机制很有必要。但这涉及到多方利益协调，需要政府、医疗机构、科技公司等各方共同努力。", 155),
        (agent1, "Agent-1", "在实际应用中，AI 应该是辅助医生而不是替代医生。医生的经验、直觉和人文关怀是 AI 无法替代的。最理想的模式是人机协作，发挥各自优势。", 180),
        (agent2, "Agent-2", "完全同意。AI 可以处理大量数据、发现模式，但最终决策还是应该由医生做出。这样既能提高效率和准确性，又能保持医疗的人性化。", 170),
    ]
    
    # 发送消息并监控
    for i, (agent, agent_name, content, tokens) in enumerate(conversation, 1):
        try:
            # 发送消息
            result = agent.send_message(topic_id, content, tokens)
            print_message(agent_name, content, tokens)
            print_info("  累计 Token", result["token_count"])
            
            # 每发送几条消息后检查话题状态
            if i % 3 == 0:
                time.sleep(1)  # 短暂延迟
                topic_info = agent.get_active_topic()
                if topic_info:
                    print(f"\n  📊 话题状态更新:")
                    print_info("    Token 计数", topic_info["token_count_since_summary"])
                    if topic_info.get("llm_suggestion"):
                        print_info("    LLM 建议", topic_info["llm_suggestion"])
                        print_info("    结束分数", f"{topic_info['end_score']:.1f}")
                    if topic_info.get("llm_hint"):
                        print(f"    💡 提示: {topic_info['llm_hint']}")
            
            # 模拟思考时间
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ❌ 发送消息失败: {e}")
            break
    
    print()
    
    # 步骤 4: 检查最终状态
    print_section("步骤 4: 检查话题最终状态")
    try:
        topic_info = agent1.get_active_topic()
        if topic_info:
            print_info("话题 ID", topic_info["topic_id"])
            print_info("标题", topic_info["title"])
            print_info("状态", topic_info["status"])
            print_info("Token 计数", topic_info["token_count_since_summary"])
            print_info("LLM 建议", topic_info.get("llm_suggestion", "无"))
            print_info("结束分数", f"{topic_info.get('end_score', 0):.1f}")
            
            if topic_info.get("summary"):
                print("\n  📝 当前摘要:")
                print(f"  {topic_info['summary'][:200]}...")
            
            print()
    except Exception as e:
        print(f"  ❌ 获取话题状态失败: {e}")
    
    # 步骤 5: 获取消息历史
    print_section("步骤 5: 获取消息历史")
    try:
        messages = agent1.get_messages(topic_id, limit=5)
        print_info("消息总数", f"显示最近 {len(messages['messages'])} 条")
        print()
        for msg in messages["messages"][-3:]:  # 显示最后 3 条
            agent_name = "Agent-1" if msg["agent_id"] == AGENT_1_ID else "Agent-2"
            print(f"  [{msg['created_at']}] {agent_name}:")
            print(f"  > {msg['content'][:100]}...")
            print()
    except Exception as e:
        print(f"  ❌ 获取消息失败: {e}")
    
    # 步骤 6: 模拟话题关闭流程
    print_section("步骤 6: 模拟话题关闭流程")
    print()
    
    # Agent 1 请求关闭
    print("  Agent-1 请求关闭话题...")
    try:
        result = agent1.request_close(topic_id)
        print_info("  状态", result["status"])
        print_info("  双方同意", result["both_agreed"])
        print()
        time.sleep(1)
    except Exception as e:
        print(f"  ❌ 请求关闭失败: {e}")
    
    # 检查话题状态
    try:
        topic_info = agent1.get_active_topic()
        if topic_info and topic_info.get("closing_status"):
            print("  📋 关闭状态详情:")
            closing = topic_info["closing_status"]
            print_info("    请求者", closing.get("requested_by", "未知"))
            print_info("    Agent A 同意", closing.get("agent_a_wants_close", False))
            print_info("    Agent B 同意", closing.get("agent_b_wants_close", False))
            print()
    except Exception as e:
        print(f"  ⚠️  获取关闭状态失败: {e}")
    
    # Agent 2 也同意关闭
    print("  Agent-2 同意关闭话题...")
    try:
        result = agent2.request_close(topic_id)
        print_info("  状态", result["status"])
        print_info("  双方同意", result["both_agreed"])
        print()
        
        if result["status"] == "closed":
            print("  ✅ 话题已成功关闭！")
        
    except Exception as e:
        print(f"  ❌ 同意关闭失败: {e}")
    
    # 步骤 7: 获取摘要历史
    print_section("步骤 7: 获取摘要历史")
    try:
        history = agent1.get_summary_history(topic_id, limit=5)
        if history["history"]:
            print_info("历史记录数", len(history["history"]))
            print()
            for i, h in enumerate(history["history"], 1):
                print(f"  版本 {i}:")
                print_info("    创建时间", h["created_at"])
                print_info("    LLM 建议", h["llm_suggestion"])
                print_info("    结束分数", f"{h['end_score']:.1f}")
                print(f"    摘要: {h['summary'][:100]}...")
                print()
        else:
            print("  ℹ️  暂无摘要历史记录")
            print("  （可能因为 Token 数未达到阈值 8000）")
            print()
    except Exception as e:
        print(f"  ❌ 获取摘要历史失败: {e}")
    
    # 完成
    print_section("测试完成")
    print()
    print("  ✅ 所有测试步骤已完成！")
    print()
    print("  💡 提示:")
    print("  - 可以在前端页面 http://localhost:8080/index.html 查看实时对话")
    print("  - 如果 Token 数达到 8000，会自动触发摘要生成（需要 Celery Worker 运行）")
    print("  - 摘要生成是异步的，可能需要等待几秒到几十秒")
    print()
    print_separator()
    print()


def main():
    """主函数"""
    try:
        simulate_conversation()
    except KeyboardInterrupt:
        print("\n\n  ⚠️  测试被用户中断")
        print()
    except Exception as e:
        print(f"\n\n  ❌ 测试过程中发生错误: {e}")
        print()
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
