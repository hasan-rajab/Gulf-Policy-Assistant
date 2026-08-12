from abc import ABC, abstractmethod
import hashlib
import math
import re
import unicodedata

from app.core.config import Settings


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[tuple[str, str]]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Credential-free deterministic retrieval for the customer demo.

    This is intentionally *not* presented as a replacement for Gemini
    embeddings. It adds a few bilingual banking-policy concept aliases so the
    bundled demo remains deterministic and meaningful without cloud credentials.
    Production mode uses Gemini embeddings instead.
    """

    _CONCEPTS: tuple[tuple[tuple[str, ...], str], ...] = (
        (("remote work", "work from home", "working from home", "عن بعد", "العمل عن بعد", "العمل عن بُعد"), "concept_remote_work"),
        (("approval", "approve", "approved", "manager", "line manager", "موافقة", "الموافقة", "المدير", "اعتماد"), "concept_approval"),
        (("bahrain", "outside bahrain", "another country", "abroad", "البحرين", "خارج البحرين", "دولة أخرى", "دولة اخرى"), "concept_work_location"),
        (("customer data", "customer information", "confidential", "restricted", "classification", "بيانات العملاء", "معلومات العملاء", "سرية", "سري", "مقيدة", "تصنيف المعلومات"), "concept_information_classification"),
        (("personal laptop", "personal device", "personal devices", "personal email", "unapproved storage", "جهاز شخصي", "أجهزة شخصية", "اجهزة شخصية", "بريد شخصي", "تخزين غير معتمد"), "concept_device_security"),
        (("annual leave", "planned leave", "leave request", "إجازة", "الاجازة", "الإجازة", "إجازة سنوية", "اجازة سنوية"), "concept_leave"),
        (("attendance", "absence", "الحضور", "الغياب"), "concept_attendance"),
        (("vpn", "secure access", "information security", "أمن المعلومات", "امن المعلومات", "وصول آمن", "الوصول الآمن"), "concept_security"),
        (("cybersecurity incident", "security incident", "suspected cybersecurity incident", "incident reporting", "security service desk", "حادث سيبراني", "الحادث السيبراني", "الإبلاغ عن الحوادث", "مكتب خدمات الأمن"), "concept_cybersecurity_incident"),
        (("30 minutes", "within 30 minutes", "thirty minutes", "30 دقيقة", "خلال 30 دقيقة"), "concept_cybersecurity_reporting_window"),
    )

    _STOPWORDS = {
        "the", "a", "an", "is", "are", "what", "how", "can", "i", "to", "of", "for",
        "policy", "employee", "employees", "company", "bank",
        "ما", "هي", "هو", "هل", "كيف", "في", "من", "إلى", "الى", "على", "عن",
        "سياسة", "الموظف", "الموظفين", "البنك",
    }

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions

    @staticmethod
    def _normalize(text: str) -> str:
        text = unicodedata.normalize("NFKC", text).lower()
        # Normalize common Arabic variants without transliteration.
        text = re.sub(r"[إأآا]", "ا", text)
        text = text.replace("ى", "ي").replace("ة", "ه")
        text = re.sub(r"[ًٌٍَُِّْـ]", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def _features(self, text: str) -> list[str]:
        normalized = self._normalize(text)
        words = [
            w for w in re.findall(r"[\w\u0600-\u06ff]+", normalized, flags=re.UNICODE)
            if len(w) > 1 and w not in self._STOPWORDS
        ]
        features = words[:]

        # Character n-grams retain useful Arabic/English morphology while the
        # concept aliases create a small bilingual bridge for this fixed demo.
        compact = re.sub(r"\s+", " ", normalized)
        features.extend(compact[i : i + 4] for i in range(max(0, len(compact) - 3)))

        for phrases, concept in self._CONCEPTS:
            normalized_phrases = [self._normalize(p) for p in phrases]
            hits = sum(1 for p in normalized_phrases if p in normalized)
            if hits:
                features.extend([concept] * (10 + 3 * min(hits, 4)))
        return features

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        for feature in self._features(text):
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def _title_aliases(self, title: str) -> str:
        title_l = title.lower()
        if "remote work" in title_l:
            return "remote work العمل عن بعد manager approval موافقة المدير Bahrain البحرين VPN"
        if "information classification" in title_l:
            return "information classification confidential customer data تصنيف المعلومات بيانات العملاء سرية أمن المعلومات"
        if "leave and attendance" in title_l:
            return "annual leave attendance manager approval إجازة سنوية الحضور موافقة المدير"
        return ""

    def embed_documents(self, texts: list[tuple[str, str]]) -> list[list[float]]:
        return [self._embed(f"{title}\n{self._title_aliases(title)}\n{text}") for title, text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: Settings):
        if not settings.google_cloud_project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required for Gemini embeddings")
        from google import genai
        from google.genai import types

        self.settings = settings
        self._types = types
        self.client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )

    def _embed_single(self, content: str) -> list[float]:
        result = self.client.models.embed_content(
            model=self.settings.embedding_model,
            contents=content,
            config=self._types.EmbedContentConfig(
                output_dimensionality=self.settings.embedding_dimensions,
            ),
        )
        if not result.embeddings:
            raise RuntimeError("Embedding API returned no embedding")
        return list(result.embeddings[0].values)

    def embed_documents(self, texts: list[tuple[str, str]]) -> list[list[float]]:
        # Gemini Embedding 2 uses prompt-side task instructions for asymmetric retrieval.
        return [
            self._embed_single(f"title: {title or 'none'} | text: {text}")
            for title, text in texts
        ]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_single(f"task: question answering | query: {text}")
