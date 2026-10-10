import json

import httpx
import pytest

from ai_ops.models import QueryRequest
from ai_ops.service import OpsAssistant


def selector_transport(change=None):
    def handle(request: httpx.Request):
        assert str(request.url) == "http://127.0.0.1:11434/api/chat"
        payload = json.loads(request.content)
        assert payload["stream"] is False
        assert payload["format"]["type"] == "object"
        context = json.loads(payload["messages"][1]["content"])
        source = context["evidence"][0]
        selection = {"chunk_id": source["chunk_id"], "quote": source["text"]}
        if change:
            change(selection)
        return httpx.Response(200, json={"message": {"content": json.dumps({"selections": [selection]})}})
    return httpx.MockTransport(handle)


async def test_valid_model_quote_selection():
    assistant = OpsAssistant(provider="ollama", model="test-fixture", transport=selector_transport())
    result = await assistant.answer(QueryRequest(query="rollback decision", language="en"))
    assert result.mode == "ollama_quote_selection"
    assert len(result.evidence) == 1
    assert not result.warnings


@pytest.mark.parametrize("change", [
    lambda selection: selection.update(quote="Every deployment is guaranteed safe without checking."),
    lambda selection: selection.update(chunk_id="invented_en:L1-3"),
    lambda selection: selection.update(quote=selection["quote"].replace("not automatically safe", "automatically safe")),
    lambda selection: selection.update(quote=selection["quote"][:50]),
])
async def test_fabricated_or_truncated_quotes_rejected(change):
    assistant = OpsAssistant(provider="ollama", model="test-fixture", transport=selector_transport(change))
    result = await assistant.answer(QueryRequest(query="rollback decision irreversible migration", language="en"))
    assert result.mode == "offline_fallback"
    assert result.warnings
    assert "not automatically safe" in result.answer
    assert "Every deployment is guaranteed safe" not in result.answer


async def test_ollama_connection_failure_falls_back():
    def fail(request):
        raise httpx.ConnectError("fixture: unavailable", request=request)
    assistant = OpsAssistant(provider="ollama", model="test-fixture", transport=httpx.MockTransport(fail))
    result = await assistant.answer(QueryRequest(query="backup restore", language="en"))
    assert result.mode == "offline_fallback"
    assert result.evidence


async def test_no_network_when_no_evidence():
    def fail(_):
        pytest.fail("The LLM must not be called without source evidence.")
    assistant = OpsAssistant(provider="ollama", model="test-fixture", transport=httpx.MockTransport(fail))
    result = await assistant.answer(QueryRequest(query="Neptune orbital period"))
    assert result.status == "not_found"


@pytest.mark.parametrize("url", ["https://example.com", "http://example.com", "http://127.0.0.1@evil.test", "http://localhost/private", "http://localhost?token=secret"])
def test_model_server_must_be_plain_loopback(url):
    with pytest.raises(ValueError):
        OpsAssistant(provider="ollama", ollama_url=url, model="fixture")


def test_ollama_needs_explicit_installed_model():
    with pytest.raises(ValueError):
        OpsAssistant(provider="ollama")

