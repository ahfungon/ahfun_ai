#!/usr/bin/env python3
"""
增强版智能体对话模拟器

功能特性：
1. 自动注册智能体
2. 集成真实 LLM 生成对话
3. 监控评分和反馈
4. 完整的话题生命周期
5. 统计和报告生成
"""

import os
import sys
import time
import json
import yaml
import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import tiktoken

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMBackend:
    """LLM 后端接口（支持 OpenAI/DeepSeek）"""
    
    def __init__(self, api_key: str, api_url: str = "https://api.openai.com/v1", model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        self.model = model
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """计算文本的 token 数"""
        return len(self.encoding.encode(text))
    
    def generate_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict],
        temperature: float = 0.7
    ) -> Tuple[str, int]:
        """
        生成回复
        
        Returns:
            (response_text, token_count)
        """
        try:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_history)
            
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 500
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            tokens = self.count_tokens(content)
            
            return content, tokens
        
        except Exception as e:
            logger.error(f"LLM 生成失败: {e}")
            # 返回备用回复
            fallback = "我理解你的观点，让我们继续深入讨论这个话题。"
            return fallback, self.count_tokens(fallback)


class Agent:
    """智能体类"""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        token: str,
        api_base_url: str,
        llm_backend: Optional[LLMBackend] = None,
        personality: str = "balanced"
    ):
        self.agent_id = agent_id
        self.name = name
        self.token = token
        self.api_base_url = api_base_url.rstrip('/')
        self.llm_backend = llm_backend
        self.personality = personality
        self.headers = {
            "X-Agent-Id": agent_id,
            "X-Auth-Token": token,
            "Content-Type": "application/json"
        }
        self.my_scores = []
        self.conversation_history = []
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """发送 HTTP 请求"""
        url = f"{self.api_base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response
    
    def register(self) -> Dict:
        """注册智能体（如果尚未注册）"""
        # 注意：这里假设使用自注册端点
        try:
            response = requests.post(
                f"{self.api_base_url}/api/agent/register",
                json={"agent_name": self.name}
            )
            response.raise_for_status()
            data = response.json()
            self.agent_id = data["agent_id"]
            self.token = data["auth_token"]
            self.headers["X-Agent-Id"] = self.agent_id
            self.headers["X-Auth-Token"] = self.token
            return data
        except Exception as e:
            logger.warning(f"注册失败（可能已存在）: {e}")
            return {}
    
    def create_topic(self, title: str, description: str = "") -> Dict:
        """创建话题"""
        data = {"title": title}
        if description:
            data["topic_description"] = description
        response = self._make_request("POST", "/api/topic", json=data)
        return response.json()
    
    def get_active_topic(self) -> Optional[Dict]:
        """获取活跃话题"""
        try:
            response = self._make_request("GET", "/api/topic/active")
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    def send_message(self, topic_id: str, content: str, actual_tokens: int) -> Dict:
        """发送消息"""
        data = {
            "topic_id": topic_id,
            "content": content,
            "actual_tokens": actual_tokens
        }
        response = self._make_request("POST", "/api/message", json=data)
        return response.json()
    
    def get_messages(self, topic_id: str, limit: int = 20) -> List[Dict]:
        """获取消息列表"""
        response = self._make_request(
            "GET",
            f"/api/topic/{topic_id}/messages",
            params={"limit": limit}
        )
        return response.json()["messages"]
    
    def get_my_scores(self, limit: int = 10) -> Dict:
        """获取我的评分"""
        response = self._make_request(
            "GET",
            "/api/agent/my-scores",
            params={"limit": limit}
        )
        return response.json()
    
    def request_close(self, topic_id: str) -> Dict:
        """请求关闭话题"""
        response = self._make_request("POST", f"/api/topic/{topic_id}/request-close")
        return response.json()
    
    def generate_response_with_llm(
        self,
        topic_title: str,
        topic_description: str,
        conversation_history: List[Dict],
        my_recent_scores: List[Dict]
    ) -> Tuple[str, int]:
        """使用 LLM 生成回复"""
        if not self.llm_backend:
            # 如果没有 LLM，返回预设回复
            content = f"作为 {self.name}，我认为这是一个很有意思的话题。"
            return content, 50
        
        # 构建系统提示
        system_prompt = self._build_system_prompt(
            topic_title,
            topic_description,
            my_recent_scores
        )
        
        # 准备对话历史
        llm_history = []
        for msg in conversation_history[-5:]:  # 只取最近5条
            role = "assistant" if msg["agent_id"] == self.agent_id else "user"
            llm_history.append({
                "role": role,
                "content": msg["content"]
            })
        
        # 生成回复
        return self.llm_backend.generate_response(
            system_prompt,
            llm_history,
            temperature=0.7
        )
    
    def _build_system_prompt(
        self,
        topic_title: str,
        topic_description: str,
        recent_scores: List[Dict]
    ) -> str:
        """构建系统提示词"""
        prompt = f"""你是一个参与讨论的智能体，名字是 {self.name}。

【讨论主题】
标题：{topic_title}
描述：{topic_description}

【你的角色】
你需要围绕主题进行有深度的讨论，提出有见地的观点。

【评分反馈】
"""
        
        if recent_scores:
            avg_score = sum(s["score"] for s in recent_scores) / len(recent_scores)
            prompt += f"你最近的平均评分是 {avg_score:.1f}/100。\n"
            
            if avg_score < 60:
                prompt += "评分较低，请更加紧扣主题，提高内容质量和深度。\n"
            elif avg_score >= 80:
                prompt += "评分很好，继续保持高质量的讨论。\n"
            
            # 显示最近一次评分的评论
            if recent_scores[0].get("comment"):
                prompt += f"最近评价：{recent_scores[0]['comment']}\n"
        
        prompt += """
【要求】
1. 紧扣主题，不要偏离讨论范围
2. 提供有深度、有见地的观点
3. 推动讨论向前发展
4. 回复长度控制在100-200字
5. 使用中文回复

请生成你的下一条回复："""
        
        return prompt


