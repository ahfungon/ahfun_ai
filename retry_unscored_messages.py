#!/usr/bin/env python3
"""
Retry scoring for unscored messages.

This script directly triggers the scoring tasks for messages that don't have scores yet.
"""
from sqlalchemy import create_engine, not_, exists
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from models.models import Message, MessageRelevanceScore
from workers.tasks import evaluate_message_relevance

def retry_unscored_messages(limit=50):
    """Retry scoring for unscored messages."""
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Find unscored messages
        unscored_messages = db.query(Message).filter(
            not_(exists().where(MessageRelevanceScore.message_id == Message.id))
        ).order_by(Message.created_at.desc()).limit(limit).all()
        
        if not unscored_messages:
            print("✅ No unscored messages found!")
            return
        
        print(f"Found {len(unscored_messages)} unscored messages")
        print(f"Triggering scoring tasks...\n")
        
        success_count = 0
        for msg in unscored_messages:
            try:
                # Trigger async scoring task
                task = evaluate_message_relevance.delay(
                    message_id=msg.id,
                    topic_id=msg.topic_id,
                    agent_id=msg.agent_id,
                    content=msg.content
                )
                print(f"✓ Queued: {msg.id[:8]}... (task: {task.id[:8]}...)")
                success_count += 1
            except Exception as e:
                print(f"✗ Failed to queue {msg.id[:8]}...: {e}")
        
        print(f"\n✅ Successfully queued {success_count}/{len(unscored_messages)} scoring tasks")
        print(f"\n💡 Tasks are being processed by Celery workers")
        print(f"   Check progress with: python3 check_recent_scoring.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    retry_unscored_messages()
