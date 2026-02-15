#!/usr/bin/env python3
"""手动测试评分功能"""

import sys
from models.database import SessionLocal
from models.models import Message, Topic
from services.message_scoring_service import MessageScoringService

def main():
    db = SessionLocal()
    try:
        # 获取最新的消息
        messages = db.query(Message).order_by(Message.id.desc()).limit(5).all()
        
        if not messages:
            print("❌ 没有找到消息")
            return 1
        
        print(f"✓ 找到 {len(messages)} 条消息")
        
        # 创建评分服务
        scoring_service = MessageScoringService(db)
        
        # 对每条消息进行评分
        for msg in messages:
            print(f"\n评分消息: {msg.id}")
            print(f"  内容: {msg.content[:50]}...")
            
            try:
                score = scoring_service.evaluate_message(
                    message_id=msg.id,
                    topic_id=msg.topic_id,
                    agent_id=msg.agent_id,
                    content=msg.content
                )
                
                if score:
                    print(f"  ✓ 评分成功: {score.relevance_score:.1f}/100")
                    print(f"  评论: {score.evaluation_comment}")
                else:
                    print(f"  ⚠ 评分失败（返回 None）")
                    
            except Exception as e:
                print(f"  ❌ 评分出错: {e}")
                import traceback
                traceback.print_exc()
        
        return 0
        
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
