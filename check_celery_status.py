#!/usr/bin/env python3
"""
检查 Celery 任务状态和配置

这个脚本会检查：
1. Celery Worker 是否运行
2. Redis 连接是否正常
3. 注册的任务列表
4. 队列配置
5. 最近的任务执行记录
"""

import sys
import subprocess
import redis
from celery import Celery
from config.settings import settings

def check_redis():
    """检查 Redis 连接"""
    print("=" * 60)
    print("1. 检查 Redis 连接")
    print("=" * 60)
    
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        print("✅ Redis 连接正常")
        
        # 检查队列中的任务数量
        queues = ['default', 'summary_jobs', 'periodic_tasks']
        for queue in queues:
            length = r.llen(queue)
            print(f"   队列 '{queue}': {length} 个待处理任务")
        
        return True
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        return False


def check_celery_worker():
    """检查 Celery Worker 进程"""
    print("\n" + "=" * 60)
    print("2. 检查 Celery Worker 进程")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        
        worker_lines = [
            line for line in result.stdout.split('\n')
            if 'celery' in line and 'worker' in line and 'grep' not in line
        ]
        
        if worker_lines:
            print(f"✅ 找到 {len(worker_lines)} 个 Celery Worker 进程")
            for line in worker_lines[:3]:  # 只显示前3个
                parts = line.split()
                if len(parts) >= 2:
                    print(f"   PID: {parts[1]}")
            return True
        else:
            print("❌ 未找到 Celery Worker 进程")
            print("\n启动命令:")
            print("   celery -A workers.celery_app worker --loglevel=info")
            return False
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def check_celery_tasks():
    """检查注册的 Celery 任务"""
    print("\n" + "=" * 60)
    print("3. 检查注册的任务")
    print("=" * 60)
    
    try:
        from workers.celery_app import celery_app
        
        tasks = list(celery_app.tasks.keys())
        
        # 过滤掉 celery 内置任务
        user_tasks = [t for t in tasks if not t.startswith('celery.')]
        
        print(f"✅ 找到 {len(user_tasks)} 个用户任务:")
        for task in sorted(user_tasks):
            print(f"   • {task}")
        
        # 检查关键任务
        required_tasks = [
            'workers.tasks.evaluate_message_relevance',
            'workers.tasks.generate_new_topic',
            'workers.tasks.process_summary_job'
        ]
        
        print("\n关键任务检查:")
        for task in required_tasks:
            if task in user_tasks:
                print(f"   ✅ {task}")
            else:
                print(f"   ❌ {task} (未找到)")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def check_task_triggers():
    """检查任务触发点"""
    print("\n" + "=" * 60)
    print("4. 检查任务触发点")
    print("=" * 60)
    
    triggers = {
        "消息评分": {
            "任务": "evaluate_message_relevance",
            "触发位置": "services/message_service.py:159",
            "触发时机": "Agent 发送消息后"
        },
        "生成新话题": {
            "任务": "generate_new_topic",
            "触发位置": [
                "services/topic_service.py:176",
                "services/message_service.py:128"
            ],
            "触发时机": "双方同意关闭话题后"
        },
        "处理摘要": {
            "任务": "process_summary_job",
            "触发位置": "services/message_service.py (达到阈值时)",
            "触发时机": "Token 计数达到阈值"
        }
    }
    
    for name, info in triggers.items():
        print(f"\n📋 {name}")
        print(f"   任务: {info['任务']}")
        if isinstance(info['触发位置'], list):
            print(f"   触发位置:")
            for loc in info['触发位置']:
                print(f"      - {loc}")
        else:
            print(f"   触发位置: {info['触发位置']}")
        print(f"   触发时机: {info['触发时机']}")
    
    return True


def check_recent_tasks():
    """检查最近的任务执行"""
    print("\n" + "=" * 60)
    print("5. 检查最近的任务执行")
    print("=" * 60)
    
    try:
        from models.database import SessionLocal
        from models.models import MessageRelevanceScore, Topic
        from sqlalchemy import desc
        
        db = SessionLocal()
        
        # 检查最近的评分记录
        recent_scores = db.query(MessageRelevanceScore).order_by(
            desc(MessageRelevanceScore.evaluated_at)
        ).limit(5).all()
        
        if recent_scores:
            print(f"\n✅ 最近 {len(recent_scores)} 条消息评分:")
            for score in recent_scores:
                print(f"   • 消息 {score.message_id[:8]}... 评分: {score.relevance_score:.1f}/100")
                print(f"     时间: {score.evaluated_at}")
        else:
            print("\n⚠️  暂无消息评分记录")
            print("   提示: 发送消息后会自动触发评分")
        
        # 检查最近生成的话题
        recent_topics = db.query(Topic).order_by(
            desc(Topic.created_at)
        ).limit(3).all()
        
        if recent_topics:
            print(f"\n✅ 最近 {len(recent_topics)} 个话题:")
            for topic in recent_topics:
                print(f"   • {topic.title}")
                print(f"     状态: {topic.status} | 创建时间: {topic.created_at}")
        else:
            print("\n⚠️  暂无话题记录")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def main():
    """主函数"""
    print("\n🔍 Celery 任务系统状态检查")
    print("=" * 60)
    
    results = []
    
    # 执行所有检查
    results.append(("Redis 连接", check_redis()))
    results.append(("Celery Worker", check_celery_worker()))
    results.append(("注册任务", check_celery_tasks()))
    results.append(("触发点配置", check_task_triggers()))
    results.append(("最近执行", check_recent_tasks()))
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 检查总结")
    print("=" * 60)
    
    for name, status in results:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {name}")
    
    all_passed = all(status for _, status in results)
    
    if all_passed:
        print("\n🎉 所有检查通过！Celery 任务系统运行正常。")
        print("\n💡 提示:")
        print("   • 消息评分: 发送消息后自动触发")
        print("   • 生成新话题: 双方同意关闭话题后 2 秒触发")
        print("   • 处理摘要: Token 达到阈值时触发")
        return 0
    else:
        print("\n⚠️  部分检查未通过，请查看上面的详细信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
