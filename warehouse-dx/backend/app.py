"""Warehouse DX: synthetic portfolio demo, never a client deployment."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sqlite3
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
ROLE_ACTORS = {"viewer": "Planning desk", "operator": "Warehouse operator", "manager": "Operations manager"}


class DomainError(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code, self.status = code, status


class Movement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    kind: Literal["receive", "issue", "transfer"]
    product_id: int = Field(gt=0, strict=True)
    quantity: int = Field(gt=0, le=100000, strict=True)
    from_location: str | None = Field(default=None, max_length=20)
    to_location: str | None = Field(default=None, max_length=20)
    reference: str = Field(min_length=3, max_length=100)


class Replenishment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int = Field(gt=0, strict=True)
    quantity: int = Field(gt=0, le=100000, strict=True)
    location: str = Field(min_length=1, max_length=20)
    note: str = Field(min_length=3, max_length=200)


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "reject"]


class ReceiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path):
    db = sqlite3.connect(path, timeout=15, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=15000")
    return db


@contextmanager
def transaction(path):
    db = connect(path)
    try:
        # Reserve the write lock before reading stock: concurrent dispatches serialize.
        db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = connect(path)
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY, sku TEXT UNIQUE NOT NULL, name_en TEXT NOT NULL,
            name_ja TEXT NOT NULL, category TEXT NOT NULL, unit TEXT NOT NULL,
            reorder_point INTEGER NOT NULL CHECK(reorder_point >= 0));
        CREATE TABLE IF NOT EXISTS locations (id TEXT PRIMARY KEY, name_en TEXT, name_ja TEXT);
        CREATE TABLE IF NOT EXISTS balances (
            product_id INTEGER REFERENCES products(id), location TEXT REFERENCES locations(id),
            quantity INTEGER NOT NULL CHECK(quantity >= 0), PRIMARY KEY(product_id,location));
        CREATE TABLE IF NOT EXISTS movements (
            id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL, request_hash TEXT NOT NULL,
            kind TEXT NOT NULL, product_id INTEGER REFERENCES products(id), quantity INTEGER NOT NULL CHECK(quantity > 0),
            from_location TEXT REFERENCES locations(id), to_location TEXT REFERENCES locations(id),
            reference TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS requests (
            id TEXT PRIMARY KEY, product_id INTEGER REFERENCES products(id), quantity INTEGER NOT NULL CHECK(quantity > 0),
            location TEXT REFERENCES locations(id), note TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('open','approved','rejected','received')),
            created_by TEXT NOT NULL, created_at TEXT NOT NULL, decided_by TEXT,
            decided_at TEXT, received_at TEXT, movement_id TEXT REFERENCES movements(id));
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, entity_id TEXT NOT NULL,
            actor TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM metadata WHERE key='seeded'").fetchone():
            db.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?)", [
                (1,"PKG-001","Shipping cartons","発送用段ボール","packaging","pcs",150),
                (2,"PKG-002","Protective wraps","緩衝材","packaging","rolls",40),
                (3,"LBL-003","Thermal labels","感熱ラベル","consumables","rolls",60),
                (4,"OPS-004","Handheld scanners","ハンディスキャナー","equipment","pcs",8),
                (5,"OPS-005","Safety gloves","作業用手袋","safety","pairs",80),
                (6,"PKG-006","Packing tape","梱包テープ","packaging","rolls",50),
                (7,"OPS-007","Return containers","返品用コンテナ","equipment","pcs",20),
            ])
            db.executemany("INSERT INTO locations VALUES (?,?,?)", [
                ("A","Main warehouse","本倉庫"),("B","Dispatch hub","出荷拠点")])
            db.executemany("INSERT INTO balances VALUES (?,?,?)", [
                (1,"A",240),(1,"B",72),(2,"A",20),(2,"B",12),(3,"A",18),(3,"B",8),
                (4,"A",9),(4,"B",3),(5,"A",100),(5,"B",44),(6,"A",67),(6,"B",21),
                (7,"A",11),(7,"B",5)])
            now=utc_now()
            db.execute("INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                ("REQ-DEMO-001",3,80,"A","Weekly replenishment / 週次補充","open",ROLE_ACTORS["operator"],now,None,None,None,None))
            db.execute("INSERT INTO audit(event,entity_id,actor,detail,created_at) VALUES (?,?,?,?,?)",
                ("request.created","REQ-DEMO-001",ROLE_ACTORS["operator"],json.dumps({"quantity":80,"product_id":3}),now))
            for payload in [
                Movement(idempotency_key="seed-receive-001",kind="receive",product_id=1,quantity=48,to_location="A",reference="DEMO-SUPPLIER-001"),
                Movement(idempotency_key="seed-issue-001",kind="issue",product_id=1,quantity=20,from_location="B",reference="DEMO-DISPATCH-001"),
                Movement(idempotency_key="seed-transfer-001",kind="transfer",product_id=3,quantity=4,from_location="A",to_location="B",reference="DEMO-TRANSFER-001"),
            ]:
                movement_in_transaction(db,payload,ROLE_ACTORS["operator"])
            db.execute("INSERT INTO metadata VALUES ('seeded','synthetic-v1')")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def role(x_demo_role: str = Header(default="viewer")):
    if x_demo_role not in ROLE_ACTORS:
        raise DomainError("invalid_role",403)
    return x_demo_role


def require_write(actor_role):
    if actor_role == "viewer":
        raise DomainError("read_only",403)


def audit(db,event,entity,actor,detail):
    db.execute("INSERT INTO audit(event,entity_id,actor,detail,created_at) VALUES (?,?,?,?,?)",
        (event,entity,actor,json.dumps(detail,ensure_ascii=False),utc_now()))


def movement_in_transaction(db, payload: Movement, actor: str):
    data = payload.model_dump()
    digest = hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
    prior = db.execute("SELECT * FROM movements WHERE idempotency_key=?",(payload.idempotency_key,)).fetchone()
    if prior:
        if prior["request_hash"] != digest:
            raise DomainError("idempotency_conflict")
        return dict(prior),True
    if not db.execute("SELECT 1 FROM products WHERE id=?",(payload.product_id,)).fetchone():
        raise DomainError("unknown_product",404)
    source,destination=payload.from_location,payload.to_location
    valid = ((payload.kind=="receive" and not source and destination) or
             (payload.kind=="issue" and source and not destination) or
             (payload.kind=="transfer" and source and destination and source!=destination))
    if not valid:
        raise DomainError("invalid_locations",422)
    for location in (source,destination):
        if location and not db.execute("SELECT 1 FROM locations WHERE id=?",(location,)).fetchone():
            raise DomainError("unknown_location",422)
    if source:
        available=db.execute("SELECT quantity FROM balances WHERE product_id=? AND location=?",
            (payload.product_id,source)).fetchone()
        if not available or available["quantity"] < payload.quantity:
            raise DomainError("insufficient_stock")
        db.execute("UPDATE balances SET quantity=quantity-? WHERE product_id=? AND location=?",
            (payload.quantity,payload.product_id,source))
    if destination:
        db.execute("INSERT INTO balances VALUES (?,?,?) ON CONFLICT(product_id,location) DO UPDATE SET quantity=quantity+excluded.quantity",
            (payload.product_id,destination,payload.quantity))
    movement_id="MOV-"+uuid.uuid4().hex[:12].upper()
    db.execute("INSERT INTO movements VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (movement_id,payload.idempotency_key,digest,payload.kind,payload.product_id,payload.quantity,source,destination,payload.reference,actor,utc_now()))
    audit(db,"stock."+payload.kind,movement_id,actor,{k:v for k,v in data.items() if k!="idempotency_key"})
    return dict(db.execute("SELECT * FROM movements WHERE id=?",(movement_id,)).fetchone()),False


def create_app(db_path: str | Path | None = None):
    database=Path(db_path or os.environ.get("WAREHOUSE_DB",ROOT/"data"/"warehouse.sqlite3"))
    initialize(database)
    app=FastAPI(title="Warehouse DX Demo",version="1.0.0",description="Synthetic portfolio project. Demo role headers are not authentication.")
    app.state.database=database

    @app.exception_handler(DomainError)
    async def domain_handler(request: Request,exc: DomainError):
        return JSONResponse(status_code=exc.status,content={"error":{"code":exc.code}})

    @app.exception_handler(sqlite3.Error)
    async def database_handler(request: Request,exc: sqlite3.Error):
        return JSONResponse(status_code=503,content={"error":{"code":"database_unavailable"}})

    @app.get("/api/health")
    def health():
        return {"status":"ok","mode":"synthetic-demo"}

    @app.get("/api/state")
    def state(actor_role: str = Depends(role)):
        with closing(connect(database)) as db:
            # One read transaction keeps balances, requests and KPIs in a consistent
            # snapshot even while another connection commits a stock movement.
            db.execute("BEGIN")
            products=[]
            for p in db.execute("SELECT * FROM products ORDER BY sku"):
                item=dict(p)
                item["balances"]={r["location"]:r["quantity"] for r in db.execute("SELECT * FROM balances WHERE product_id=?",(p["id"],))}
                item["total"]=sum(item["balances"].values())
                item["low_stock"]=item["total"]<item["reorder_point"]
                products.append(item)
            return {"mode":"synthetic-demo","role":actor_role,"products":products,
                "locations":[dict(r) for r in db.execute("SELECT * FROM locations ORDER BY id")],
                "movements":[{k:v for k,v in dict(r).items() if k not in ('request_hash','idempotency_key')} for r in db.execute("SELECT * FROM movements ORDER BY rowid DESC LIMIT 50")],
                "requests":[dict(r) for r in db.execute("SELECT * FROM requests ORDER BY rowid DESC LIMIT 100")],
                "audit":[dict(r) for r in db.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 50")],
                "summary":{"active_skus":len(products),"units":sum(p["total"] for p in products),
                    "low_stock":sum(p["low_stock"] for p in products),
                    "pending_requests":db.execute("SELECT count(*) FROM requests WHERE status='open'").fetchone()[0],
                    "movement_count":db.execute("SELECT count(*) FROM movements").fetchone()[0]},
                "generated_at":utc_now()}

    @app.post("/api/movements",status_code=201)
    def move(payload: Movement,actor_role: str = Depends(role)):
        require_write(actor_role)
        with transaction(database) as db:
            result,replayed=movement_in_transaction(db,payload,ROLE_ACTORS[actor_role])
            return {"movement":{k:v for k,v in result.items() if k not in ('request_hash','idempotency_key')},"replayed":replayed}

    @app.post("/api/requests",status_code=201)
    def request_stock(payload: Replenishment,actor_role: str = Depends(role)):
        require_write(actor_role)
        with transaction(database) as db:
            if not db.execute("SELECT 1 FROM products WHERE id=?",(payload.product_id,)).fetchone():
                raise DomainError("unknown_product",404)
            if not db.execute("SELECT 1 FROM locations WHERE id=?",(payload.location,)).fetchone():
                raise DomainError("unknown_location",422)
            request_id="REQ-"+uuid.uuid4().hex[:10].upper()
            now=utc_now()
            db.execute("INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (request_id,payload.product_id,payload.quantity,payload.location,payload.note,"open",ROLE_ACTORS[actor_role],now,None,None,None,None))
            audit(db,"request.created",request_id,ROLE_ACTORS[actor_role],payload.model_dump())
            return dict(db.execute("SELECT * FROM requests WHERE id=?",(request_id,)).fetchone())

    @app.post("/api/requests/{request_id}/decision")
    def decide(request_id: str,payload: Decision,actor_role: str = Depends(role)):
        if actor_role!="manager":
            raise DomainError("manager_required",403)
        with transaction(database) as db:
            item=db.execute("SELECT * FROM requests WHERE id=?",(request_id,)).fetchone()
            if not item:
                raise DomainError("unknown_request",404)
            if item["status"]!="open":
                raise DomainError("request_state_conflict")
            status="approved" if payload.decision=="approve" else "rejected"
            db.execute("UPDATE requests SET status=?,decided_by=?,decided_at=? WHERE id=?",(status,ROLE_ACTORS[actor_role],utc_now(),request_id))
            audit(db,"request."+status,request_id,ROLE_ACTORS[actor_role],{})
            return {"id":request_id,"status":status}

    @app.post("/api/requests/{request_id}/receive")
    def receive_request(request_id: str,payload: ReceiveRequest,actor_role: str = Depends(role)):
        require_write(actor_role)
        with transaction(database) as db:
            item=db.execute("SELECT * FROM requests WHERE id=?",(request_id,)).fetchone()
            if not item:
                raise DomainError("unknown_request",404)
            # A retry after commit must resolve to the same movement, never add stock twice.
            if item["status"]=="received":
                prior=db.execute("SELECT idempotency_key FROM movements WHERE id=?",(item["movement_id"],)).fetchone()
                if prior["idempotency_key"]==payload.idempotency_key:
                    return {"id":request_id,"status":"received","movement_id":item["movement_id"],"replayed":True}
                raise DomainError("request_state_conflict")
            if item["status"]!="approved":
                raise DomainError("approval_required")
            movement,replayed=movement_in_transaction(db,Movement(idempotency_key=payload.idempotency_key,kind="receive",
                product_id=item["product_id"],quantity=item["quantity"],to_location=item["location"],reference=request_id),ROLE_ACTORS[actor_role])
            db.execute("UPDATE requests SET status='received',received_at=?,movement_id=? WHERE id=?",(utc_now(),movement["id"],request_id))
            audit(db,"request.received",request_id,ROLE_ACTORS[actor_role],{"movement_id":movement["id"]})
            return {"id":request_id,"status":"received","movement_id":movement["id"],"replayed":replayed}

    @app.get("/api/inventory.csv")
    def export(actor_role: str = Depends(role)):
        output=io.StringIO(newline="")
        writer=csv.writer(output)
        writer.writerow(["SKU","Product","Location","Quantity","Unit","Reorder point (total)"])
        with closing(connect(database)) as db:
            for item in db.execute("SELECT p.sku,p.name_en,b.location,b.quantity,p.unit,p.reorder_point FROM balances b JOIN products p ON p.id=b.product_id ORDER BY p.sku,b.location"):
                writer.writerow(tuple(item))
        return Response("\ufeff"+output.getvalue(),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":"attachment; filename=warehouse-inventory.csv"})

    dist=ROOT/"frontend"/"dist"
    if dist.exists():
        app.mount("/assets",StaticFiles(directory=dist/"assets"),name="assets")
        @app.get("/")
        def frontend():
            return FileResponse(dist/"index.html")
    return app


# Uvicorn --factory avoids creating a database when tests import this module.
