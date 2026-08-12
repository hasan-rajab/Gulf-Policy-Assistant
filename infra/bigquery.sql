-- Replace PROJECT_ID before running.
CREATE SCHEMA IF NOT EXISTS `PROJECT_ID.enterprise_rag` OPTIONS(location="US");

CREATE TABLE IF NOT EXISTS `PROJECT_ID.enterprise_rag.policy_chunks` (
  id STRING NOT NULL,
  document_id STRING NOT NULL,
  title STRING NOT NULL,
  text STRING NOT NULL,
  embedding ARRAY<FLOAT64> NOT NULL,
  chunk_index INT64 NOT NULL,
  page INT64,
  language STRING,
  source_uri STRING,
  metadata STRING
);

-- Vector indexes are most useful when the corpus is large enough to justify ANN.
-- Run after data is loaded; index population is asynchronous.
CREATE OR REPLACE VECTOR INDEX policy_chunks_embedding_idx
ON `PROJECT_ID.enterprise_rag.policy_chunks`(embedding)
STORING(document_id, title, chunk_index, page, language, source_uri)
OPTIONS(distance_type='COSINE', index_type='IVF');
