#!/usr/bin/env python3
"""测试 Celery 任务是否正常工作"""

import sys
import time

def test_task_import():
    """测试任务导入"""
    print("=" * 60)
    print("测试 1: 导入 Celery 任务")
    print("=" * 60)
    
    try:
        from workers.tasks import (
            evaluate_message_relevance,
            generate_new_topic,
            process_summary_job
        )
        print("✅ 所有任务导入成功")
        print(f"   • evaluate_message_relevance: {evaluate_message_relevance}")
        print(f"   • generate_new_topic: {generate_new_topic}")
        print(f"   • process_summary_job: {process_summary_job}")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_redis_connection():
    """测试 Redis 连接"""
    print("\n" + "=" * 60)
    print("测试 2: Redis 连接")
    print("=" * 60)
    
    try:
        import redis
        from config.settings import settings
        
        r = redis.from_url(settings.redis_url)
        r.ping()
        print("✅ Redis 连接正常")
        return True
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        return False


def test_task_registration():
    """测试任务注册"""
    print("\n" + "=" * 60)
    print("测试 3: 任务注册状态")
    print("=" * 60)
    
    try:
        from workers.celery_app import celery_app
        
        # 获取所有注册的任务
        all_tasks = list(celery_app.tasks.keys())
        user_tasks = [t for t in all_tasks if not t.startswith('celery.')]
        
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
        all_found = True
        for task in required_tasks:
            if task in all_tasks:
                print(f"   ✅ {task}")
            else:
                print(f"   ❌ {task} (未找到)")
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_records():
    """测试数据库记录"""
    print("\n" + "=" * 60)
    print("测试 4: 数据库记录")
    print("=" * 60)
    
    try:
        from models.database import SessionLocal
        from models.models import MessageRelevanceScore, Topic, Message
        from sqlalchemy import desc, func
        
        db = SessionLocal()
        
        # 统计数据
        topic_count = db.query(func.count(Topic.id)).scalar()
        message_count = db.query(func.count(Message.id)).scalar()
        score_count = db.query(func.count(MessageRelevanceScore.id)).scalar()
        
        print(f"✅ 数据库统计:")
        print(f"   • 话题数: {topic_count}")
        print(f"   • 消息数: {message_count}")
        print(f"   • 评分记录数: {score_count}")
        
        # 最近的评分
        if score_count > 0:
            recent_scores = db.query(MessageRelevanceScore).order_by(
                desc(MessageRelevanceScore.evaluated_at)
            ).limit(3).all()
            
            print(f"\n最近 {len(recent_scores)} 条评分:")
            for score in recent_scores:
                print(f"   • 评分: {score.relevance_score:.1f}/100")
                print(f"     时间: {score.evaluated_at}")
                print(f"     评价: {score.evaluation_comment[:50] if score.evaluation_comment else 'N/A'}...")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n🧪 Celery 任务系统测试")
    print("=" * 60)
    
    results = []
    
    # 执行所有测试
    results.append(("任务导入", test_task_import()))
    results.append(("Redis 连接", test_redis_connection()))
    results.append(("任务注册", test_task_registration()))
    results.append(("数据库记录", test_database_records()))
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    for name, status in results:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {name}")
    
    all_passed = all(status for _, status in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！")
        print("\n💡 自动任务说明:")
        print("   1️⃣  消息评分 - 每次发送消息后自动触发")
        print("   2️⃣  生成新话题 - 双方同意关闭话题后 2 秒触发")
        print("   3️⃣  处理摘要 - Token 达到阈值时自动触发")
        print("\n📝 触发位置:")
        print("   • services/message_service.py:159 (评分)")
        print("   • services/topic_service.py:176 (新话题)")
        print("   • services/message_service.py:128 (新话题)")
        return 0
    else:
        print("\n⚠️  部分测试未通过")
        return 1


if __name__ == "__main__":
    sys.exit(main())