class ConversationSimulator:
    """对话模拟器"""
    
    def __init__(self, config_path: str = "simulation_test/config.yaml"):
        self.config = self._load_config(config_path)
        self.api_base_url = self.config.get("api_base_url", "http://localhost:8000")
        self.agents: List[Agent] = []
        self.current_topic_id: Optional[str] = None
        self.stats = {
            "messages_sent": 0,
            "total_tokens": 0,
            "scores_received": 0,
            "start_time": None,
            "end_time": None
        }
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
    def setup_agents(self, num_agents: int = 2, use_llm: bool = False):
        """设置智能体"""
        logger.info(f"设置 {num_agents} 个智能体...")
        
        # 创建 LLM 后端（如果需要）
        llm_backend = None
        if use_llm:
            api_key = os.getenv("OPENAI_API_KEY") or self.config.get("llm", {}).get("api_key")
            if api_key:
                llm_config = self.config.get("llm", {})
                llm_backend = LLMBackend(
                    api_key=api_key,
                    api_url=llm_config.get("api_url", "https://api.openai.com/v1"),
                    model=llm_config.get("model", "gpt-3.5-turbo")
                )
                logger.info("✓ LLM 后端已启用")
            else:
                logger.warning("⚠ 未找到 LLM API 密钥，将使用预设回复")
        
        # 创建智能体
        for i in range(num_agents):
            agent = Agent(
                agent_id=f"agent-{i+1}",
                name=f"Agent-{i+1}",
                token=f"token-agent-{i+1}-secret",
                api_base_url=self.api_base_url,
                llm_backend=llm_backend
            )
            self.agents.append(agent)
            logger.info(f"✓ 创建智能体: {agent.name}")
    
    def run_simulation(
        self,
        topic_title: str,
        topic_description: str,
        num_rounds: int = 10,
        use_llm: bool = False
    ):
        """运行模拟"""
        logger.info("=" * 80)
        logger.info("开始对话模拟")
        logger.info("=" * 80)
        
        self.stats["start_time"] = datetime.now()
        
        try:
            # 1. 创建话题
            logger.info(f"\n📝 创建话题: {topic_title}")
            topic = self.agents[0].create_topic(topic_title, topic_description)
            self.current_topic_id = topic["topic_id"]
            logger.info(f"✓ 话题 ID: {self.current_topic_id}")
            
            # 2. 进行对话
            logger.info(f"\n💬 开始 {num_rounds} 轮对话...\n")
            
            for round_num in range(num_rounds):
                agent = self.agents[round_num % len(self.agents)]
                
                # 获取话题信息和历史
                topic_info = agent.get_active_topic()
                messages = agent.get_messages(self.current_topic_id, limit=10)
                
                # 生成回复
                if use_llm:
                    # 获取我的评分
                    my_scores_data = agent.get_my_scores(limit=5)
                    my_scores = my_scores_data.get("recent_scores", [])
                    
                    content, tokens = agent.generate_response_with_llm(
                        topic_title,
                        topic_description,
                        messages,
                        my_scores
                    )
                else:
                    # 使用预设回复
                    content = self._get_preset_response(round_num, agent.name)
                    tokens = len(content) * 2  # 粗略估计
                
                # 发送消息
                result = agent.send_message(self.current_topic_id, content, tokens)
                
                # 更新统计
                self.stats["messages_sent"] += 1
                self.stats["total_tokens"] += tokens
                
                # 显示消息
                timestamp = datetime.now().strftime("%H:%M:%S")
                logger.info(f"[{timestamp}] {agent.name}:")
                logger.info(f"  {content}")
                logger.info(f"  (Tokens: {tokens}, 累计: {result['token_count']})")
                
                # 检查评分（等待一下让评分任务完成）
                if round_num > 0:  # 第一条消息可能还没评分
                    time.sleep(2)  # 等待评分
                    scores_data = agent.get_my_scores(limit=1)
                    if scores_data.get("recent_scores"):
                        latest_score = scores_data["recent_scores"][0]
                        score_value = latest_score["score"]
                        comment = latest_score.get("comment", "")
                        
                        # 评分等级
                        if score_value >= 80:
                            level = "优秀 🟢"
                        elif score_value >= 60:
                            level = "良好 🔵"
                        elif score_value >= 40:
                            level = "一般 🟡"
                        else:
                            level = "较差 🔴"
                        
                        logger.info(f"  ⭐ 评分: {score_value:.1f}/100 ({level})")
                        if comment:
                            logger.info(f"  💬 评价: {comment}")
                        
                        self.stats["scores_received"] += 1
                
                # 检查话题状态
                if round_num % 3 == 2:
                    topic_info = agent.get_active_topic()
                    if topic_info:
                        logger.info(f"\n  📊 话题状态:")
                        logger.info(f"    Token 计数: {topic_info['token_count_since_summary']}")
                        if topic_info.get("llm_suggestion"):
                            logger.info(f"    LLM 建议: {topic_info['llm_suggestion']}")
                            logger.info(f"    结束评分: {topic_info['end_score']:.1f}")
                
                logger.info("")
                time.sleep(1)  # 模拟思考时间
            
            # 3. 关闭话题
            logger.info("\n🔚 关闭话题...")
            for agent in self.agents:
                result = agent.request_close(self.current_topic_id)
                logger.info(f"  {agent.name} 请求关闭: {result['status']}")
                if result["both_agreed"]:
                    logger.info("  ✓ 话题已关闭")
                    break
                time.sleep(0.5)
            
            # 4. 生成报告
            self.stats["end_time"] = datetime.now()
            self._generate_report()
        
        except Exception as e:
            logger.error(f"❌ 模拟过程出错: {e}", exc_info=True)
        
        finally:
            logger.info("\n" + "=" * 80)
            logger.info("模拟结束")
            logger.info("=" * 80)
    
    def _get_preset_response(self, round_num: int, agent_name: str) -> str:
        """获取预设回复"""
        responses = [
            "我认为这个话题非常有意义，值得深入探讨。",
            "从另一个角度来看，我们还需要考虑实际应用中的挑战。",
            "这确实是个重要的问题，需要多方面的考量。",
            "我同意你的观点，同时我想补充一些想法。",
            "让我们从技术层面来分析一下这个问题。",
            "除了技术因素，伦理和社会影响也很重要。",
            "在实践中，我们需要平衡各方面的利益。",
            "这个观点很有启发性，让我想到了相关的案例。",
            "总结一下，我们讨论了几个关键点。",
            "基于前面的讨论，我认为我们可以得出一些结论。"
        ]
        return responses[round_num % len(responses)]
    
    def _generate_report(self):
        """生成模拟报告"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 模拟统计报告")
        logger.info("=" * 80)
        
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        logger.info(f"\n时间统计:")
        logger.info(f"  开始时间: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"  结束时间: {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"  总耗时: {duration:.1f} 秒")
        
        logger.info(f"\n消息统计:")
        logger.info(f"  发送消息数: {self.stats['messages_sent']}")
        logger.info(f"  总 Token 数: {self.stats['total_tokens']}")
        logger.info(f"  平均每条: {self.stats['total_tokens'] / max(self.stats['messages_sent'], 1):.1f} tokens")
        
        logger.info(f"\n评分统计:")
        logger.info(f"  收到评分数: {self.stats['scores_received']}")
        logger.info(f"  评分覆盖率: {self.stats['scores_received'] / max(self.stats['messages_sent'], 1) * 100:.1f}%")
        
        # 获取每个智能体的评分
        logger.info(f"\n智能体评分:")
        for agent in self.agents:
            try:
                scores_data = agent.get_my_scores(limit=100)
                avg_score = scores_data.get("average_score")
                if avg_score:
                    logger.info(f"  {agent.name}: 平均 {avg_score:.1f}/100")
            except:
                pass


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="增强版智能体对话模拟器")
    parser.add_argument("--topic", default="人工智能在医疗领域的应用前景", help="话题标题")
    parser.add_argument("--description", default="讨论AI在医疗诊断、治疗、药物研发等方面的应用", help="话题描述")
    parser.add_argument("--rounds", type=int, default=10, help="对话轮数")
    parser.add_argument("--agents", type=int, default=2, help="智能体数量")
    parser.add_argument("--use-llm", action="store_true", help="使用真实 LLM 生成对话")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API 基础 URL")
    
    args = parser.parse_args()
    
    # 创建模拟器
    simulator = ConversationSimulator()
    simulator.api_base_url = args.api_url
    
    # 设置智能体
    simulator.setup_agents(num_agents=args.agents, use_llm=args.use_llm)
    
    # 运行模拟
    simulator.run_simulation(
        topic_title=args.topic,
        topic_description=args.description,
        num_rounds=args.rounds,
        use_llm=args.use_llm
    )


if __name__ == "__main__":
    main()
