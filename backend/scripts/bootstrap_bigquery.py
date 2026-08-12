from google.cloud import bigquery

from app.core.config import get_settings


def main():
    s = get_settings()
    if not s.google_cloud_project:
        raise SystemExit("Set GOOGLE_CLOUD_PROJECT first")
    client = bigquery.Client(project=s.google_cloud_project, location=s.bq_location)
    dataset_id = f"{s.google_cloud_project}.{s.bq_dataset}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = s.bq_location
    client.create_dataset(dataset, exists_ok=True)

    table = bigquery.Table(
        s.bq_table_fqn,
        schema=[
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("text", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("embedding", "FLOAT", mode="REPEATED"),
            bigquery.SchemaField("chunk_index", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("page", "INTEGER"),
            bigquery.SchemaField("language", "STRING"),
            bigquery.SchemaField("source_uri", "STRING"),
            bigquery.SchemaField("metadata", "STRING"),
        ],
    )
    client.create_table(table, exists_ok=True)
    print(f"Ready: {s.bq_table_fqn}")
    print("Optional for larger corpora: create a COSINE vector index using infra/bigquery.sql")


if __name__ == "__main__":
    main()
