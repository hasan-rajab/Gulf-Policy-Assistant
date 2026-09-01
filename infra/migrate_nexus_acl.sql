-- NEXUS v2 migration for an existing enterprise_rag.policy_chunks table.
-- Replace PROJECT_ID before running.

ALTER TABLE `PROJECT_ID.enterprise_rag.policy_chunks`
ADD COLUMN IF NOT EXISTS visibility STRING;

ALTER TABLE `PROJECT_ID.enterprise_rag.policy_chunks`
ADD COLUMN IF NOT EXISTS allowed_roles ARRAY<STRING>;

ALTER TABLE `PROJECT_ID.enterprise_rag.policy_chunks`
ADD COLUMN IF NOT EXISTS allowed_departments ARRAY<STRING>;

UPDATE `PROJECT_ID.enterprise_rag.policy_chunks`
SET visibility = 'public'
WHERE visibility IS NULL;

CREATE OR REPLACE VECTOR INDEX policy_chunks_embedding_idx
ON `PROJECT_ID.enterprise_rag.policy_chunks`(embedding)
STORING(
  document_id,
  title,
  chunk_index,
  page,
  language,
  source_uri,
  visibility,
  allowed_roles,
  allowed_departments
)
OPTIONS(distance_type='COSINE', index_type='IVF');

CREATE TABLE IF NOT EXISTS `PROJECT_ID.enterprise_rag.audit_events` (
  event_id STRING NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  actor STRING NOT NULL,
  action STRING NOT NULL,
  resource STRING,
  outcome STRING NOT NULL,
  request_id STRING,
  details STRING,
  previous_hash STRING,
  event_hash STRING NOT NULL
)
PARTITION BY DATE(timestamp)
CLUSTER BY actor, action, outcome;
