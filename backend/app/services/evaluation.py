import re

from app.services.language import detect_language
from app.services.rag import RAGService


class EvaluationService:
    def __init__(self, rag: RAGService):
        self.rag = rag

    def run(self, cases: list[dict], owner: str) -> dict:
        case_results = []
        latencies = []
        retrieval_hits = language_matches = grounding_decisions = 0
        citation_successes = 0
        grounded_case_count = 0
        keyword_scores = []

        for case in cases:
            response = self.rag.answer(case["query"], None, owner, case.get("top_k"))
            expected_grounded = case.get("expect_grounded", True)
            grounding_ok = response.grounded == expected_grounded
            grounding_decisions += int(grounding_ok)

            expected_docs = {d.lower() for d in case.get("expected_source_titles", [])}
            returned_docs = {s.title.lower() for s in response.sources}
            if expected_grounded:
                retrieval_hit = bool(expected_docs & returned_docs) if expected_docs else bool(response.sources)
                grounded_case_count += 1
                has_citation = bool(re.search(r"\[S\d+\]", response.answer))
                citation_successes += int(has_citation)
            else:
                # Correct behavior for unsupported questions is to retrieve no
                # sufficiently relevant approved context and cite nothing.
                retrieval_hit = not response.grounded
                has_citation = not bool(re.search(r"\[S\d+\]", response.answer))
            retrieval_hits += int(retrieval_hit)

            expected_lang = case.get("language") or detect_language(case["query"])
            language_match = response.language == expected_lang or expected_lang == "mixed"
            language_matches += int(language_match)

            keywords = [k.lower() for k in case.get("required_keywords", [])]
            answer_l = response.answer.lower()
            coverage = sum(1 for k in keywords if k in answer_l) / len(keywords) if keywords else 1.0
            keyword_scores.append(coverage)
            latencies.append(response.latency_ms)

            case_results.append(
                {
                    "id": case.get("id"),
                    "query": case["query"],
                    "expected_grounded": expected_grounded,
                    "grounding_decision_correct": grounding_ok,
                    "retrieval_hit": retrieval_hit,
                    "citation_behavior_correct": has_citation,
                    "language_match": language_match,
                    "keyword_coverage": round(coverage, 3),
                    "latency_ms": response.latency_ms,
                    "returned_sources": [s.title for s in response.sources],
                    "answer": response.answer,
                }
            )

        n = len(cases) or 1
        return {
            "total_cases": len(cases),
            "retrieval_hit_at_k": retrieval_hits / n,
            "citation_rate": citation_successes / grounded_case_count if grounded_case_count else 1.0,
            "grounding_decision_accuracy": grounding_decisions / n,
            "language_match_rate": language_matches / n,
            "grounded_keyword_coverage": sum(keyword_scores) / n,
            "avg_latency_ms": sum(latencies) / n if latencies else 0.0,
            "cases": case_results,
        }
