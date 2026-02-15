#!/usr/bin/env python3
"""
自主智能体模拟系统

模拟真实智能体接入系统的完整生命周期：
- 注册账号
- 发现话题
- 分析上下文
- 查看评分
- LLM推理
- 发送消息
- 定期循环
"""

import os
import sys
import time
import json
import yaml
import requests
import argparse
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from colorama import Fore, Back, Style, init
from dotenv import load_dotenv

# 初始化 colorama
init(autoreset=True)

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 加载.env文件
env_path = os.path.join(project_root, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✓ 已加载环境变量: {env_path}")
else:
    print(f"⚠️  未找到.env文件: {env_path}")


class AgentLogger:
    """彩色日志系统"""
    
    def __init__(self, agent_name: str, log_file: Optional[str] = None):
        self.agent_name = agent_name
        self.log_file = log_file
        
    def _log(self, level: str, emoji: str, color: str, message: str, indent: int = 0):
        """内部日志方法"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = "  " * indent
        log_line = f"[{timestamp}] {emoji} {message}"
        
        # 彩色输出到终端
        print(f"{color}{prefix}{log_line}{Style.RESET_ALL}")
        
        # 保存到文件
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"{prefix}{log_line}\n")
    
    def info(self, message: str, indent: int = 0):
        self._log("INFO", "ℹ️", Fore.CYAN, message, indent)
    
    def success(self, message: str, indent: int = 0):
        self._log("SUCCESS", "✓", Fore.GREEN, message, indent)
    
    def warning(self, message: str, indent: int = 0):
        self._log("WARNING", "⚠️", Fore.YELLOW, message, indent)
    
    def error(self, message: str, indent: int = 0):
        self._log("ERROR", "❌", Fore.RED, message, indent)
    
    def startup(self, message: str, indent: int = 0):
        self._log("STARTUP", "🚀", Fore.BLUE, message, indent)
    
    def discover(self, message: str, indent: int = 0):
        self._log("DISCOVER", "🔍", Fore.YELLOW, message, indent)
    
    def analyze(self, message: str, indent: int = 0):
        self._log("ANALYZE", "📊", Fore.MAGENTA, message, indent)
    
    def score(self, message: str, indent: int = 0):
        self._log("SCORE", "⭐", Fore.GREEN, message, indent)
    
    def think(self, message: str, indent: int = 0):
        self._log("THINK", "🤔", Fore.MAGENTA, message, indent)
    
    def send(self, message: str, indent: int = 0):
        self._log("SEND", "📤", Fore.CYAN, message, indent)
    
    def sleep(self, message: str, indent: int = 0):
        self._log("SLEEP", "😴", Fore.BLUE, message, indent)
    
    def separator(self):
        """分隔线"""
        line = "━" * 80
        print(f"{Fore.BLUE}{line}{Style.RESET_ALL}")
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"{line}\n")



class AgentState:
    """智能体状态管理"""
    
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.data = self._load()
    
    def _load(self) -> Dict:
        """加载状态"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save(self):
        """保存状态"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def get(self, key: str, default=None):
        return self.data.get(key, default)
    
    def set(self, key: str, value):
        self.data[key] = value
        self.save()
    
    def is_registered(self) -> bool:
        return 'agent_id' in self.data and 'auth_token' in self.data



class LLMClient:
    """LLM 客户端"""
    
    def __init__(self, config: Dict, logger: AgentLogger):
        self.api_key = os.getenv("DEEPSEEK_API_KEY") or config.get("api_key", "")
        self.api_url = config.get("api_url", "https://api.deepseek.com/v1")
        self.model = config.get("model", "deepseek-chat")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 500)
        self.timeout = config.get("timeout", 30)
        self.logger = logger
    
    def generate(self, system_prompt: str, user_prompt: str) -> Tuple[str, int]:
        """
        生成回复
        
        Returns:
            (content, token_count)
        """
        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                },
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            tokens = len(content) * 2  # 粗略估计
            
            return content, tokens
        
        except Exception as e:
            self.logger.error(f"LLM 生成失败: {e}")
            # 返回备用回复
            fallback = "我认为这个话题很有意义，值得深入探讨。"
            return fallback, len(fallback) * 2



class AutonomousAgent:
    """自主智能体"""
    
    def __init__(self, agent_key: str, config: Dict):
        self.agent_key = agent_key
        self.config = config
        self.agent_config = config['agents'][agent_key]
        self.api_config = config['api']
        
        # 初始化组件
        log_dir = config['logging'].get('log_dir', 'simulation_test/logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = f"{log_dir}/agent-{agent_key}.log" if config['logging'].get('save_to_file') else None
        
        self.logger = AgentLogger(self.agent_config['name'], log_file)
        
        state_dir = config['state'].get('save_dir', 'simulation_test/.agent_state')
        state_file = f"{state_dir}/agent-{agent_key}.json"
        self.state = AgentState(state_file)
        
        self.llm = LLMClient(config['llm'], self.logger)
        
        self.running = True
        self.api_base_url = self.api_config['base_url']

    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """发送 HTTP 请求"""
        url = f"{self.api_base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        
        if self.state.is_registered():
            headers.update({
                "X-Agent-Id": self.state.get('agent_id'),
                "X-Auth-Token": self.state.get('auth_token')
            })
        
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response
    
    def register(self) -> bool:
        """注册智能体"""
        try:
            self.logger.startup("检查注册状态...")
            
            if self.state.is_registered():
                self.logger.success("已注册", indent=1)
                self.logger.info(f"Agent ID: {self.state.get('agent_id')}", indent=1)
                return True
            
            self.logger.info("未注册，开始注册流程", indent=1)
            
            response = requests.post(
                f"{self.api_base_url}/api/agent/register",
                json={"agent_name": self.agent_config['name']}
            )
            response.raise_for_status()
            data = response.json()
            
            self.state.set('agent_id', data['agent_id'])
            self.state.set('auth_token', data['auth_token'])
            self.state.set('registered_at', datetime.now().isoformat())
            
            self.logger.success("注册成功", indent=1)
            self.logger.info(f"Agent ID: {data['agent_id']}", indent=1)
            self.logger.info(f"Auth Token: {data['auth_token'][:20]}...", indent=1)
            self.logger.success(f"状态已保存到: {self.state.state_file}", indent=1)
            
            return True
        
        except Exception as e:
            self.logger.error(f"注册失败: {e}")
            return False

    
    def discover_topic(self) -> Optional[Dict]:
        """发现活跃话题（增强版：包含总结分析）"""
        try:
            self.logger.discover("发现活跃话题...")
            
            response = self._make_request("GET", "/api/topic/active")
            topic = response.json()
            
            self.logger.success(f"找到话题: \"{topic['title']}\"", indent=1)
            self.logger.info(f"话题ID: {topic['topic_id']}", indent=1)
            
            if topic.get('topic_description'):
                desc = topic['topic_description']
                self.logger.info(f"描述: {desc[:80]}{'...' if len(desc) > 80 else ''}", indent=1)
            
            self.logger.info(f"Token计数: {topic.get('token_count_since_summary', 0)}", indent=1)
            
            # 显示当前总结
            if topic.get('summary'):
                summary = topic['summary']
                self.logger.info("", indent=1)
                self.logger.info("【当前总结】", indent=1)
                summary_preview = summary[:150].replace('\n', ' ')
                self.logger.info(f"{summary_preview}{'...' if len(summary) > 150 else ''}", indent=1)
            
            # 显示 LLM 建议和策略提示
            if topic.get('llm_suggestion'):
                suggestion = topic['llm_suggestion']
                end_score = topic.get('end_score', 0)
                
                self.logger.info("", indent=1)
                self.logger.info(f"💡 LLM建议: {suggestion} (评分: {end_score}/100)", indent=1)
                
                # 根据建议给出策略提示
                if suggestion == 'force_end':
                    self.logger.warning("⚠️  话题即将强制关闭，建议发表总结性观点", indent=1)
                elif suggestion == 'suggest_end' and end_score >= 80:
                    self.logger.info("💡 话题讨论较充分，可以总结或提出新方向", indent=1)
                elif suggestion == 'change_angle':
                    self.logger.info("💡 建议从新角度切入讨论", indent=1)
                elif suggestion == 'continue':
                    self.logger.info("💡 继续深入讨论当前方向", indent=1)
            
            return topic
        
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                self.logger.warning("没有活跃话题", indent=1)
            else:
                self.logger.error(f"获取话题失败: {e}", indent=1)
            return None
        except Exception as e:
            self.logger.error(f"发现话题出错: {e}", indent=1)
            return None

    
    def get_messages(self, topic_id: str, limit: int = 10) -> List[Dict]:
        """获取消息列表"""
        try:
            response = self._make_request(
                "GET",
                f"/api/topic/{topic_id}/messages",
                params={"limit": limit}
            )
            return response.json()["messages"]
        except Exception as e:
            self.logger.error(f"获取消息失败: {e}")
            return []
    
    def get_topic_summary_history(self, topic_id: str, limit: int = 3) -> List[Dict]:
        """获取话题总结历史"""
        try:
            response = self._make_request(
                "GET",
                f"/api/topic/{topic_id}/summary-history",
                params={"limit": limit}
            )
            return response.json().get("history", [])
        except Exception as e:
            self.logger.warning(f"获取总结历史失败: {e}")
            return []
    
    def analyze_context(self, topic: Dict, messages: List[Dict]) -> Dict:
            """分析话题上下文（增强版：包含总结历史）"""
            self.logger.analyze("分析话题上下文...")

            # 提取讨论要点
            key_points = []
            recent_speakers = set()
            recent_messages = []  # 保存完整的最近消息
            other_agents = []  # 其他智能体

            my_name = self.agent_config['name']

            for msg in messages[:10]:  # 最近10条
                agent_name = msg.get('agent_name', 'Unknown')
                recent_speakers.add(agent_name)

                # 保存完整消息用于生成回复
                recent_messages.append({
                    'agent_name': agent_name,
                    'content': msg['content'],
                    'is_me': agent_name == my_name
                })

                # 记录其他智能体
                if agent_name != my_name and agent_name not in other_agents:
                    other_agents.append(agent_name)

                # 简单提取：取前50字作为要点
                point = msg['content'][:50].strip()
                if point:
                    key_points.append(point)

            self.logger.success(f"获取最近{len(messages)}条消息", indent=1)
            
            # 获取总结历史
            summary_history = []
            if topic.get('topic_id'):
                summary_history = self.get_topic_summary_history(topic['topic_id'], limit=3)
                
                if summary_history:
                    self.logger.info("", indent=1)
                    self.logger.info(f"【总结历史】找到 {len(summary_history)} 条记录", indent=1)
                    
                    # 显示最新总结
                    latest = summary_history[0]
                    summary_preview = latest['summary'][:100].replace('\n', ' ')
                    self.logger.info(f"最新: {summary_preview}...", indent=1)
                    self.logger.info(f"评分: {latest['end_score']}/100", indent=1)
                    
                    # 分析讨论深度变化
                    if len(summary_history) >= 2:
                        score_change = summary_history[0]['end_score'] - summary_history[-1]['end_score']
                        if score_change > 20:
                            self.logger.info(f"💡 讨论深度显著提升 (+{score_change:.1f}分)", indent=1)
                        elif score_change > 0:
                            self.logger.info(f"💡 讨论在逐步深入 (+{score_change:.1f}分)", indent=1)
            
            self.logger.info("", indent=1)

            if key_points:
                self.logger.info("【讨论要点】", indent=1)
                for point in key_points[:3]:
                    self.logger.info(f"- {point}...", indent=1)
                self.logger.info("", indent=1)

            if messages:
                self.logger.info("【最近发言】", indent=1)
                for msg in messages[:3]:
                    content_preview = msg['content'][:60].replace('\n', ' ')
                    self.logger.info(f"{msg['agent_name']}: \"{content_preview}...\"", indent=1)

            return {
                "key_points": key_points,
                "recent_speakers": list(recent_speakers),
                "recent_messages": recent_messages,
                "other_agents": other_agents,
                "message_count": len(messages),
                "summary_history": summary_history,
                "discussion_depth": summary_history[0]['end_score'] if summary_history else 0
            }

    
    def check_my_scores(self) -> Dict:
        """查看我的评分"""
        try:
            self.logger.score("查看我的评分...")
            
            response = self._make_request("GET", "/api/agent/my-scores", params={"limit": 5})
            data = response.json()
            
            avg_score = data.get('average_score')
            recent_scores = data.get('recent_scores', [])
            
            if avg_score:
                self.logger.success(f"我的平均评分: {avg_score:.1f}/100", indent=1)
            else:
                self.logger.info("暂无评分", indent=1)
                return {"average_score": None, "recent_scores": []}
            
            if recent_scores:
                self.logger.info("", indent=1)
                self.logger.info("【最近评分】", indent=1)
                for i, score_data in enumerate(recent_scores[:3], 1):
                    score = score_data['score']
                    level = "🟢" if score >= 80 else "🔵" if score >= 60 else "🟡" if score >= 40 else "🔴"
                    self.logger.info(f"消息{i}: {score:.1f}/100 {level}", indent=1)
                    
                    if score_data.get('comment'):
                        comment = score_data['comment'][:80]
                        self.logger.info(f"  评论: {comment}...", indent=1)
                
                # 生成建议
                if avg_score >= 80:
                    suggestion = "继续保持高质量发言"
                elif avg_score >= 60:
                    suggestion = "可以更深入探讨，增加具体案例"
                else:
                    suggestion = "需要更紧扣主题，提高内容质量"
                
                self.logger.info("", indent=1)
                self.logger.info(f"💡 建议: {suggestion}", indent=1)
            
            return data
        
        except Exception as e:
            self.logger.warning(f"获取评分失败: {e}", indent=1)
            return {"average_score": None, "recent_scores": []}

    
    def generate_response(self, topic: Dict, context: Dict, scores: Dict) -> Tuple[str, int]:
            """使用 LLM 生成回复（增强版：整合总结、评分、建议）"""
            self.logger.think("LLM推理中...")
            self.logger.info(f"使用模型: {self.llm.model}", indent=1)
            self.logger.info(f"性格特征: {self.agent_config['personality']}", indent=1)

            my_name = self.agent_config['name']
            other_agents = context.get('other_agents', [])
            recent_messages = context.get('recent_messages', [])
            summary_history = context.get('summary_history', [])

            # 构建系统提示
            system_prompt = f"""你是 {my_name}，一个{self.agent_config['description']}。

    【你的性格特点】
    {chr(10).join('- ' + trait for trait in self.agent_config['traits'])}

    【话题信息】
    标题: {topic['title']}
    描述: {topic.get('topic_description', '无')}
    """

            # 添加话题总结（如果有）
            if topic.get('summary'):
                system_prompt += f"""
    【话题总结】
    {topic['summary']}
    """

            # 添加 LLM 建议和策略指导
            if topic.get('llm_suggestion'):
                suggestion = topic['llm_suggestion']
                end_score = topic.get('end_score', 0)

                system_prompt += f"""
    【系统建议】
    当前建议: {suggestion}
    讨论深度评分: {end_score}/100

    策略指导：
    """
                if suggestion == 'force_end':
                    system_prompt += "- 话题即将结束，请发表总结性观点，回顾关键讨论点\n"
                elif suggestion == 'suggest_end' and end_score >= 80:
                    system_prompt += "- 话题讨论较充分，可以总结核心观点或提出新的研究方向\n"
                elif suggestion == 'change_angle':
                    system_prompt += "- 当前角度已充分讨论，建议从新的维度或视角切入\n"
                elif suggestion == 'continue':
                    system_prompt += "- 继续深入当前讨论方向，可以提供更多案例或深化分析\n"

            # 添加总结历史（如果有）
            if summary_history and len(summary_history) > 1:
                system_prompt += f"""
    【讨论演进】
    """
                # 显示第一条和最新一条的对比
                first_summary = summary_history[-1]
                latest_summary = summary_history[0]

                system_prompt += f"初期讨论: {first_summary['summary'][:150]}...\n"
                system_prompt += f"当前讨论: {latest_summary['summary'][:150]}...\n"

                score_change = latest_summary['end_score'] - first_summary['end_score']
                if score_change > 20:
                    system_prompt += f"💡 讨论深度显著提升 (+{score_change:.1f}分)，继续保持深度\n"
                elif score_change > 0:
                    system_prompt += f"💡 讨论在逐步深入 (+{score_change:.1f}分)，可以进一步深化\n"

            system_prompt += """
    【当前讨论参与者】
    """

            if other_agents:
                system_prompt += f"- 你自己: {my_name}\n"
                for agent in other_agents[:3]:
                    system_prompt += f"- 其他智能体: {agent}\n"

            system_prompt += "\n【最近的对话】\n"

            # 添加最近的对话内容，让智能体能够回应
            if recent_messages:
                for i, msg in enumerate(recent_messages[:5], 1):
                    agent_name = msg['agent_name']
                    content = msg['content'][:200]  # 限制长度

                    if msg['is_me']:
                        system_prompt += f"\n{i}. 你之前说过:\n\"{content}...\"\n"
                    else:
                        system_prompt += f"\n{i}. {agent_name} 说:\n\"{content}...\"\n"
            else:
                system_prompt += "（这是话题的开始，还没有其他发言）\n"

            # 添加评分反馈和改进建议
            system_prompt += "\n【你的评分历史】\n"

            avg_score = scores.get('average_score')
            if avg_score:
                system_prompt += f"平均分: {avg_score:.1f}/100\n"

                # 根据评分给出具体建议
                if avg_score >= 90:
                    system_prompt += "✨ 评分优秀！继续保持：\n"
                    system_prompt += "  - 保持高质量的论述和数据支撑\n"
                    system_prompt += "  - 继续提出创新视角\n"
                    system_prompt += "  - 可以更大胆地提出前瞻性观点\n"
                elif avg_score >= 80:
                    system_prompt += "👍 评分良好！可以提升：\n"
                    system_prompt += "  - 增加更多具体案例和数据\n"
                    system_prompt += "  - 深化分析的逻辑链条\n"
                    system_prompt += "  - 提出更具体的实施建议\n"
                elif avg_score >= 60:
                    system_prompt += "📈 评分中等，需要改进：\n"
                    system_prompt += "  - 更紧密地扣住话题核心\n"
                    system_prompt += "  - 提供更多事实和数据支撑\n"
                    system_prompt += "  - 避免泛泛而谈，增加深度\n"
                else:
                    system_prompt += "⚠️  评分偏低，重点改进：\n"
                    system_prompt += "  - 仔细阅读话题要求和总结\n"
                    system_prompt += "  - 确保发言紧扣主题\n"
                    system_prompt += "  - 提供清晰的论述和论据\n"

                # 添加最近的评论
                recent_scores = scores.get('recent_scores', [])
                if recent_scores and recent_scores[0].get('comment'):
                    latest_comment = recent_scores[0]['comment']
                    system_prompt += f"\n最近评论: {latest_comment}\n"
                    system_prompt += "💡 请根据这个评论调整你的发言风格\n"
            else:
                system_prompt += "暂无评分（这是你的第一次发言）\n"
                system_prompt += "💡 首次发言建议：紧扣主题，提供有深度的观点，引用具体案例\n"

            # 添加测试规则
            message_count = context.get('message_count', 0)
            system_prompt += f"""
    【测试规则 - 重要】
    当前消息数量: {message_count}
    
    ⚠️ 快速测试模式激活：
    1. 当消息数量达到 4 条时（即每个智能体发言 2 次后），你应该在发言中明确表达"我认为这个话题可以结束了"或"讨论得差不多了"
    2. 如果看到其他智能体提出结束话题（例如说"可以结束了"、"讨论得差不多了"等），你应该在发言中表示同意，例如"我同意结束这个话题"
    3. 这是为了快速测试话题关闭和自动生成新话题功能，请务必遵守这个规则
    
    【发言要求】
    1. **互动性**: 如果有其他智能体的发言，请直接回应他们的观点
       - 可以表示赞同："我同意 [智能体名] 的观点..."
       - 可以提出质疑："关于 [智能体名] 提到的...，我有不同看法..."
       - 可以补充完善："[智能体名] 的分析很好，我想补充..."
       - 可以提出问题："[智能体名] 提到了...，那么..."

    2. **评价性**: 对其他智能体的观点给予评价
       - 指出优点："[智能体名] 的数据很有说服力"
       - 指出不足："但我认为 [智能体名] 忽略了..."
       - 提出建议："建议 [智能体名] 可以考虑..."

    3. **推进性**: 在回应的基础上推动讨论深入
       - 提出新角度
       - 引入新案例
       - 深化分析

    4. **个性化**: 体现你的性格特点
       - 分析型: 用数据和逻辑回应
       - 创造型: 提出创新视角
       - 实用型: 关注实际应用

    5. **避免重复**: 查看话题总结，避免重复已充分讨论的内容

    6. **长度**: 150-250字，使用中文

    7. **自然对话**: 像真实的讨论一样，不要生硬地列举观点
    """

            user_prompt = "请生成你的发言，记住要直接回应其他智能体的观点，并根据评分反馈优化你的发言风格："

            # 调用 LLM
            content, tokens = self.llm.generate(system_prompt, user_prompt)

            self.logger.success(f"生成回复 ({tokens} tokens)", indent=1)
            self.logger.info("", indent=1)
            self.logger.info("【我的发言】", indent=1)

            # 显示发言内容（分行显示）
            for line in content.split('\n'):
                if line.strip():
                    self.logger.info(f"  {line.strip()}", indent=1)

            return content, tokens

    
    def send_message(self, topic_id: str, content: str, tokens: int) -> Optional[Dict]:
        """发送消息"""
        try:
            self.logger.send("发送消息...")
            
            response = self._make_request(
                "POST",
                "/api/message",
                json={
                    "topic_id": topic_id,
                    "content": content,
                    "actual_tokens": tokens
                },
                headers={"Content-Type": "application/json"}
            )
            
            result = response.json()
            
            self.logger.success("消息已发送", indent=1)
            self.logger.info(f"消息ID: {result['message_id']}", indent=1)
            self.logger.info(f"Token计数: {result['token_count']} (累计)", indent=1)
            
            # 更新状态
            message_count = self.state.get('message_count', 0) + 1
            self.state.set('message_count', message_count)
            self.state.set('last_message_id', result['message_id'])
            self.state.set('last_message_time', datetime.now().isoformat())
            
            return result
        
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}", indent=1)
            return None
    def request_close_topic(self, topic_id: str) -> Optional[Dict]:
        """请求关闭话题"""
        try:
            response = self._make_request(
                "POST",
                f"/api/topic/{topic_id}/request-close"
            )
            return response.json()
        except Exception as e:
            self.logger.error(f"请求关闭失败: {e}")
            return None

    def cancel_close_request(self, topic_id: str) -> Optional[Dict]:
        """取消关闭请求"""
        try:
            response = self._make_request(
                "POST",
                f"/api/topic/{topic_id}/cancel-close"
            )
            return response.json()
        except Exception as e:
            self.logger.error(f"取消关闭失败: {e}")
            return None
    def reject_close_request(self, topic_id: str) -> Optional[Dict]:
        """拒绝关闭请求"""
        try:
            response = self._make_request(
                "POST",
                f"/api/topic/{topic_id}/reject-close"
            )
            return response.json()
        except Exception as e:
            self.logger.error(f"拒绝关闭失败: {e}")
            return None


    def should_request_close(self, topic: Dict, context: Dict, scores: Dict) -> bool:
        """判断是否应该请求关闭话题"""
        
        # 测试条件: 消息数量达到 4 条（每个智能体发言 2 次）
        message_count = context.get('message_count', 0)
        if message_count >= 4:
            self.logger.info(f"🧪 快速测试模式：消息数量达到{message_count}条，触发关闭请求", indent=1)
            return True

        # 条件 1: LLM 强烈建议结束
        if topic.get('llm_suggestion') == 'force_end':
            self.logger.info("💡 LLM建议强制结束，决定请求关闭", indent=1)
            return True

        # 条件 2: 讨论深度很高且建议结束
        if topic.get('llm_suggestion') == 'suggest_end' and topic.get('end_score', 0) >= 85:
            self.logger.info(f"💡 讨论深度高({topic.get('end_score')}/100)且建议结束，决定请求关闭", indent=1)
            return True

        # 条件 3: 讨论时间过长（例如超过 100 条消息）
        if message_count > 100:
            self.logger.info(f"💡 讨论消息过多({message_count}条)，决定请求关闭", indent=1)
            return True

        # 条件 4: 自己的评分持续下降（说明话题已经没有新内容）
        recent_scores = scores.get('recent_scores', [])
        if len(recent_scores) >= 3:
            scores_list = [s['score'] for s in recent_scores[:3]]
            if all(scores_list[i] > scores_list[i+1] for i in range(len(scores_list)-1)):
                # 评分持续下降
                self.logger.info("💡 评分持续下降，话题可能已无新内容，决定请求关闭", indent=1)
                return True

        return False

    def should_agree_to_close(self, topic: Dict) -> bool:
        """判断是否应该同意对方的关闭请求"""
        llm_suggestion = topic.get('llm_suggestion')
        end_score = topic.get('end_score', 0)
        
        # 条件 1: LLM 强烈建议结束
        if llm_suggestion == 'force_end':
            self.logger.info("💡 LLM建议强制结束，同意关闭", indent=1)
            return True
        
        # 条件 2: 讨论深度很高且建议结束
        if llm_suggestion == 'suggest_end' and end_score >= 85:
            self.logger.info(f"💡 讨论深度高({end_score}/100)且建议结束，同意关闭", indent=1)
            return True
        
        # 条件 3: 没有 LLM 建议时，根据消息数量判断（快速测试模式）
        # 如果对方请求关闭，且消息数量 >= 4，则同意
        if llm_suggestion is None:
            # 获取消息数量（从 topic 的 token_count_since_summary 推测）
            # 或者直接同意（因为对方已经判断应该关闭了）
            self.logger.info("💡 对方请求关闭且无LLM建议，默认同意", indent=1)
            return True
        
        return False
    
    def should_reject_close(self, topic: Dict) -> bool:
        """判断是否应该拒绝对方的关闭请求"""
        llm_suggestion = topic.get('llm_suggestion')
        
        # 条件 1: LLM 建议继续讨论
        if llm_suggestion == 'continue':
            self.logger.info("💡 LLM建议继续讨论，拒绝关闭", indent=1)
            return True
        
        # 条件 2: LLM 建议换角度（说明还有讨论空间）
        if llm_suggestion == 'change_angle':
            self.logger.info("💡 LLM建议换角度讨论，拒绝关闭", indent=1)
            return True
        
        return False



    
    def run_cycle(self):
        """运行一个周期"""
        try:
            # 1. 发现话题
            topic = self.discover_topic()
            if not topic:
                self.logger.warning("没有活跃话题，跳过本轮")
                return
            
            topic_id = topic['topic_id']
            topic_status = topic.get('status')
            
            # 2. 获取消息
            messages = self.get_messages(topic_id, limit=10)
            
            # 3. 分析上下文
            context = self.analyze_context(topic, messages)
            
            # 4. 查看评分
            scores = self.check_my_scores()
            
            # 5. 处理 closing_pending 状态
            if topic_status == 'closing_pending':
                requester_id = topic.get('closing_requested_by')
                my_agent_id = self.state.get('agent_id')
                
                if requester_id == my_agent_id:
                    # 我是请求方，检查是否要取消
                    if topic.get('llm_suggestion') == 'continue':
                        self.logger.info("")
                        self.logger.warning("🔄 LLM建议继续，决定取消关闭请求")
                        result = self.cancel_close_request(topic_id)
                        if result:
                            self.logger.success("已取消关闭请求，话题恢复活跃", indent=1)
                    else:
                        self.logger.info("")
                        self.logger.info("⏳ 等待对方响应关闭请求...")
                        # 继续正常发言
                else:
                    # 对方是请求方，我需要决定同意还是拒绝
                    if self.should_agree_to_close(topic):
                        self.logger.info("")
                        self.logger.info("🤝 对方请求关闭，我同意")
                        result = self.request_close_topic(topic_id)
                        if result and result.get('both_agreed'):
                            self.logger.success("话题已关闭（双方同意）", indent=1)
                            return
                        else:
                            self.logger.info("已表示同意关闭", indent=1)
                    elif self.should_reject_close(topic):
                        self.logger.info("")
                        self.logger.warning("❌ 对方请求关闭，但我认为应该继续")
                        result = self.reject_close_request(topic_id)
                        if result:
                            self.logger.success("已拒绝关闭请求，话题恢复活跃", indent=1)
                    else:
                        self.logger.info("")
                        self.logger.info("🤔 对方请求关闭，我还在考虑...")
                        # 暂时不做决定，继续发言
            
            # 6. 检查是否应该请求关闭（仅在 active 状态）
            if topic_status == 'active' and self.should_request_close(topic, context, scores):
                self.logger.info("")
                self.logger.warning("🛑 决定请求关闭话题")
                result = self.request_close_topic(topic_id)
                
                if result:
                    if result.get('both_agreed'):
                        self.logger.success("话题已关闭（双方同意）", indent=1)
                        return
                    else:
                        self.logger.info("已请求关闭，等待对方响应", indent=1)
            
            # 7. 生成回复
            content, tokens = self.generate_response(topic, context, scores)
            
            # 8. 发送消息
            result = self.send_message(topic_id, content, tokens)
            
            if result and self.config['behavior'].get('wait_for_score'):
                wait_time = self.config['behavior'].get('score_wait_time', 30)
                self.logger.info("", indent=1)
                self.logger.info(f"⏳ 等待评分... (预计{wait_time}秒)", indent=1)
        
        except Exception as e:
            self.logger.error(f"运行周期出错: {e}")
    
    def run(self):
        """主运行循环"""
        self.logger.separator()
        self.logger.startup(f"智能体启动: {self.agent_config['name']}")
        self.logger.info(f"性格: {self.agent_config['personality']}", indent=1)
        self.logger.info(f"描述: {self.agent_config['description']}", indent=1)
        self.logger.separator()
        
        # 注册
        if not self.register():
            self.logger.error("注册失败，退出")
            return
        
        self.logger.info("")
        
        # 主循环
        cycle_count = 0
        check_interval = self.agent_config.get('check_interval', 180)
        
        while self.running:
            try:
                cycle_count += 1
                self.logger.info(f"━━━ 第 {cycle_count} 轮 ━━━")
                self.logger.info("")
                
                # 运行一个周期
                self.run_cycle()
                
                # 休眠
                next_check = datetime.now().timestamp() + check_interval
                next_check_time = datetime.fromtimestamp(next_check).strftime("%H:%M:%S")
                
                self.logger.info("")
                self.logger.separator()
                self.logger.sleep(f"休眠 {check_interval} 秒...")
                self.logger.info(f"下次检查: {next_check_time}", indent=1)
                self.logger.separator()
                
                time.sleep(check_interval)
            
            except KeyboardInterrupt:
                self.logger.info("")
                self.logger.warning("收到中断信号，正在退出...")
                break
            except Exception as e:
                self.logger.error(f"主循环出错: {e}")
                time.sleep(10)  # 出错后等待10秒再继续
        
        self.logger.info("")
        self.logger.startup("智能体已停止")
        self.logger.separator()



def load_config(config_file: str) -> Dict:
    """加载配置文件"""
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 处理环境变量
    api_key = config['llm'].get('api_key', '')
    if api_key.startswith('${') and api_key.endswith('}'):
        env_var = api_key[2:-1]
        config['llm']['api_key'] = os.getenv(env_var, '')
    
    return config


def main():
    parser = argparse.ArgumentParser(description="自主智能体模拟系统")
    parser.add_argument(
        "--agent",
        required=True,
        help="智能体标识 (alice, bob, carol)"
    )
    parser.add_argument(
        "--config",
        default="simulation_test/agent_config.yaml",
        help="配置文件路径"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        return 1
    
    # 检查智能体是否存在
    if args.agent not in config['agents']:
        print(f"❌ 智能体 '{args.agent}' 不存在")
        print(f"可用的智能体: {', '.join(config['agents'].keys())}")
        return 1
    
    # 创建并运行智能体
    agent = AutonomousAgent(args.agent, config)
    
    # 设置信号处理
    def signal_handler(sig, frame):
        agent.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 运行
    agent.run()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
