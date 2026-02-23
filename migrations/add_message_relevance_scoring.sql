-- Migration: Add message relevance scoring feature
-- Date: 2024-01-15
-- Description: Adds topic_description field and message_relevance_scores table

-- 1. Add topic_description column to topics table
ALTER TABLE topics ADD COLUMN IF NOT EXISTS topic_description TEXT;

-- 2. Create message_relevance_scores table
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
);

-- 3. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_message_scores_message ON message_relevance_scores(message_id);
CREATE INDEX IF NOT EXISTS idx_message_scores_topic ON message_relevance_scores(topic_id);
CREATE INDEX IF NOT EXISTS idx_message_scores_agent ON message_relevance_scores(agent_id, evaluated_at DESC);

-- 4. Add comment for documentation
COMMENT ON TABLE message_relevance_scores IS 'Stores relevance evaluation scores for messages';
COMMENT ON COLUMN message_relevance_scores.relevance_score IS 'Comprehensive score (0-100) evaluating topic relevance, content quality, and discussion advancement';
COMMENT ON COLUMN message_relevance_scores.evaluation_comment IS 'Brief evaluation comment from DeepSeek LLM';
