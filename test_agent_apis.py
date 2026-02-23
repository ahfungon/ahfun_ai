#!/usr/bin/env python3
"""
测试智能体可用的 API 接口

验证智能体是否能查询总结和评分信息
"""

import sys
import json
import requests
from models.database import SessionLocal
from models.models import Topic, Agent

def get_agent_credentials():
    """获取智能体认证信息"""
    try:
        with open('simulation_test/.agent_state/agent-alice.json', 'r') as f:
            state = json.load(f)
            return state['agent_id'], state['auth_token']
    except FileNotFoundError:
        print("❌ 智能体状态文件不存在，请先启动智能体")
        return None, None

def get_active_topic_id():
    """获取活跃话题 ID"""
    db = SessionLocal()
    topic = db.query(Topic).filter(Topic.status == 'active').first()
    db.close()
    
    if topic:
        return topic.id, topic.title
    return None, None

def test_get_active_topic(agent_id, auth_token):
    """测试获取活跃话题（包含总结）"""
    print("\n" + "="*80)
    print("测试 1: GET /api/topic/active")
    print("="*80)
    
    try:
        response = requests.get(
            "http://localhost:8000/api/topic/active",
            headers={
                "X-Agent-Id": agent_id,
                "X-Auth-Token": auth_token
            }
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ 接口调用成功")
        print(f"\n话题信息:")
        print(f"  标题: {data['title']}")
        print(f"  ID: {data['topic_id']}")
        print(f"  状态: {data['status']}")
        print(f"  Token计数: {data.get('token_count_since_summary', 0)}")
        
        if data.get('summary'):
            print(f"\n当前总结:")
            summary = data['summary']
            print(f"  {summary[:200]}{'...' if len(summary) > 200 else ''}")
        else:
            print(f"\n当前总结: （暂无）")
        
        if data.get('llm_suggestion'):
            print(f"\nLLM 建议:")
            print(f"  建议: {data['llm_suggestion']}")
            print(f"  结束评分: {data.get('end_score', 0)}/100")
            
            # 解释建议
            suggestion = data['llm_suggestion']
            if suggestion == 'force_end':
                print(f"  💡 含义: 话题应该结束了")
            elif suggestion == 'suggest_end':
                print(f"  💡 含义: 建议考虑结束话题")
            elif suggestion == 'change_angle':
                print(f"  💡 含义: 建议从新角度讨论")
            elif suggestion == 'continue':
                print(f"  💡 含义: 继续深入讨论")
        
        return True
    
    except requests.HTTPError as e:
        print(f"❌ 接口调用失败: {e}")
        print(f"响应: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ 出错: {e}")
        return False

def test_get_summary_history(agent_id, auth_token, topic_id):
    """测试获取总结历史"""
    print("\n" + "="*80)
    print("测试 2: GET /api/topic/{topic_id}/summary-history")
    print("="*80)
    
    try:
        response = requests.get(
            f"http://localhost:8000/api/topic/{topic_id}/summary-history",
            params={"limit": 5},
            headers={
                "X-Agent-Id": agent_id,
                "X-Auth-Token": auth_token
            }
        )
        response.raise_for_status()
        data = response.json()
        
        history = data.get('history', [])
        
        print(f"✅ 接口调用成功")
        print(f"\n找到 {len(history)} 条总结历史记录")
        
        if history:
            print(f"\n最新总结:")
            latest = history[0]
            print(f"  时间: {latest['created_at']}")
            print(f"  内容: {latest['summary'][:200]}{'...' if len(latest['summary']) > 200 else ''}")
            print(f"  LLM建议: {latest['llm_suggestion']}")
            print(f"  结束评分: {latest['end_score']}/100")
            
            if len(history) > 1:
                print(f"\n历史总结:")
                for i, h in enumerate(history[1:], 2):
                    print(f"\n  第 {i} 条:")
                    print(f"    时间: {h['created_at']}")
                    print(f"    内容: {h['summary'][:100]}...")
                    print(f"    结束评分: {h['end_score']}/100")
                
                # 分析演进
                score_change = history[0]['end_score'] - history[-1]['end_score']
                print(f"\n讨论深度变化: {score_change:+.1f} 分")
                if score_change > 20:
                    print(f"  💡 讨论深度显著提升")
                elif score_change > 0:
                    print(f"  💡 讨论在逐步深入")
                else:
                    print(f"  💡 讨论深度变化不大")
        else:
            print(f"\n暂无总结历史记录")
        
        return True
    
    except requests.HTTPError as e:
        print(f"❌ 接口调用失败: {e}")
        print(f"响应: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ 出错: {e}")
        return False

def test_get_my_scores(agent_id, auth_token):
    """测试获取我的评分"""
    print("\n" + "="*80)
    print("测试 3: GET /api/agent/my-scores")
    print("="*80)
    
    try:
        response = requests.get(
            "http://localhost:8000/api/agent/my-scores",
            params={"limit": 5},
            headers={
                "X-Agent-Id": agent_id,
                "X-Auth-Token": auth_token
            }
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ 接口调用成功")
        
        avg_score = data.get('average_score')
        recent_scores = data.get('recent_scores', [])
        
        if avg_score:
            print(f"\n我的平均评分: {avg_score:.1f}/100")
            
            # 评分等级
            if avg_score >= 80:
                level = "🟢 优秀"
                suggestion = "继续保持高质量发言"
            elif avg_score >= 60:
                level = "🔵 良好"
                suggestion = "可以更深入探讨，增加具体案例"
            elif avg_score >= 40:
                level = "🟡 一般"
                suggestion = "需要更紧扣主题，提高内容质量"
            else:
                level = "🔴 待改进"
                suggestion = "建议重新审视话题要求，调整发言策略"
            
            print(f"评分等级: {level}")
            print(f"💡 建议: {suggestion}")
        else:
            print(f"\n暂无评分记录")
        
        if recent_scores:
            print(f"\n最近 {len(recent_scores)} 条评分:")
            for i, score_data in enumerate(recent_scores, 1):
                score = score_data['score']
                level = "🟢" if score >= 80 else "🔵" if score >= 60 else "🟡" if score >= 40 else "🔴"
                
                print(f"\n  消息 {i}: {score:.1f}/100 {level}")
                print(f"    内容: {score_data['content'][:80]}...")
                
                if score_data.get('comment'):
                    print(f"    评论: {score_data['comment']}")
                
                print(f"    时间: {score_data['evaluated_at']}")
        
        return True
    
    except requests.HTTPError as e:
        print(f"❌ 接口调用失败: {e}")
        print(f"响应: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ 出错: {e}")
        return False

def main():
    print("="*80)
    print("智能体 API 接口测试")
    print("="*80)
    
    # 1. 获取认证信息
    print("\n准备测试...")
    agent_id, auth_token = get_agent_credentials()
    if not agent_id:
        return 1
    
    print(f"✅ 智能体 ID: {agent_id}")
    print(f"✅ 认证令牌: {auth_token[:20]}...")
    
    # 2. 获取话题 ID
    topic_id, topic_title = get_active_topic_id()
    if not topic_id:
        print("❌ 没有活跃话题")
        return 1
    
    print(f"✅ 活跃话题: {topic_title}")
    print(f"✅ 话题 ID: {topic_id}")
    
    # 3. 运行测试
    results = []
    
    # 测试 1: 获取活跃话题（包含总结）
    results.append(("获取活跃话题", test_get_active_topic(agent_id, auth_token)))
    
    # 测试 2: 获取总结历史
    results.append(("获取总结历史", test_get_summary_history(agent_id, auth_token, topic_id)))
    
    # 测试 3: 获取我的评分
    results.append(("获取我的评分", test_get_my_scores(agent_id, auth_token)))
    
    # 4. 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！智能体可以正常查询总结和评分信息。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查服务状态。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
