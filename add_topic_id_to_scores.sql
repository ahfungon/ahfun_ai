-- 为 message_relevance_scores 表添加 topic_id 列

-- 添加列（允许NULL，因为可能有旧数据）
ALTER TABLE message_relevance_scores 
ADD COLUMN IF NOT EXISTS topic_id VARCHAR(36);

-- 从 messages 表填充 topic_id
UPDATE message_relevance_scores mrs
SET topic_id = m.topic_id
FROM messages m
WHERE mrs.message_id = m.id
AND mrs.topic_id IS NULL;

-- 设置为 NOT NULL（如果所有数据都已填充）
-- ALTER TABLE message_relevance_scores 
-- ALTER COLUMN topic_id SET NOT NULL;

-- 添加外键约束
ALTER TABLE message_relevance_scores
ADD CONSTRAINT IF NOT EXISTS fk_message_relevance_scores_topic
FOREIGN KEY (topic_id) REFERENCES topics(id);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_message_relevance_scores_topic_id 
ON message_relevance_scores(topic_id);
