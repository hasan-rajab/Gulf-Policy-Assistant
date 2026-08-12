from dataclasses import dataclass
import re

from app.services.language import detect_language


@dataclass
class Chunk:
    text: str
    page: int | None
    chunk_index: int
    language: str


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1400, overlap: int = 220, page: int | None = None) -> list[Chunk]:
    text = clean_text(text)
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{para}".strip()
        else:
            # hard split a single very long paragraph
            start = 0
            while start < len(para):
                end = min(start + chunk_size, len(para))
                chunks.append(para[start:end].strip())
                if end == len(para):
                    current = ""
                    break
                start = max(end - overlap, start + 1)

    if current:
        chunks.append(current)

    return [
        Chunk(text=c, page=page, chunk_index=i, language=detect_language(c))
        for i, c in enumerate(chunks)
        if c
    ]
