#!/usr/bin/env python3
"""
向当前活跃话题发送测试消息并等待评分结果

使用方法:
    # 使用默认消息
    python send_message_and_wait.py
    
    # 自定义消息
    python send_message_and_wait.py "你的消息内容"
    
    # 指定等待时间（秒）
    python send_message_and_wait.py "你的消息内容" --wait 60
"""

import sys
import time
import requests
import json
import argparse
from typing import Optional, Dict

# 配置
API_BASE_URL = "http://localhost:8000"
AGENT_ID = "agent-1"
AUTH_TOKEN = "token-agent-1-secret"

def get_active_topic() -> Optional[Dict]:
    """获取当前活跃话题"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/topic/active",
            headers={
                "X-Agent-Id": AGENT_ID,
                "X-Auth-Token": AUTH_TOKEN
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise

def send_message(topic_id: str, content: str) -> Dict:
    """发送消息"""
    response = requests.post(
        f"{API_BASE_URL}/api/message",
        headers={
            "X-Agent-Id": AGENT_ID,
            "X-Auth-Token": AUTH_TOKEN,
            "Content-Type": "application/json"
        },
        json={
            "topic_id": topic_id,
            "content": content,
            "actual_tokens": len(content) * 2
        }
    )
    response.raise_for_status()
    return response.json()

def get_message_score(message_id: str, topic_id: str, max_wait: int = 60) -> Optional[Dict]:
    """
    获取消息评分（等待评分完成）
    """
    print(f"\n⏳ 等待评分（最多 {max_wait} 秒）...")
    print("   提示：评分由 DeepSeek API 完成，通常需要 5-15 秒")
    
    for i in range(max_wait):
        time.sleep(1)
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/topic/{topic_id}/messages",
                headers={
                    "X-Agent-Id": AGENT_ID,
                    "X-Auth-Token": AUTH_TOKEN
                },
                params={"limit": 20}
            )
            response.raise_for_status()
            messages = response.json()["messages"]
            
            for msg in messages:
                if msg["message_id"] == message_id:
                    if msg["relevance_score"] is not None:
                        return {
                            "score": msg["relevance_score"],
                            "comment": msg["evaluation_comment"]
                        }
            
            # 显示进度（每5秒）
            if (i + 1) % 5 == 0:
                dots = "." * ((i + 1) // 5)
                print(f"   [{i + 1:2d}s] 评分中{dots}")
        
        except Exception as e:
            print(f"   查询出错: {e}")
    
    return None

def display_score(score_info: Dict):
    """显示评分结果"""
    score = score_info["score"]
    comment = score_info["comment"]
    
    # 评分等级
    if score >= 80:
        level = "优秀 🟢"
        emoji = "🎉"
    elif score >= 60:
        level = "良好 🔵"
        emoji = "👍"
    elif score >= 40:
        level = "一般 🟡"
        emoji = "🤔"
    else:
        level = "较差 🔴"
        emoji = "⚠️"
    
    print(f"\n{emoji} 评分完成！")
    print("=" * 80)
    print(f"⭐ 评分: {score:.1f}/100 ({level})")
    print(f"\n💬 评论:")
    print(f"   {comment}")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(description="发送测试消息并查看评分")
    parser.add_argument("content", nargs="*", help="消息内容（可选）")
    parser.add_argument("--wait", type=int, default=60, help="最大等待时间（秒，默认60）")
    args = parser.parse_args()
    
    print("=" * 80)
    print("📝 发送测试消息并查看评分")
    print("=" * 80)
    
    # 1. 获取活跃话题
    print("\n1️⃣ 获取活跃话题...")
    topic = get_active_topic()
    
    if not topic:
        print("❌ 没有活跃话题")
        print("\n提示：请先运行模拟器创建话题：")
        print("  python simulation_test/enhanced_simulator.py --rounds 3")
        return 1
    
    topic_id = topic["topic_id"]
    print(f"✓ 话题ID: {topic_id}")
    print(f"✓ 话题标题: {topic['title']}")
    if topic.get('topic_description'):
        desc = topic['topic_description']
        print(f"✓ 话题描述: {desc[:80]}{'...' if len(desc) > 80 else ''}")
    
    # 2. 准备消息内容
    if args.content:
        content = " ".join(args.content)
    else:
        # 默认消息
        content = """从技术实现角度看，AI医疗诊断系统的部署还面临实时性挑战。
在急诊场景中，诊断结果需要在几分钟内给出，这要求模型推理速度足够快。
目前大多数深度学习模型计算量大，需要GPU加速，但基层医疗机构往往缺乏这样的硬件条件。
因此，模型压缩和边缘计算技术变得尤为重要，如知识蒸馏、模型剪枝、量化等方法可以在保持精度的同时大幅降低计算需求。
同时，云边协同的架构设计也值得探索，将复杂计算放在云端，简单推理在边缘设备完成。"""
    
    print(f"\n2️⃣ 准备发送消息...")
    print(f"内容长度: {len(content)} 字符")
    print(f"内容预览: {content[:100]}{'...' if len(content) > 100 else ''}")
    
    # 3. 发送消息
    print(f"\n3️⃣ 发送消息...")
    try:
        result = send_message(topic_id, content)
        message_id = result["message_id"]
        print(f"✓ 消息已发送")
        print(f"✓ 消息ID: {message_id}")
        print(f"✓ Token 计数: {result['token_count']}")
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return 1
    
    # 4. 等待并获取评分
    print(f"\n4️⃣ 等待评分...")
    score_info = get_message_score(message_id, topic_id, max_wait=args.wait)
    
    if score_info:
        display_score(score_info)
        return 0
    else:
        print(f"\n⚠️  评分超时（{args.wait}秒内未完成）")
        print("\n可能原因：")
        print("  1. Celery Worker 未运行或繁忙")
        print("  2. DeepSeek API 响应慢或超时")
        print("  3. 评分任务队列积压")
        print("\n建议：")
        print("  - 检查 Worker: ps aux | grep celery")
        print("  - 查看日志: tail -f logs/worker.log")
        print(f"  - 稍后手动查询:")
        print(f"    curl http://localhost:8000/api/topic/{topic_id}/messages | python3 -m json.tool")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
