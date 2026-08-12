import re

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
LATIN_RE = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> str:
    ar = len(ARABIC_RE.findall(text))
    en = len(LATIN_RE.findall(text))
    if ar and en and min(ar, en) / max(ar, en) > 0.2:
        return "mixed"
    if ar > en:
        return "ar"
    return "en"
