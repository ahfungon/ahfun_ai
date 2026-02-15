"""Direct test of Celery task execution."""
from models.database import SessionLocal
from models.models import Message, MessageRelevanceScore
from workers.tasks import evaluate_message_relevance

# Get a message
db = SessionLocal()
msg = db.query(Message).order_by(Message.created_at.desc()).first()

if msg:
    print(f'Testing with message: {msg.id[:8]}... from {msg.agent_id}')
    print(f'Content: {msg.content[:100]}...')
    
    # Call the task function directly (not async)
    print('\nCalling task function directly...')
    result = evaluate_message_relevance(
        message_id=msg.id,
        topic_id=msg.topic_id,
        agent_id=msg.agent_id,
        content=msg.content
    )
    
    print(f'Task completed: {result}')
    
    # Check if score was created
    score = db.query(MessageRelevanceScore).filter(
        MessageRelevanceScore.message_id == msg.id
    ).first()
    
    if score:
        print(f'\n✓ Score created:')
        print(f'  Score: {score.relevance_score}')
        print(f'  Comment: {score.evaluation_comment}')
    else:
        print('\n✗ No score found')
else:
    print('No messages found')

db.close()
