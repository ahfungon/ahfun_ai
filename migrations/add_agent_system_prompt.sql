-- Add system_prompt column to agents table
-- This allows configuring agent personality and speaking style

ALTER TABLE agents 
ADD COLUMN IF NOT EXISTS system_prompt TEXT;

COMMENT ON COLUMN agents.system_prompt IS 'System prompt for agent personality and speaking style';
