#!/usr/bin/env python3
"""检查所有依赖 DeepSeek API 的功能状态"""
import os
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

def print_header(text):
    """打印标题"""
    print()
    print("=" * 70)
    print(f"  {text}")
    print("=" * 70)
    print()

def print_section(text):
    """打印小节标题"""
    print()
    print(f"【{text}】")
    print("-" * 70)

def check_api_key():
    """检查 API Key 配置"""
    print_section("1. API Key 配置检查")
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    api_url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    print(f"API URL: {api_url}")
    print(f"Model: {model}")
    print(f"API Key: {api_key}")
    print()
    
    if not api_key or api_key == "your_deepseek_api_key_here":
        print("❌ API Key 未配置或使用占位符")
        print()
        print("请按照以下步骤配置：")
        print("1. 访问 https://platform.deepseek.com/ 获取 API Key")
        print("2. 编辑 .env 文件，设置 DEEPSEEK_API_KEY=sk-xxx")
        print("3. 重启 Celery Worker: pkill -f celery && python quick_start.py")
        return False
    else:
        print("✅ API Key 已配置")
        return True

def check_celery_status():
    """检查 Celery Worker 状态"""
    print_section("2. Celery Worker 状态")
    
    import subprocess
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    
    celery_processes = [
        line for line in result.stdout.split('\n')
        if 'celery' in line and 'worker' in line and 'grep' not in line
    ]
    
    if celery_processes:
        print(f"✅ Celery Worker 正在运行（{len(celery_processes)} 个进程）")
        return True
    else:
        print("❌ Celery Worker 未运行")
        print()
        print("启动方法：python quick_start.py")
        return False

def check_message_scoring():
    """检查消息评分功能"""
    print_section("3. 消息评分功能")
    
    try:
        from models.database import SessionLocal
        from models.models import MessageRelevanceScore, Message
        from sqlalchemy import func
        
        db = SessionLocal()
        
        # 统计评分记录数
        total_scores = db.query(func.count(MessageRelevanceScore.id)).scalar()
        print(f"总评分记录数: {total_scores}")
        
        if total_scores == 0:
            print("⚠️  暂无评分记录")
            print("   可能原因：")
            print("   - API Key 未配置")
            print("   - 还没有发送过消息")
            print("   - Celery Worker 未运行")
        else:
            # 获取最近的评分
            recent_scores = db.query(
                MessageRelevanceScore, Message
            ).join(
                Message, MessageRelevanceScore.message_id == Message.id
            ).order_by(
                MessageRelevanceScore.evaluated_at.desc()
            ).limit(3).all()
            
            print()
            print("最近的评分记录：")
            for score, message in recent_scores:
                print(f"  • 评分: {score.relevance_score:.1f} | "
                      f"时间: {score.evaluated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    评论: {score.evaluation_comment}")
                print(f"    内容: {message.content[:50]}...")
                print()
            
            print("✅ 消息评分功能正常")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")

def check_summary_generation():
    """检查对话总结功能"""
    print_section("4. 对话总结功能")
    
    try:
        from models.database import SessionLocal
        from models.models import SummaryHistory, SummaryJob
        from sqlalchemy import func
        
        db = SessionLocal()
        
        # 统计总结记录数
        total_summaries = db.query(func.count(SummaryHistory.id)).scalar()
        print(f"总总结记录数: {total_summaries}")
        
        # 统计总结任务
        pending_jobs = db.query(func.count(SummaryJob.id)).filter(
            SummaryJob.status == 'pending'
        ).scalar()
        processing_jobs = db.query(func.count(SummaryJob.id)).filter(
            SummaryJob.status == 'processing'
        ).scalar()
        failed_jobs = db.query(func.count(SummaryJob.id)).filter(
            SummaryJob.status == 'failed'
        ).scalar()
        
        print(f"待处理任务: {pending_jobs}")
        print(f"处理中任务: {processing_jobs}")
        print(f"失败任务: {failed_jobs}")
        
        if total_summaries == 0:
            print()
            print("⚠️  暂无总结记录")
            print("   可能原因：")
            print("   - 对话 token 数未达到阈值（默认 8000）")
            print("   - API Key 未配置")
        else:
            # 获取最近的总结
            recent_summaries = db.query(SummaryHistory).order_by(
                SummaryHistory.created_at.desc()
            ).limit(2).all()
            
            print()
            print("最近的总结记录：")
            for summary in recent_summaries:
                print(f"  • 建议: {summary.suggestion} | "
                      f"结束评分: {summary.end_score} | "
                      f"时间: {summary.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    总结: {summary.summary[:80]}...")
                print()
            
            print("✅ 对话总结功能正常")
        
        # 检查失败的任务
        if failed_jobs > 0:
            print()
            print(f"⚠️  有 {failed_jobs} 个失败的总结任务")
            failed = db.query(SummaryJob).filter(
                SummaryJob.status == 'failed'
            ).order_by(SummaryJob.created_at.desc()).first()
            
            if failed:
                print(f"   最近失败原因: {failed.error_message}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")

