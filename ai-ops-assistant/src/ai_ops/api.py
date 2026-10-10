"""Local FastAPI demo. No authentication: bind to loopback only."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .models import AnswerResponse, DocumentInfo, DocumentResponse, QueryRequest, SearchResponse
from .service import OpsAssistant


def create_app(assistant: OpsAssistant | None = None) -> FastAPI:
    assistant = assistant or OpsAssistant.from_environment()
    app = FastAPI(title="AI Operations Assistant — portfolio demo", version="0.1.0",
                  description="Fictional EN/JA operational corpus. Exact source excerpts, not operational decisions.")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def homepage() -> str:
        return (Path(__file__).parent / "web" / "index.html").read_text(encoding="utf-8")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "provider": assistant.provider,
                "corpus_version": assistant.corpus.version,
                "documents": len(assistant.corpus.documents), "chunks": len(assistant.corpus.chunks)}

    @app.get("/api/documents", response_model=list[DocumentInfo])
    def documents() -> list[DocumentInfo]:
        return assistant.corpus.list_documents()

    @app.get("/api/documents/{document_id}", response_model=DocumentResponse)
    def document(document_id: str) -> DocumentResponse:
        try:
            return assistant.corpus.read_document(document_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Document ID not in corpus") from exc

    @app.post("/api/search", response_model=SearchResponse)
    def search(request: QueryRequest) -> SearchResponse:
        return assistant.corpus.search(request)

    @app.post("/api/answer", response_model=AnswerResponse)
    async def answer(request: QueryRequest) -> AnswerResponse:
        return await assistant.answer(request)

    return app


app = create_app()

