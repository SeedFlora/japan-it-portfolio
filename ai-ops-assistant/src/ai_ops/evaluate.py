"""Measure retrieval on an explicit, small synthetic EN/JA evaluation suite."""

import json
import sys
from pathlib import Path

from .models import QueryRequest
from .service import DEFAULT_CORPUS
from .retrieval import Corpus


def run_evaluation() -> dict:
    corpus = Corpus(DEFAULT_CORPUS)
    cases = json.loads((Path(__file__).parent / "evaluation" / "cases.json").read_text(encoding="utf-8"))
    rows = []
    document_top1 = section_top1 = section_top3 = abstained = 0
    reciprocal_rank = 0.0
    for case in cases:
        evidence = corpus.search(QueryRequest(query=case["query"], language=case["language"], limit=3)).evidence
        expected = case["expected_document"]
        expected_section = case["expected_section"]
        rank = next((i for i, e in enumerate(evidence, start=1)
                     if e.document_id == expected and e.section == expected_section), None)
        if expected is None:
            abstained += not evidence
        else:
            document_top1 += bool(evidence and evidence[0].document_id == expected)
            section_top1 += rank == 1
            section_top3 += rank is not None
            reciprocal_rank += 1 / rank if rank else 0
        rows.append({**case, "actual_top_document": evidence[0].document_id if evidence else None,
                     "actual_top_section": evidence[0].section if evidence else None,
                     "expected_section_rank": rank, "returned_count": len(evidence)})
    positive_count = sum(c["expected_document"] is not None for c in cases)
    negative_count = len(cases) - positive_count
    return {
        "scope": "Hand-authored synthetic fixture; same six demo documents; not a held-out or production benchmark",
        "retrieval": "bm25_words_cjk_ngrams", "corpus_version": corpus.version,
        "documents": len(corpus.documents), "chunks": len(corpus.chunks),
        "positive_cases": positive_count, "negative_cases": negative_count,
        "metrics": {"document_recall_at_1": round(document_top1 / positive_count, 5),
                    "section_recall_at_1": round(section_top1 / positive_count, 5),
                    "section_recall_at_3": round(section_top3 / positive_count, 5),
                    "section_mrr_at_3": round(reciprocal_rank / positive_count, 5),
                    "negative_abstention_rate": round(abstained / negative_count, 5)},
        "cases": rows,
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(run_evaluation(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
