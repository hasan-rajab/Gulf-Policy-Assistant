from app.services.chunking import chunk_text
from app.services.language import detect_language


def test_language_detection():
    assert detect_language("ما هي سياسة العمل عن بعد؟") == "ar"
    assert detect_language("What is the remote work policy?") == "en"


def test_chunking_preserves_content():
    text = "Paragraph one.\n\n" + ("سياسة العمل عن بعد. " * 100)
    chunks = chunk_text(text, chunk_size=250, overlap=30)
    assert len(chunks) > 1
    assert all(c.text for c in chunks)
