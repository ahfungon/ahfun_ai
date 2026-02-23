-- Database Initialization Script
-- Generated: 2026-02-24
-- Database: dual_agent_chat

BEGIN;

-- Table: agents
CREATE TABLE IF NOT EXISTS agents (
id VARCHAR(36) NOT NULL,
name VARCHAR(100) NOT NULL,
auth_token_hash VARCHAR(128) NOT NULL,
created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
);


-- Table: alembic_version
CREATE TABLE IF NOT EXISTS alembic_version (
version_num VARCHAR(32) NOT NULL,
    PRIMARY KEY (version_num)
);


-- Table: message_relevance_scores
CREATE TABLE IF NOT EXISTS message_relevance_scores (
id VARCHAR(36) NOT NULL,
message_id VARCHAR(36) NOT NULL,
relevance_score DOUBLE PRECISION,
evaluation_comment TEXT,
evaluated_at TIMESTAMP  DEFAULT CURRENT_TIMESTAMP,
topic_id VARCHAR(36),
agent_id VARCHAR(36),
    PRIMARY KEY (id)
);

ALTER TABLE message_relevance_scores ADD CONSTRAINT fk_message_relevance_scores_topic FOREIGN KEY (topic_id) REFERENCES topics(id);
ALTER TABLE message_relevance_scores ADD CONSTRAINT message_relevance_scores_message_id_fkey FOREIGN KEY (message_id) REFERENCES messages(id);

-- Table: audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
id VARCHAR(36) NOT NULL,
operation_type VARCHAR(50) NOT NULL,
topic_id VARCHAR(36),
agent_id VARCHAR(36),
details TEXT,
created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
);


-- Table: messages
CREATE TABLE IF NOT EXISTS messages (
id VARCHAR(36) NOT NULL,
topic_id VARCHAR(36) NOT NULL,
agent_id VARCHAR(36) NOT NULL,
content TEXT NOT NULL,
actual_tokens INTEGER NOT NULL,
created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
);

ALTER TABLE messages ADD CONSTRAINT messages_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES topics(id);

-- Table: summary_history
CREATE TABLE IF NOT EXISTS summary_history (
id VARCHAR(36) NOT NULL,
topic_id VARCHAR(36) NOT NULL,
summary TEXT NOT NULL,
llm_suggestion VARCHAR(20) NOT NULL,
end_score DOUBLE PRECISION NOT NULL,
created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
);

ALTER TABLE summary_history ADD CONSTRAINT summary_history_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES topics(id);

-- Table: summary_jobs
CREATE TABLE IF NOT EXISTS summary_jobs (
id VARCHAR(36) NOT NULL,
topic_id VARCHAR(36) NOT NULL,
start_message_id VARCHAR(36),
end_message_id VARCHAR(36) NOT NULL,
status VARCHAR(20) NOT NULL,
retry_count INTEGER NOT NULL,
error_message TEXT,
created_at TIMESTAMP NOT NULL,
updated_at TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
);

ALTER TABLE summary_jobs ADD CONSTRAINT summary_jobs_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES topics(id);

-- Table: topics
CREATE TABLE IF NOT EXISTS topics (
id VARCHAR(36) NOT NULL,
title VARCHAR(255) NOT NULL,
status VARCHAR(20) NOT NULL,
summary TEXT,
llm_suggestion VARCHAR(20),
end_score DOUBLE PRECISION,
token_count_since_summary INTEGER NOT NULL,
summary_threshold INTEGER,
last_summarized_message_id VARCHAR(36),
pending_summary_job BOOLEAN NOT NULL,
agent_a_wants_close BOOLEAN NOT NULL,
agent_b_wants_close BOOLEAN NOT NULL,
closing_requested_by VARCHAR(36),
closing_requested_at TIMESTAMP,
created_at TIMESTAMP NOT NULL,
updated_at TIMESTAMP NOT NULL,
topic_description TEXT,
    PRIMARY KEY (id)
);


COMMIT;