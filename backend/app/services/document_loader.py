from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


@dataclass
class PageText:
    page: int | None
    text: str


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def load_document(filename: str, data: bytes) -> list[PageText]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")

    if suffix == ".pdf":
        reader = PdfReader(BytesIO(data))
        return [PageText(page=i + 1, text=page.extract_text() or "") for i, page in enumerate(reader.pages)]

    if suffix == ".docx":
        doc = Document(BytesIO(data))
        text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return [PageText(page=None, text=text)]

    return [PageText(page=None, text=data.decode("utf-8", errors="replace"))]
