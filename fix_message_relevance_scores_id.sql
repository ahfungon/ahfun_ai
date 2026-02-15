-- Fix message_relevance_scores table: change id from integer to varchar(36) for UUID
-- This migration is safe because the table should be empty

BEGIN;

-- Drop the existing primary key constraint
ALTER TABLE message_relevance_scores DROP CONSTRAINT message_relevance_scores_pkey;

-- Drop the sequence
DROP SEQUENCE IF EXISTS message_relevance_scores_id_seq CASCADE;

-- Change id column type to VARCHAR(36) for UUID
ALTER TABLE message_relevance_scores ALTER COLUMN id TYPE VARCHAR(36);

-- Re-add primary key constraint
ALTER TABLE message_relevance_scores ADD CONSTRAINT message_relevance_scores_pkey PRIMARY KEY (id);

COMMIT;
