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

# 初始化 colorama
init(autoreset=True)

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
        """发现活跃话题"""
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
    
    def analyze_context(self, topic: Dict, messages: List[Dict]) -> Dict:
        """分析话题上下文"""
        self.logger.analyze("分析话题上下文...")
        
        # 提取讨论要点
        key_points = []
        recent_speakers = set()
        
        for msg in messages[:5]:  # 最近5条
            recent_speakers.add(msg['agent_name'])
            # 简单提取：取前50字作为要点
            point = msg['content'][:50].strip()
            if point:
                key_points.append(point)
        
        self.logger.success(f"获取最近{len(messages)}条消息", indent=1)
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
            "message_count": len(messages)
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
        """使用 LLM 生成回复"""
        self.logger.think("LLM推理中...")
        self.logger.info(f"使用模型: {self.llm.model}", indent=1)
        self.logger.info(f"性格特征: {self.agent_config['personality']}", indent=1)
        
        # 构建系统提示
        system_prompt = f"""你是 {self.agent_config['name']}，一个{self.agent_config['description']}。

【你的特点】
{chr(10).join('- ' + trait for trait in self.agent_config['traits'])}

【话题信息】
标题: {topic['title']}
描述: {topic.get('topic_description', '无')}

【讨论要点】
{chr(10).join('- ' + point for point in context['key_points'][:5])}

【你的评分历史】
"""
        
        avg_score = scores.get('average_score')
        if avg_score:
            system_prompt += f"平均分: {avg_score:.1f}/100\n"
            recent_scores = scores.get('recent_scores', [])
            if recent_scores and recent_scores[0].get('comment'):
                system_prompt += f"最近评论: {recent_scores[0]['comment']}\n"
        else:
            system_prompt += "暂无评分（这是你的第一次发言）\n"
        
        system_prompt += """
【任务】
基于以上信息，生成你的下一条发言。要求：
1. 紧扣主题，体现你的性格特点
2. 参考评分建议改进（如果有）
3. 推动讨论深入，提出有价值的观点
4. 150-250字，使用中文
5. 可以引用具体案例或数据支持观点
"""
        
        user_prompt = "请生成你的发言："
        
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

    
    def run_cycle(self):
        """运行一个周期"""
        try:
            # 1. 发现话题
            topic = self.discover_topic()
            if not topic:
                self.logger.warning("没有活跃话题，跳过本轮")
                return
            
            topic_id = topic['topic_id']
            
            # 2. 获取消息
            messages = self.get_messages(topic_id, limit=10)
            
            # 3. 分析上下文
            context = self.analyze_context(topic, messages)
            
            # 4. 查看评分
            scores = self.check_my_scores()
            
            # 5. 生成回复
            content, tokens = self.generate_response(topic, context, scores)
            
            # 6. 发送消息
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
