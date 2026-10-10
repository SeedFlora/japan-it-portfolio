"""Real HTTP smoke test. Uses a disposable DB and shuts down its own server."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def run():
    if not (ROOT / "frontend" / "dist" / "index.html").exists():
        raise SystemExit("Build frontend first: cd frontend && pnpm build")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="warehouse-dx-smoke-") as temporary:
        env = dict(os.environ, WAREHOUSE_DB=str(Path(temporary) / "smoke.sqlite3"))
        log_path = Path(temporary) / "server.log"
        with log_path.open("w+", encoding="utf-8") as log:
            server = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "backend.app:create_app", "--factory",
                 "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, env=env,
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            def http(path, body=None, role="operator"):
                request = Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                  headers={"Content-Type": "application/json", "X-Demo-Role": role})
                try:
                    with urlopen(request, timeout=5) as response:
                        return response.status, response.read()
                except HTTPError as error:
                    return error.code, error.read()

            def api(path, body=None, role="operator"):
                status, body_bytes = http(path, body, role)
                return status, json.loads(body_bytes)

            def quantity():
                return next(p for p in api("/api/state")[1]["products"] if p["id"] == 4)["balances"]["A"]

            try:
                deadline = time.monotonic() + 10
                while True:
                    try:
                        assert api("/api/health")[0] == 200
                        break
                    except (URLError, AssertionError):
                        if server.poll() is not None or time.monotonic() > deadline:
                            log.flush(); log.seek(0)
                            raise RuntimeError("Server startup failed: " + log.read())
                        time.sleep(.1)
                status, html = http("/")
                assert status == 200 and b'Warehouse DX' in html
                assets = re.findall(rb'(?:src|href)="(/assets/[^\"]+)"', html)
                assert len(assets) >= 2
                for asset in assets:
                    assert http(asset.decode())[0] == 200
                assert quantity() == 9
                movement = {"idempotency_key": "smoke-dispatch-001", "kind": "issue", "product_id": 4,
                            "quantity": 2, "from_location": "A", "reference": "SMOKE-ORDER-001"}
                first_status, first = api("/api/movements", movement)
                retry_status, retry = api("/api/movements", movement)
                assert first_status == retry_status == 201 and retry["replayed"]
                assert first["movement"]["id"] == retry["movement"]["id"] and quantity() == 7
                invalid = dict(movement, idempotency_key="smoke-insufficient", quantity=8)
                assert api("/api/movements", invalid)[0] == 409 and quantity() == 7
                status, request = api("/api/requests", {"product_id": 4, "quantity": 3, "location": "A", "note": "Synthetic replenishment"})
                assert status == 201
                route = "/api/requests/" + request["id"]
                receipt = {"idempotency_key": "smoke-receipt-001"}
                assert api(route + "/receive", receipt)[0] == 409
                assert api(route + "/decision", {"decision": "approve"}, "manager")[0] == 200
                assert api(route + "/receive", receipt)[0] == 200 and quantity() == 10
                assert api(route + "/receive", receipt)[1]["replayed"] and quantity() == 10
                assert api("/api/movements", dict(movement, idempotency_key="smoke-viewer-001"), "viewer")[0] == 403
                status, csv_bytes = http("/api/inventory.csv")
                assert status == 200 and b"OPS-004,Handheld scanners,A,10" in csv_bytes
                print(json.dumps({"status": "passed", "checks": ["real_uvicorn_http", "built_frontend_and_assets", "movement_retry", "negative_stock_rejection", "request_approval_receipt", "receipt_retry", "viewer_restriction", "csv_export"], "persistent_rows": "isolated synthetic temporary database"}))
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill(); server.wait(timeout=5)


if __name__ == "__main__":
    run()
