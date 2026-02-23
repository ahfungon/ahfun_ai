"""Run database migration for message relevance scoring."""
import sys
from sqlalchemy import text
from models.database import engine

def run_migration():
    """Execute the migration SQL file."""
    try:
        # Execute migration statements in order
        with engine.connect() as conn:
            # 1. Add topic_description column
            print("1. Adding topic_description column...")
            conn.execute(text("ALTER TABLE topics ADD COLUMN IF NOT EXISTS topic_description TEXT"))
            conn.commit()
            
            # 2. Create message_relevance_scores table
            print("2. Creating message_relevance_scores table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS message_relevance_scores (
                    id VARCHAR(36) PRIMARY KEY,
                    message_id VARCHAR(36) NOT NULL UNIQUE,
                    topic_id VARCHAR(36) NOT NULL,
                    agent_id VARCHAR(36) NOT NULL,
                    relevance_score FLOAT NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 100),
                    evaluation_comment TEXT,
                    evaluated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
                    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
                )
            """))
            conn.commit()
            
            # 3. Create indexes
            print("3. Creating indexes...")
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_message_scores_message ON message_relevance_scores(message_id)"))
            conn.commit()
            
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_message_scores_topic ON message_relevance_scores(topic_id)"))
            conn.commit()
            
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_message_scores_agent ON message_relevance_scores(agent_id, evaluated_at DESC)"))
            conn.commit()
        
        print("\n✅ Migration executed successfully!")
        print("Added:")
        print("  - topic_description column to topics table")
        print("  - message_relevance_scores table")
        print("  - Indexes for performance")
        return 0
    
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_migration())
