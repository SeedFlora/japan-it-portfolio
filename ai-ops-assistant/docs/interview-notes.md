# Explain the implementation

This is a newly created portfolio project. Demonstrate it from the repository; do not describe it as historical client or employer delivery.

## A short demo

1. Start the API and ask **When should we rollback a release?** Show the complete paragraph, source lines and the irreversible-migration exception. Explain that the relevant section appears third for this general lexical query; ranking alone does not establish relevance.
2. Ask **重大障害のエスカレーションと復旧手順は？** with Japanese sources. Open the source document and compare its exact wording with the result.
3. Ask **What is the orbital period of Neptune?** and show the no-evidence response.
4. Run `python -m ai_ops.demo` to make a real MCP stdio connection. Point to the negotiated protocol version and the returned structured evidence.
5. Run `python -m pytest -q` and `python -m ai_ops.evaluate`. Explain the synthetic fixture scope and the difference between section Recall@1 and Recall@3.

## Why the design is limited deliberately

**Why BM25?** It provides a reproducible local baseline without downloading an embedding model. It cannot understand paraphrases or translate between languages. A multilingual embedding experiment would need a separate relevance evaluation.

**Why does the optional model return full paragraphs?** A substring can omit negation or a safety condition. The validator accepts only the original complete paragraph identified by a retrieved chunk ID. Grounding limits unsupported output, but cannot prove that a quoted paragraph answers a question.

**What does MCP add?** An actual host can discover typed read-only tools and resource URIs. REST and MCP share the same retrieval and validation service, reducing inconsistent behavior between interfaces.

**What happens on failure?** Input errors are rejected. Unknown document IDs cannot read arbitrary local files. A missing, invalid or misleading Ollama response falls back to original retrieved source excerpts. No retrieval result means no model call.

**What would be needed for production?** Authentication, document-level authorization, request limits, observability, corpus maintenance, more diverse evaluation and review of deployment controls. The current local demo does not supply those features.

## Accurate CV wording

English: “Built a bilingual Python/FastAPI portfolio assistant with BM25 document retrieval, line-level citations, optional local Ollama evidence selection, and official MCP tools; added automated tests and a reproducible synthetic evaluation.”

Japanese: 「日英の文書を検索するPython/FastAPIのポートフォリオを実装。BM25検索、行番号付き引用、任意のローカルOllama連携、公式MCPツールを組み合わせ、自動テストと再現可能な小規模評価を追加。」

Do not claim vector search, fine-tuning, a production rollout, years of MCP experience, or savings that this project has not established.
