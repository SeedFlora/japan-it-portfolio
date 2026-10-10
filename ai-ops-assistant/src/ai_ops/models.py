"""Shared contracts for REST and MCP. The same validation applies to both."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=3, ge=1, le=5)
    language: Literal["en", "ja", "all"] = "all"

    @field_validator("query")
    @classmethod
    def meaningful_query(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2 or not re.search(r"\w", value, re.UNICODE):
            raise ValueError("Provide a question with at least two meaningful characters.")
        if any(ord(char) < 32 for char in value):
            raise ValueError("Control characters are not accepted in a query.")
        return value


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    section: str
    language: Literal["en", "ja"]
    source_file: str
    line_start: int
    line_end: int
    document_sha256: str
    quote: str
    score: float
    query_coverage: float


class SearchResponse(BaseModel):
    query: str
    retrieval: Literal["bm25_words_cjk_ngrams"] = "bm25_words_cjk_ngrams"
    evidence: list[Citation]
    corpus_version: str


class AnswerResponse(SearchResponse):
    status: Literal["evidence_found", "not_found"]
    mode: Literal["offline_extractive", "ollama_quote_selection", "offline_fallback"]
    answer: str
    warnings: list[str] = Field(default_factory=list)


class DocumentInfo(BaseModel):
    document_id: str
    title: str
    language: Literal["en", "ja"]
    sha256: str
    chunks: int


class DocumentResponse(DocumentInfo):
    source_file: str
    text: str

