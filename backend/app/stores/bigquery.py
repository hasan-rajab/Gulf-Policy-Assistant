import json

from google.cloud import bigquery

from app.core.config import Settings
from app.stores.base import SearchResult, StoredChunk, VectorStore


class BigQueryVectorStore(VectorStore):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = bigquery.Client(project=settings.google_cloud_project, location=settings.bq_location)
        self.table = settings.bq_table_fqn

    def upsert(self, chunks: list[StoredChunk]) -> None:
        if not chunks:
            return
        # Prototype ingestion uses append-only chunk IDs. Re-ingesting the same
        # document uses deterministic IDs and a DELETE first to avoid duplicates.
        doc_ids = sorted({c.document_id for c in chunks})
        delete_sql = f"DELETE FROM `{self.table}` WHERE document_id IN UNNEST(@doc_ids)"
        delete_job = self.client.query(
            delete_sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ArrayQueryParameter("doc_ids", "STRING", doc_ids)]
            ),
        )
        delete_job.result()

        rows = [
            {
                "id": c.id,
                "document_id": c.document_id,
                "title": c.title,
                "text": c.text,
                "embedding": c.embedding,
                "chunk_index": c.chunk_index,
                "page": c.page,
                "language": c.language,
                "source_uri": c.source_uri,
                "metadata": json.dumps(c.metadata, ensure_ascii=False),
            }
            for c in chunks
        ]
        errors = self.client.insert_rows_json(self.table, rows)
        if errors:
            raise RuntimeError(f"BigQuery insert failed: {errors}")

    def search(self, query_embedding: list[float], top_k: int) -> list[SearchResult]:
        sql = f"""
        SELECT
          base.id, base.document_id, base.title, base.text, base.embedding,
          base.chunk_index, base.page, base.language, base.source_uri,
          base.metadata, distance
        FROM VECTOR_SEARCH(
          TABLE `{self.table}`,
          'embedding',
          (SELECT @query_embedding AS embedding),
          'embedding',
          top_k => @top_k,
          distance_type => 'COSINE'
        )
        ORDER BY distance ASC
        """
        params = [
            bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding),
            bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
        ]
        rows = self.client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params)).result()
        results: list[SearchResult] = []
        for row in rows:
            metadata = json.loads(row.metadata) if row.metadata else {}
            chunk = StoredChunk(
                id=row.id,
                document_id=row.document_id,
                title=row.title,
                text=row.text,
                embedding=list(row.embedding),
                chunk_index=row.chunk_index,
                page=row.page,
                language=row.language,
                source_uri=row.source_uri,
                metadata=metadata,
            )
            # COSINE distance: 0 means identical; convert to an intuitive 0..1 score.
            score = max(0.0, min(1.0, 1.0 - float(row.distance)))
            results.append(SearchResult(chunk=chunk, score=score))
        return results

    def list_documents(self) -> list[dict]:
        sql = f"""
        SELECT document_id, ANY_VALUE(title) title, COUNT(*) chunks,
               ANY_VALUE(source_uri) source_uri,
               IF(COUNT(DISTINCT language) > 1, 'mixed', ANY_VALUE(language)) language
        FROM `{self.table}`
        GROUP BY document_id
        ORDER BY title
        """
        return [dict(row.items()) for row in self.client.query(sql).result()]
