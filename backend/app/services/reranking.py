from __future__ import annotations

import re

from app.services.language import detect_language
from app.stores.base import SearchResult


class PolicyReranker:
    _STOPWORDS = {
        "the", "a", "an", "is", "are", "what", "how", "can", "to", "of", "for",
        "policy", "employee", "employees", "company", "bank", "please", "tell",
        "ما", "هي", "هو", "هل", "كيف", "في", "من", "إلى", "الى", "على", "عن",
        "سياسة", "الموظف", "الموظفين", "البنك",
    }

    @classmethod
    def _tokens(cls, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[\w\u0600-\u06FF]+", (text or "").lower())
            if len(token) > 1 and token not in cls._STOPWORDS
        }

    def rerank(self, query: str, results: list[SearchResult], top_k: int) -> list[SearchResult]:
        if not results:
            return []

        query_tokens = self._tokens(query)
        query_lang = detect_language(query)
        rescored: list[SearchResult] = []

        for result in results:
            body_tokens = self._tokens(result.chunk.text)
            title_tokens = self._tokens(result.chunk.title)
            overlap = len(query_tokens & body_tokens) / max(1, len(query_tokens))
            title_overlap = len(query_tokens & title_tokens) / max(1, len(query_tokens))
            language_match = 1.0 if result.chunk.language in {query_lang, "mixed"} else 0.0
            rank_score = (
                0.55 * result.score
                + 0.30 * overlap
                + 0.10 * title_overlap
                + 0.05 * language_match
            )
            rescored.append(
                SearchResult(
                    chunk=result.chunk,
                    score=result.score,
                    rerank_score=max(0.0, min(1.0, rank_score)),
                )
            )

        rescored.sort(key=lambda item: (item.rerank_score or 0.0, item.score), reverse=True)
        return rescored[:top_k]
