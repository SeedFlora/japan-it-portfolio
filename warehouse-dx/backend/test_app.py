"""HTTP integration tests using real SQLite transactions and temporary databases."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from backend.app import connect, create_app

OPERATOR={"X-Demo-Role":"operator"}
MANAGER={"X-Demo-Role":"manager"}


@pytest.fixture
def api(tmp_path):
    app=create_app(tmp_path/"test.sqlite3")
    with TestClient(app) as client:
        yield client,app.state.database


def payload(key="test-move-001",**changes):
    value={"idempotency_key":key,"kind":"issue","product_id":4,"quantity":1,"from_location":"A","reference":"TEST-ORDER-001"}
    value.update(changes)
    return value


def stock(client,product=4,location="A"):
    return next(p for p in client.get("/api/state").json()["products"] if p["id"]==product)["balances"][location]


def test_dispatch_cannot_make_stock_negative_or_create_failed_audit(api):
    client,db=api
    before=client.get("/api/state").json()
    response=client.post("/api/movements",headers=OPERATOR,json=payload(quantity=10))
    assert response.status_code==409
    assert response.json()["error"]["code"]=="insufficient_stock"
    after=client.get("/api/state").json()
    assert after["products"]==before["products"]
    assert after["audit"]==before["audit"]
    assert after["movements"]==before["movements"]


def test_idempotent_retry_does_not_duplicate_stock_or_audit(api):
    client,db=api
    before=stock(client)
    first=client.post("/api/movements",headers=OPERATOR,json=payload())
    retry=client.post("/api/movements",headers=OPERATOR,json=payload())
    assert first.status_code==retry.status_code==201
    assert first.json()["replayed"] is False
    assert retry.json()["replayed"] is True
    assert first.json()["movement"]["id"]==retry.json()["movement"]["id"]
    assert stock(client)==before-1
    with closing(connect(db)) as conn:
        assert conn.execute("SELECT count(*) FROM movements WHERE idempotency_key='test-move-001'").fetchone()[0]==1
        assert conn.execute("SELECT count(*) FROM audit WHERE entity_id=?",(first.json()["movement"]["id"],)).fetchone()[0]==1


def test_same_key_with_different_payload_rejected(api):
    client,db=api
    assert client.post("/api/movements",headers=OPERATOR,json=payload()).status_code==201
    response=client.post("/api/movements",headers=OPERATOR,json=payload(quantity=2))
    assert response.status_code==409
    assert response.json()["error"]["code"]=="idempotency_conflict"
    assert stock(client)==8


def test_concurrent_dispatches_serialize_and_never_overdraw(api):
    client,db=api
    def dispatch(i):
        return client.post("/api/movements",headers=OPERATOR,json=payload(key=f"concurrent-{i:03d}" )).status_code
    with ThreadPoolExecutor(max_workers=10) as pool:
        statuses=list(pool.map(dispatch,range(20)))
    assert statuses.count(201)==9
    assert statuses.count(409)==11
    assert stock(client)==0
    with closing(connect(db)) as conn:
        assert conn.execute("SELECT count(*) FROM movements WHERE idempotency_key LIKE 'concurrent-%'").fetchone()[0]==9


def test_concurrent_identical_retry_commits_once(api):
    client,db=api
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses=list(pool.map(lambda _:client.post("/api/movements",headers=OPERATOR,json=payload(key="same-concurrent-key")),range(8)))
    assert all(r.status_code==201 for r in responses)
    assert sum(not r.json()["replayed"] for r in responses)==1
    assert stock(client)==8


def test_transfer_is_atomic_and_preserves_total(api):
    client,db=api
    response=client.post("/api/movements",headers=OPERATOR,json=payload(kind="transfer",quantity=4,to_location="B"))
    assert response.status_code==201
    assert stock(client)==5
    assert stock(client,location="B")==7
    snapshot=client.get("/api/state").json()["products"]
    failed=client.post("/api/movements",headers=OPERATOR,json=payload(key="failed-transfer",kind="transfer",quantity=6,to_location="B"))
    assert failed.status_code==409
    assert client.get("/api/state").json()["products"]==snapshot


def test_failed_audit_insert_rolls_back_stock_and_movement(api):
    client,db=api
    with closing(connect(db)) as conn:
        conn.execute("CREATE TRIGGER fail_demo_audit BEFORE INSERT ON audit WHEN NEW.event='stock.issue' BEGIN SELECT RAISE(ABORT,'forced test failure'); END")
    result=client.post("/api/movements",headers=OPERATOR,json=payload())
    assert result.status_code==503
    assert stock(client)==9
    with closing(connect(db)) as conn:
        assert not conn.execute("SELECT 1 FROM movements WHERE idempotency_key='test-move-001'").fetchone()


def test_viewer_cannot_mutate_and_operator_cannot_approve(api):
    client,db=api
    assert client.post("/api/movements",json=payload()).status_code==403
    assert client.post("/api/requests/REQ-DEMO-001/decision",headers=OPERATOR,json={"decision":"approve"}).status_code==403
    assert client.get("/api/state",headers={"X-Demo-Role":"superuser"}).status_code==403


def test_approval_receipt_is_atomic_and_idempotent(api):
    client,db=api
    original=stock(client,product=3)
    data={"idempotency_key":"receive-approved-001"}
    path="/api/requests/REQ-DEMO-001"
    assert client.post(path+"/receive",headers=OPERATOR,json=data).json()["error"]["code"]=="approval_required"
    assert client.post(path+"/decision",headers=MANAGER,json={"decision":"approve"}).status_code==200
    first=client.post(path+"/receive",headers=OPERATOR,json=data)
    retry=client.post(path+"/receive",headers=OPERATOR,json=data)
    assert first.status_code==retry.status_code==200
    assert retry.json()["replayed"] is True
    assert stock(client,product=3)==original+80
    assert client.post(path+"/receive",headers=OPERATOR,json={"idempotency_key":"different-receipt"}).status_code==409
    assert client.post(path+"/decision",headers=MANAGER,json={"decision":"reject"}).status_code==409


def test_concurrent_receipt_commits_stock_once(api):
    client,db=api
    path="/api/requests/REQ-DEMO-001"
    original=stock(client,product=3)
    assert client.post(path+"/decision",headers=MANAGER,json={"decision":"approve"}).status_code==200
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses=list(pool.map(lambda _:client.post(path+"/receive",headers=OPERATOR,
            json={"idempotency_key":"concurrent-approved-receipt"}),range(8)))
    assert all(r.status_code==200 for r in responses)
    assert sum(not r.json()["replayed"] for r in responses)==1
    assert stock(client,product=3)==original+80
    with closing(connect(db)) as conn:
        assert conn.execute("SELECT count(*) FROM audit WHERE event='request.received' AND entity_id='REQ-DEMO-001'").fetchone()[0]==1


def test_failed_receipt_audit_rolls_back_request_stock_and_movement(api):
    client,db=api
    path="/api/requests/REQ-DEMO-001"
    assert client.post(path+"/decision",headers=MANAGER,json={"decision":"approve"}).status_code==200
    original=stock(client,product=3)
    with closing(connect(db)) as conn:
        conn.execute("CREATE TRIGGER fail_receipt_audit BEFORE INSERT ON audit WHEN NEW.event='request.received' BEGIN SELECT RAISE(ABORT,'forced receipt failure'); END")
    result=client.post(path+"/receive",headers=OPERATOR,json={"idempotency_key":"failed-approved-receipt"})
    assert result.status_code==503
    assert stock(client,product=3)==original
    with closing(connect(db)) as conn:
        assert conn.execute("SELECT status FROM requests WHERE id='REQ-DEMO-001'").fetchone()[0]=="approved"
        assert not conn.execute("SELECT 1 FROM movements WHERE idempotency_key='failed-approved-receipt'").fetchone()


@pytest.mark.parametrize("changes",[{"quantity":0},{"quantity":-1},{"quantity":1.2},{"quantity":"3"},{"kind":"adjust"},{"to_location":"A"},{"from_location":"UNKNOWN"},{"unexpected":True}])
def test_invalid_input_does_not_change_stock(api,changes):
    client,db=api
    response=client.post("/api/movements",headers=OPERATOR,json=payload(**changes))
    assert response.status_code==422
    assert stock(client)==9


def test_request_creation_rejection_and_no_stock_change(api):
    client,db=api
    before=stock(client)
    created=client.post("/api/requests",headers=OPERATOR,json={"product_id":4,"quantity":5,"location":"A","note":"Replacement scanners"})
    assert created.status_code==201
    request_id=created.json()["id"]
    assert client.post(f"/api/requests/{request_id}/decision",headers=MANAGER,json={"decision":"reject"}).json()["status"]=="rejected"
    assert stock(client)==before
    assert client.post(f"/api/requests/{request_id}/receive",headers=OPERATOR,json={"idempotency_key":"rejected-receipt"}).status_code==409


def test_database_persists_across_app_restart_without_reseed(api):
    client,db=api
    assert client.post("/api/movements",headers=OPERATOR,json=payload()).status_code==201
    with TestClient(create_app(db)) as reopened:
        assert stock(reopened)==8
        assert reopened.get("/api/state").json()["summary"]["movement_count"]==4


def test_export_and_health(api):
    client,db=api
    export=client.get("/api/inventory.csv")
    assert export.status_code==200
    assert "PKG-001,Shipping cartons,A,288" in export.text
    assert len(export.text.splitlines())==15
    assert client.get("/api/health").json()["mode"]=="synthetic-demo"
