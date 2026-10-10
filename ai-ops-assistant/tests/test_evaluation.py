from ai_ops.evaluate import run_evaluation


def test_explicit_synthetic_retrieval_suite():
    result = run_evaluation()
    assert result["positive_cases"] == 20
    assert result["negative_cases"] == 6
    # Section-level relevance is stricter than retrieving any paragraph from a
    # matching document. Thresholds are regression floors, not production claims.
    assert result["metrics"]["document_recall_at_1"] >= 0.9
    assert result["metrics"]["section_recall_at_3"] >= 0.85
    assert result["metrics"]["negative_abstention_rate"] == 1.0
