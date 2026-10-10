# Warehouse DX / 倉庫DX

A bilingual warehouse operations portfolio built by Budi Juarto in October 2026. This is a newly created engineering demonstration using entirely synthetic products, locations and actors. It is not a client deployment or evidence of historical production work.

React + TypeScript present inventory, stock movements, replenishment approvals and the audit trail. A FastAPI API persists the workflow in SQLite. The application is useful evidence for internal systems, logistics DX and software engineering roles.

## What actually works

- English / Japanese interface and product labels, including translated error messages.
- Inventory search, low-stock filter, reorder alerts, per-location stock and CSV export.
- Receipts, dispatches and transfers; a dispatch or transfer cannot create negative stock.
- Operator request → manager approval or rejection → operator receipt. A request or approval alone never adds stock.
- Stock updates, movement records and audit entries commit in one transaction. Failed audit writes roll back stock and movement changes.
- Stable idempotency keys for movement retries and approved-request receipts. Replaying the same payload returns the existing movement; reusing a key with different data is rejected.
- SQLite `BEGIN IMMEDIATE` serializes competing writes before checking stock. State reads use one consistent database snapshot.
- Data survives a server restart. Synthetic data is seeded once in each new database.

## Run locally

Requirements: Python 3.11+, Node.js 20.19+ or 22.12+, and pnpm. The committed `pnpm-lock.yaml` pins the JavaScript dependency graph. `requirements-lock.txt` records the Python environment actually tested; `requirements.txt` is the supported top-level range.

From this `warehouse-dx` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
cd frontend
pnpm install --frozen-lockfile
pnpm build
cd ..
.\.venv\Scripts\python.exe -m uvicorn backend.app:create_app --factory --host 127.0.0.1 --port 8008
```

Open `http://127.0.0.1:8008`. The same origin serves the built frontend and API. OpenAPI documentation is at `/docs`. The database is created in ignored `data/warehouse.sqlite3`; set `WAREHOUSE_DB` to use a different path. On Linux/macOS use `.venv/bin/python` instead of the Windows Python path.

For frontend development, start the API as above and run `pnpm dev` in `frontend` in a second terminal. Vite runs on port 5188 and proxies `/api` to port 8008.

## Try the workflow

1. Open Replenishment. The synthetic `REQ-DEMO-001` request is awaiting approval.
2. Switch the demo role to Operations / manager and approve it.
3. Switch to Warehouse / operator and receive approved stock. Inventory and audit entries update together.
4. Dispatch more handheld scanners than are available at location A. The API rejects the operation and keeps inventory unchanged.
5. Switch to Japanese and explore the same screens and error messages. Export the inventory from Inventory.

The role picker intentionally simulates permissions using `X-Demo-Role`. It is **not authentication**. Anyone with API access can select a demo role. Keep the default loopback binding; the demo is not ready for an untrusted production network.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest backend/test_app.py -q
cd frontend
pnpm build
```

The HTTP integration tests use real SQLite transactions and temporary databases. They cover overselling, simultaneous dispatches, simultaneous identical retries, atomic transfer, forced audit-write rollback, role restrictions, approval/receipt state transitions, receipt idempotency, input validation, persistence across app restart, CSV and health.

`backend/smoke_http.py` starts a real Uvicorn process on a free loopback port, serves the built frontend, and exercises the API using HTTP against an isolated temporary database:

```powershell
.\.venv\Scripts\python.exe backend/smoke_http.py
```

The frontend was type-checked and bundled; it has not been visually verified in a browser in this run. Font imports are optional remote Google Fonts; local fallback fonts allow the application to function offline.

## Design and practical limits

- All IDs, stock and actor names are fictional. No CVs, contact details, identity documents or job-application information are included.
- SQLite is suitable for a small local demonstration. There is no production authentication, organization isolation, tamper-resistant audit storage, monitoring, backup automation or multi-region deployment.
- All quantities are integers. Reorder points apply to the product total, not an individual location. Products have different units; quantities should not be summed into one business KPI.
- The UI displays the latest 50 movements and audit entries and latest 100 requests. The total movement count includes all persisted movements. There is no server-side pagination.
- Movement and approved-receipt retries are idempotent. Creating a replenishment request is not idempotent: do not retry a request creation after an uncertain network result without refreshing and checking the list.
- Role and language selections are local UI state. The database persists operations, but the UI preference resets on page reload.
- The demo has no automatic reset endpoint. To get fresh synthetic data, choose a new `WAREHOUSE_DB` path while the server is stopped.

## 日本語

2026年10月に制作した架空データのポートフォリオです。実際の顧客導入や過去の実務経験を示すものではありません。

入庫・出庫・拠点間移動、補充申請・管理者承認・入庫、および監査ログを実装しています。在庫・履歴・監査ログは同一トランザクションで確定します。在庫不足、同時出庫、再送時の二重更新、監査ログ書き込み失敗時のロールバックをテストしています。

言語ボタンで英語と日本語を切り替えます。デモ用権限の選択はユーザー認証ではありません。本番運用には認証・権限管理・監視・バックアップなどを追加する必要があります。
