"""Reproducible demo with actual retrieval and actual SDK stdio calls."""

import asyncio
import json
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from .models import QueryRequest
from .service import OpsAssistant


async def run_demo() -> dict:
    assistant = OpsAssistant(provider="offline")
    questions = [
        ("When should we rollback a release?", "en"),
        ("重大障害のエスカレーションと復旧手順は？", "ja"),
        ("How are backup restore tests performed?", "en"),
        ("What is the orbital period of Neptune?", "all"),
    ]
    answers = [(await assistant.answer(QueryRequest(query=q, language=lang))).model_dump()
               for q, lang in questions]
    parameters = StdioServerParameters(command=sys.executable, args=["-m", "ai_ops.mcp_server"])
    async with Client(parameters) as client:
        tools = await client.list_tools()
        result = await client.call_tool("answer_question", {
            "query": "When should we rollback a release?", "language": "en", "limit": 3,
        })
        if result.is_error:
            raise RuntimeError("MCP demo tool call failed.")
        mcp_result = {"protocol_version": client.protocol_version,
                      "tools": [tool.name for tool in tools.tools],
                      "answer": result.structured_content}
    return {"demo_data": "Fictional operational policies; newly built portfolio project",
            "offline_answers": answers, "mcp_stdio": mcp_result}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(asyncio.run(run_demo()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

