# Japan IT Portfolio — Budi Juarto

Two runnable, AI-assisted personal portfolio projects created in October 2026. They demonstrate software and data engineering for bilingual operations teams using fictional documents and synthetic warehouse records.

These are portfolio demonstrations, not previous client deliveries or production deployments. A new portfolio project does not imply years of professional experience with every component in its stack.

| Project | What to try | Engineering focus |
| --- | --- | --- |
| [AI Operations Assistant](ai-ops-assistant/) | Ask an English or Japanese operations question, inspect its evidence, or call its MCP tools | Python, FastAPI, bilingual retrieval, citations, refusal behaviour, evaluation, official MCP SDK, optional local LLM quote selection |
| [Warehouse DX](warehouse-dx/) | Receive, issue and transfer stock; approve a replenishment request; inspect the audit trail | React, TypeScript, FastAPI, SQLite transactions, idempotency, approval workflows, role checks, CSV exports |

## Run and review

Each project has its own setup instructions, tests and limitations. Start with the linked project README files; neither project needs a paid service for its default demo.

- AI assistant: Python 3.11+, a deterministic offline retrieval mode and an optional Ollama adapter. The same document service is available through REST and MCP.
- Warehouse: Python 3.11+ and Node.js 22 with pnpm. The React interface supports English and Japanese; the backend persists synthetic data locally.

The repository CI checks the Python suites, the warehouse TypeScript build and the assistant evaluation. Test output is a reproducible verification of this demo, not a claim of production reliability or measured business impact.

Local verification on 10 October 2026: **48 assistant tests and 22 warehouse tests passed**. The warehouse frontend type check and production build passed; a real Uvicorn HTTP smoke test exercised the built frontend and stock/approval workflow. The assistant also ran successfully as a packaged Linux container, including its real MCP stdio client. Recorded evidence is available in [assistant evidence](ai-ops-assistant/evidence/) and [warehouse evidence](warehouse-dx/evidence/verification.json). Browser layout was not visually verified in this run.

## Scope and limitations

The assistant searches a small, fictional runbook corpus. Its offline answer mode returns evidence excerpts, not LLM-generated prose. It can refuse when evidence is missing; it should not be used to make real operational decisions without review.

The warehouse uses a local SQLite database and explicit demo roles. It is intended for local evaluation, not an authenticated multi-tenant deployment. Its project README explains the difference between its role checks and production authentication.

## 日本語

2026年10月に作成した、AI支援による個人ポートフォリオです。架空の運用文書と合成の在庫データを用い、英語・日本語に対応する2つのアプリケーションを実装しています。顧客への納品実績や本番運用実績ではありません。

- **AI運用アシスタント**：根拠と出典を確認できる文書検索、回答の拒否、REST API、公式MCP SDK、評価ケース。
- **倉庫DX**：入出庫・移動、補充申請と承認、監査ログ、トランザクション、冪等性、英日UI。

動作方法・検証方法・制約は、各プロジェクトのREADMEをご覧ください。

## Professional profile

[Portfolio](https://budijuarto.com) · [LinkedIn](https://www.linkedin.com/in/budijuarto/) · [GitHub](https://github.com/SeedFlora)

Budi Juarto — based in Bandung, Indonesia; master's degree in Computer Science; JLPT N2. Seeking IT, AI/data engineering and technical project roles in Japan, with relocation availability around April 2027.
