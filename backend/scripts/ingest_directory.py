import sys
from pathlib import Path

from app.dependencies import get_ingestion_service


def main(directory: str):
    ingestor = get_ingestion_service()
    path = Path(directory)
    if not path.exists():
        raise SystemExit(f"Directory not found: {path}")
    for file in sorted(path.iterdir()):
        if file.suffix.lower() not in {".pdf", ".docx", ".txt", ".md"}:
            continue
        result = ingestor.ingest_bytes(file.name, file.read_bytes(), source_uri=f"approved://policies/{file.name}")
        print(file.name, result)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../sample_data")