def check_topic_generation():
    """检查自动生成新话题功能"""
    print_section("5. 自动生成新话题功能")
    
    try:
        from models.database import SessionLocal
        from models.models import Topic
        from sqlalchemy import func
        
        db = SessionLocal()
        
        # 统计话题数
        total_topics = db.query(func.count(Topic.id)).scalar()
        active_topics = db.query(func.count(Topic.id)).filter(
            Topic.status == 'active'
        ).scalar()
        closed_topics = db.query(func.count(Topic.id)).filter(
            Topic.status == 'closed'
        ).scalar()
        
        print(f"总话题数: {total_topics}")
        print(f"活跃话题: {active_topics}")
        print(f"已关闭话题: {closed_topics}")
        
        # 获取最近创建的话题
        recent_topics = db.query(Topic).order_by(
            Topic.created_at.desc()
        ).limit(3).all()
        
        print()
        print("最近的话题：")
        for topic in recent_topics:
            print(f"  • {topic.title}")
            print(f"    状态: {topic.status} | "
                  f"创建时间: {topic.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if topic.topic_description:
                print(f"    描述: {topic.topic_description[:60]}...")
            print()
        
        # 检查是否有最近自动生成的话题（24小时内）
        recent_auto_topics = db.query(Topic).filter(
            Topic.created_at >= datetime.utcnow() - timedelta(days=1)
        ).order_by(Topic.created_at.desc()).all()
        
        if recent_auto_topics:
            print(f"✅ 最近 24 小时内创建了 {len(recent_auto_topics)} 个话题")
        else:
            print("⚠️  最近 24 小时内没有新话题")
            print("   提示：只有在话题关闭时才会自动生成新话题")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")

def test_api_connection():
    """测试 API 连接"""
    print_section("6. API 连接测试")
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key or api_key == "your_deepseek_api_key_here":
        print("⏭️  跳过（API Key 未配置）")
        return
    
    try:
        from services.llm_clients.deepseek_client import DeepSeekClient
        
        client = DeepSeekClient(
            api_key=api_key,
            api_url=os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
        )
        
        print("正在测试 API 连接...")
        
        test_prompt = """请评估以下发言的相关性（0-100分）：
主题：人工智能的未来
发言：我认为AI将改变世界

返回JSON格式：
{
  "relevance_score": 90,
  "evaluation_comment": "紧扣主题"
}"""
        
        result = client.evaluate_message_relevance(test_prompt)
        
        if result:
            print("✅ API 连接成功")
            print(f"   测试评分: {result.get('relevance_score')}")
            print(f"   测试评论: {result.get('evaluation_comment')}")
        else:
            print("❌ API 调用失败")
            print("   可能原因：")
            print("   - API Key 无效")
            print("   - 网络连接问题")
            print("   - API 配额用尽")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def main():
    """主函数"""
    print_header("DeepSeek 功能状态检查")
    
    # 1. 检查 API Key
    api_key_ok = check_api_key()
    
    # 2. 检查 Celery
    celery_ok = check_celery_status()
    
    # 3. 检查各项功能
    check_message_scoring()
    check_summary_generation()
    check_topic_generation()
    
    # 4. 测试 API 连接
    if api_key_ok:
        test_api_connection()
    
    # 总结
    print_header("检查完成")
    
    if not api_key_ok:
        print("⚠️  请先配置 DeepSeek API Key")
        print()
        print("配置步骤：")
        print("1. 访问 https://platform.deepseek.com/ 获取 API Key")
        print("2. 编辑 .env 文件，设置 DEEPSEEK_API_KEY=sk-xxx")
        print("3. 重启服务: pkill -f celery && python quick_start.py")
        print()
        print("详细说明请查看：DeepSeek_API配置指南.md")
    elif not celery_ok:
        print("⚠️  请启动 Celery Worker")
        print()
        print("启动命令：python quick_start.py")
    else:
        print("✅ 所有检查完成")
        print()
        print("如果某些功能显示无数据，可能是因为：")
        print("- 系统刚启动，还没有触发相关功能")
        print("- 需要发送更多消息来触发评分和总结")
        print("- 需要关闭话题来触发新话题生成")
    
    print()

if __name__ == "__main__":
    main()
