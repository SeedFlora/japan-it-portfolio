import hashlib

import pytest
from pydantic import ValidationError

from ai_ops.models import QueryRequest
from ai_ops.retrieval import Corpus, tokenize
from ai_ops.service import DEFAULT_CORPUS, OpsAssistant


@pytest.fixture
def corpus():
    return Corpus(DEFAULT_CORPUS)


def test_corpus_has_parallel_documents(corpus):
    assert len(corpus.documents) == 6
    assert len(corpus.chunks) == 30
    assert {d.language for d in corpus.list_documents()} == {"en", "ja"}


@pytest.mark.parametrize("query,language,expected", [
    ("When should we rollback a release?", "en", "release_en"),
    ("How are backup restore tests performed?", "en", "data_en"),
    ("重大障害のエスカレーションと復旧手順は？", "ja", "incident_ja"),
    ("バックアップ復元テストの頻度は？", "ja", "data_ja"),
])
def test_relevant_document_ranked_first(corpus, query, language, expected):
    result = corpus.search(QueryRequest(query=query, language=language))
    assert result.evidence[0].document_id == expected
    assert all(e.language == language for e in result.evidence)


def test_every_quote_matches_source_lines_and_hash(corpus):
    for chunk in corpus.chunks:
        document = corpus.read_document(chunk.document_id)
        lines = document.text.splitlines()
        assert chunk.text == "\n".join(lines[chunk.line_start - 1 : chunk.line_end])
        raw = (DEFAULT_CORPUS / (chunk.document_id + ".md")).read_bytes()
        assert chunk.sha256 == hashlib.sha256(raw).hexdigest() == document.sha256


def test_ranking_is_deterministic_and_limit_enforced(corpus):
    request = QueryRequest(query="rollback", limit=1)
    assert corpus.search(request) == corpus.search(request)
    assert len(corpus.search(request).evidence) == 1


def test_unicode_normalization():
    assert tokenize("ＲＯＬＬＢＡＣＫ") == tokenize("rollback")
    assert "障害" in tokenize("重大障害")


@pytest.mark.parametrize("value", ["", " ", "x", "!!!", "a" * 501, "backup\x00restore", "backups\nrestore"])
def test_invalid_questions_rejected(value):
    with pytest.raises(ValidationError):
        QueryRequest(query=value)


@pytest.mark.parametrize("values", [{"limit": 0}, {"limit": 6}, {"limit": "3"}, {"limit": True}, {"language": "de"}, {"extra": 1}])
def test_invalid_options_rejected(values):
    with pytest.raises(ValidationError):
        QueryRequest(query="rollback", **values)


def test_document_lookup_is_allowlisted(corpus):
    for identifier in ("../../secrets", "C:/Users/secret", "release_en.md", "unknown_en"):
        with pytest.raises(KeyError):
            corpus.read_document(identifier)


async def test_unsupported_question_abstains(corpus):
    answer = await OpsAssistant(corpus).answer(QueryRequest(query="What is the orbital period of Neptune?"))
    assert answer.status == "not_found"
    assert answer.evidence == []
    assert "No sufficiently matching evidence" in answer.answer


async def test_japanese_answer_and_abstention_are_localized(corpus):
    assistant = OpsAssistant(corpus)
    answer = await assistant.answer(QueryRequest(query="バックアップ復元テスト", language="ja"))
    assert answer.answer.startswith("関連する原文の抜粋")
    missing = await assistant.answer(QueryRequest(query="海王星の公転周期", language="ja"))
    assert missing.status == "not_found"
    assert "根拠が見つかりません" in missing.answer


async def test_important_negation_and_migration_exception_preserved(corpus):
    result = await OpsAssistant(corpus).answer(QueryRequest(query="rollback decision irreversible migration", language="en"))
    evidence = next(e for e in result.evidence if e.section == "Rollback decision")
    assert "not automatically safe" in evidence.quote
    assert "first consult the migration owner" in evidence.quote
    assert evidence.quote in result.answer
    # We present excerpts, not an invented yes/no conclusion about the user scenario.
    assert result.answer.startswith("Relevant source excerpts")


def test_bad_corpus_rejected(tmp_path):
    (tmp_path / "bad_en.md").write_text("no markdown title", encoding="utf-8")
    with pytest.raises(ValueError, match="title"):
        Corpus(tmp_path)


def test_empty_corpus_rejected(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        Corpus(tmp_path)

