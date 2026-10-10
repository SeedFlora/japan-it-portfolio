"""Deterministic BM25 retrieval with exact, versioned, line-addressed evidence."""

import hashlib
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .models import Citation, DocumentInfo, DocumentResponse, QueryRequest, SearchResponse

STOP_WORDS = frozenset(
    "a an and are as at be by can did do does for from had has have how i if in is it its "
    "me my of on or our should that the their them then there these they this to us was "
    "we what when where which who why will with would you your please tell about".split()
)
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]+")
LATIN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    words = [word for word in LATIN.findall(normalized) if word not in STOP_WORDS]
    # No download or morphological dictionary required. CJK grams provide local
    # Japanese lexical matching, not semantic translation or language understanding.
    for run in CJK.findall(normalized):
        if len(run) == 1:
            words.append(run)
        for width in (2, 3):
            words.extend(run[i : i + width] for i in range(len(run) - width + 1))
    return words


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    title: str
    section: str
    language: str
    source_file: str
    line_start: int
    line_end: int
    sha256: str
    text: str


class Corpus:
    def __init__(self, directory: Path):
        self.documents: dict[str, DocumentResponse] = {}
        self.chunks: list[Chunk] = []
        for path in sorted(directory.glob("*.md")):
            if path.is_symlink():
                raise ValueError("Corpus files must be regular local documents.")
            if not re.fullmatch(r"[a-z0-9_-]+_(en|ja)", path.stem):
                raise ValueError("Corpus filenames must end in _en.md or _ja.md.")
            raw = path.read_bytes()
            if len(raw) > 100_000:
                raise ValueError("A document exceeds the curated-corpus size limit.")
            text = raw.decode("utf-8")
            lines = text.splitlines()
            if not lines or not lines[0].startswith("# "):
                raise ValueError("Each document needs a title on the first line.")
            document_id = path.stem
            title = lines[0][2:].strip()
            language = document_id.rsplit("_", 1)[1]
            digest = hashlib.sha256(raw).hexdigest()
            section = "Introduction"
            paragraph: list[str] = []
            start = 0
            initial_count = len(self.chunks)

            def flush(end: int) -> None:
                nonlocal paragraph
                if not paragraph:
                    return
                body = "\n".join(paragraph)
                if len(body) > 2400:
                    raise ValueError("Split long corpus paragraphs before indexing.")
                self.chunks.append(
                    Chunk(
                        f"{document_id}:L{start}-{end}", document_id, title, section,
                        language, f"corpus/{path.name}", start, end, digest, body,
                    )
                )
                paragraph = []

            for number, line in enumerate(lines[1:], start=2):
                if line.startswith("## "):
                    flush(number - 1)
                    section = line[3:].strip()
                elif not line.strip():
                    flush(number - 1)
                else:
                    if not paragraph:
                        start = number
                    paragraph.append(line)
            flush(len(lines))
            self.documents[document_id] = DocumentResponse(
                document_id=document_id, title=title, language=language, sha256=digest,
                chunks=len(self.chunks) - initial_count,
                source_file=f"corpus/{path.name}", text=text,
            )
        if not self.chunks:
            raise ValueError("The corpus is empty.")
        if len(self.chunks) > 1000:
            raise ValueError("This demonstration supports at most 1000 chunks.")
        self.version = hashlib.sha256(
            "\n".join(doc.sha256 for doc in self.documents.values()).encode()
        ).hexdigest()[:16]
        self.by_id = {chunk.chunk_id: chunk for chunk in self.chunks}
        self.term_counts = [Counter(tokenize(c.section + " " + c.text)) for c in self.chunks]
        self.lengths = [sum(count.values()) for count in self.term_counts]
        self.average_length = sum(self.lengths) / len(self.lengths)
        self.document_frequency: Counter[str] = Counter()
        for count in self.term_counts:
            self.document_frequency.update(count.keys())

    def list_documents(self) -> list[DocumentInfo]:
        return [DocumentInfo(**doc.model_dump(exclude={"source_file", "text"}))
                for doc in self.documents.values()]

    def read_document(self, document_id: str) -> DocumentResponse:
        # IDs are looked up in an allowlist; callers never supply filesystem paths.
        if document_id not in self.documents:
            raise KeyError("Document ID is not in the corpus.")
        return self.documents[document_id]

    def search(self, request: QueryRequest) -> SearchResponse:
        terms = set(tokenize(request.query))
        ranked: list[Citation] = []
        for chunk, count, length in zip(self.chunks, self.term_counts, self.lengths):
            if request.language != "all" and chunk.language != request.language:
                continue
            matched = terms & count.keys()
            coverage = len(matched) / len(terms) if terms else 0.0
            if not matched or coverage < 0.25:
                continue
            score = 0.0
            for term in matched:
                frequency = self.document_frequency[term]
                inverse = math.log(1 + (len(self.chunks) - frequency + 0.5) / (frequency + 0.5))
                tf = count[term]
                score += inverse * tf * 2.5 / (
                    tf + 1.5 * (0.25 + 0.75 * length / self.average_length)
                )
            if score < 0.4:
                continue
            ranked.append(Citation(
                chunk_id=chunk.chunk_id, document_id=chunk.document_id, title=chunk.title,
                section=chunk.section, language=chunk.language, source_file=chunk.source_file,
                line_start=chunk.line_start, line_end=chunk.line_end,
                document_sha256=chunk.sha256, quote=chunk.text,
                score=round(score, 5), query_coverage=round(coverage, 5),
            ))
        ranked.sort(key=lambda evidence: (-evidence.score, evidence.chunk_id))
        return SearchResponse(query=request.query, evidence=ranked[: request.limit],
                              corpus_version=self.version)

