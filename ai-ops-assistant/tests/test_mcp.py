import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from ai_ops.mcp_server import create_server
from ai_ops.service import OpsAssistant


async def test_actual_sdk_tools_and_resources():
    async with Client(create_server(OpsAssistant())) as client:
        listed = await client.list_tools()
        assert {tool.name for tool in listed.tools} == {"search_documents", "answer_question", "read_document"}
        assert all(tool.annotations.read_only_hint for tool in listed.tools)
        result = await client.call_tool("answer_question", {"query": "backup restore", "language": "en", "limit": 2})
        assert result.is_error is False
        assert result.structured_content["mode"] == "offline_extractive"
        assert result.structured_content["evidence"][0]["document_id"] == "data_en"
        document = await client.call_tool("read_document", {"document_id": "data_en"})
        assert document.structured_content["text"].startswith("# Data quality")
        resources = await client.list_resources()
        assert any(str(r.uri) == "ops://catalog" for r in resources.resources)
        resource = await client.read_resource("ops://documents/data_en")
        assert "02:00 JST" in resource.contents[0].text


async def test_mcp_rejects_bad_inputs_without_side_effects():
    async with Client(create_server(OpsAssistant())) as client:
        for name, arguments in [
            ("search_documents", {"query": "  "}),
            ("search_documents", {"query": "backup", "limit": 0}),
            ("answer_question", {"query": "backup", "language": "xx"}),
            ("read_document", {"document_id": "../../private"}),
            ("does_not_exist", {}),
        ]:
            result = await client.call_tool(name, arguments)
            assert result.is_error is True
            assert result.structured_content is None


async def test_real_stdio_subprocess_protocol():
    parameters = StdioServerParameters(command=sys.executable, args=["-m", "ai_ops.mcp_server"])
    async with Client(parameters, read_timeout_seconds=15) as client:
        assert client.protocol_version
        result = await client.call_tool("search_documents", {"query": "重大障害 エスカレーション", "language": "ja", "limit": 1})
        assert result.is_error is False
        assert result.structured_content["evidence"][0]["document_id"] == "incident_ja"

