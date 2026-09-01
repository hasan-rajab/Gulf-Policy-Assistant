from __future__ import annotations

import json

from google.cloud import bigquery

from app.core.access import AccessContext
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
                "visibility": c.visibility,
                "allowed_roles": c.allowed_roles,
                "allowed_departments": c.allowed_departments,
            }
            for c in chunks
        ]
        errors = self.client.insert_rows_json(self.table, rows)
        if errors:
            raise RuntimeError(f"BigQuery insert failed: {errors}")

    @staticmethod
    def _access_parameters(access: AccessContext | None) -> list:
        access = access or AccessContext.create("internal-public-only")
        return [
            bigquery.ScalarQueryParameter("is_admin", "BOOL", access.is_admin),
            bigquery.ArrayQueryParameter("roles", "STRING", sorted(access.roles)),
            bigquery.ArrayQueryParameter("departments", "STRING", sorted(access.departments)),
        ]

    @staticmethod
    def _acl_predicate() -> str:
        return """
        (
          @is_admin
          OR COALESCE(visibility, 'public') = 'public'
          OR EXISTS (
            SELECT 1 FROM UNNEST(allowed_roles) role
            WHERE role IN UNNEST(@roles)
          )
          OR EXISTS (
            SELECT 1 FROM UNNEST(allowed_departments) department
            WHERE department IN UNNEST(@departments)
          )
        )
        """

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        access: AccessContext | None = None,
    ) -> list[SearchResult]:
        # ACL columns are stored in the vector index (see infra/bigquery.sql), so
        # the base-table WHERE clause can be evaluated as a pre-filter before ANN.
        sql = f"""
        SELECT
          base.id, base.document_id, base.title, base.text, base.embedding,
          base.chunk_index, base.page, base.language, base.source_uri,
          base.metadata, base.visibility, base.allowed_roles,
          base.allowed_departments, distance
        FROM VECTOR_SEARCH(
          (
            SELECT * FROM `{self.table}`
            WHERE {self._acl_predicate()}
          ),
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
            *self._access_parameters(access),
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
                visibility=row.visibility or "public",
                allowed_roles=list(row.allowed_roles or []),
                allowed_departments=list(row.allowed_departments or []),
            )
            score = max(0.0, min(1.0, 1.0 - float(row.distance)))
            results.append(SearchResult(chunk=chunk, score=score))
        return results

    def list_documents(self, access: AccessContext | None = None) -> list[dict]:
        sql = f"""
        SELECT document_id, ANY_VALUE(title) title, COUNT(*) chunks,
               ANY_VALUE(source_uri) source_uri,
               IF(COUNT(DISTINCT language) > 1, 'mixed', ANY_VALUE(language)) language,
               ANY_VALUE(visibility) visibility
        FROM `{self.table}`
        WHERE {self._acl_predicate()}
        GROUP BY document_id
        ORDER BY title
        """
        params = self._access_parameters(access)
        return [
            dict(row.items())
            for row in self.client.query(
                sql,
                job_config=bigquery.QueryJobConfig(query_parameters=params),
            ).result()
        ]
