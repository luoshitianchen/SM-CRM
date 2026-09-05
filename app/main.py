"""SM CRM —— 客户关系管理系统：线索、客户、联系人、商机与跟进活动。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field

from app import base

SERVICE = "sm-crm"
VERSION = "3.0.0"
NAME = "SM CRM"
DESCRIPTION = "客户关系管理系统：线索、客户、联系人、商机与跟进活动"
PORT = 8510


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _init() -> None:
    with base.db_ctx() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, phone TEXT, email TEXT,
                source TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new',
                owner TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, industry TEXT,
                tier TEXT NOT NULL DEFAULT 'standard', status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, name TEXT NOT NULL,
                email TEXT, phone TEXT, role TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, name TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0, stage TEXT NOT NULL DEFAULT 'prospecting',
                probability REAL NOT NULL DEFAULT 10, owner TEXT, expected_close_date TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS activities (
                id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
                activity_type TEXT NOT NULL, note TEXT, performed_by TEXT, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_opps_stage ON opportunities(stage, amount DESC);
            """
        )


app = base.create_app(
    service=SERVICE, name=NAME, description=DESCRIPTION, version=VERSION, port=PORT,
    dependencies=["sm-iam", "sm-audit-log-center"],
    events=["lead.created", "customer.created", "opportunity.updated"],
    overview_fn=lambda _r: {
        "summary": {
            "customers": base.get_db().execute("SELECT COUNT(*) FROM customers").fetchone()[0],
            "open_opportunities": base.get_db().execute("SELECT COUNT(*) FROM opportunities WHERE stage NOT IN ('closed_won','closed_lost')").fetchone()[0],
        }
    },
)
_init()


class LeadIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    phone: str = Field(default="", max_length=30)
    email: str = Field(default="", max_length=120)
    source: str = Field(min_length=2, max_length=40)
    owner: str = Field(default="", max_length=80)


class CustomerIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    industry: str = Field(default="", max_length=60)
    tier: str = Field(default="standard", pattern=r"^(standard|silver|gold|platinum)$")


class ContactIn(BaseModel):
    customer_id: str = Field(min_length=8)
    name: str = Field(min_length=2, max_length=60)
    email: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=30)
    role: str = Field(default="", max_length=60)


class OpportunityIn(BaseModel):
    customer_id: str = Field(min_length=8)
    name: str = Field(min_length=2, max_length=120)
    amount: float = Field(ge=0)
    stage: str = Field(pattern=r"^(prospecting|qualification|proposal|negotiation|closed_won|closed_lost)$")
    probability: float = Field(default=10, ge=0, le=100)
    owner: str = Field(default="", max_length=80)
    expected_close_date: str = Field(default="", max_length=12)


class ActivityIn(BaseModel):
    entity_type: str = Field(pattern=r"^(lead|customer|contact|opportunity)$")
    entity_id: str = Field(min_length=8)
    activity_type: str = Field(min_length=2, max_length=40)
    note: str = Field(default="", max_length=500)
    performed_by: str = Field(default="", max_length=80)


@app.post("/api/crm/leads", status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    lead_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        conn.execute("INSERT INTO leads (id, name, phone, email, source, status, owner, created_at) VALUES (?,?,?,?,?,?,?,?)", (lead_id, payload.name, payload.phone, payload.email, payload.source, "new", payload.owner, _now()))
        base.record_audit("lead.created", "internal", f"lead={lead_id}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": lead_id, "name": payload.name, "status": "new"}


@app.get("/api/crm/leads")
def list_leads(status_: str | None = None) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if status_:
            rows = conn.execute("SELECT * FROM leads WHERE status=? ORDER BY created_at DESC", (status_,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM leads ORDER BY created_at DESC LIMIT 200").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/crm/customers", status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    customer_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        try:
            conn.execute("INSERT INTO customers VALUES (?,?,?,?,?,?)", (customer_id, payload.name, payload.industry, payload.tier, "active", _now()))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "客户已存在") from exc
        base.record_audit("customer.created", "internal", f"customer={customer_id}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": customer_id, "name": payload.name}


@app.get("/api/crm/customers")
def list_customers(tier: str | None = None) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if tier:
            rows = conn.execute("SELECT * FROM customers WHERE tier=? ORDER BY created_at DESC", (tier,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM customers ORDER BY created_at DESC LIMIT 200").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/crm/contacts", status_code=status.HTTP_201_CREATED)
def create_contact(payload: ContactIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    contact_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        if not conn.execute("SELECT 1 FROM customers WHERE id=?", (payload.customer_id,)).fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "客户不存在")
        conn.execute("INSERT INTO contacts VALUES (?,?,?,?,?,?,?)", (contact_id, payload.customer_id, payload.name, payload.email, payload.phone, payload.role, _now()))
    return {"id": contact_id, "customer_id": payload.customer_id}


@app.get("/api/crm/customers/{customer_id}/contacts")
def list_contacts(customer_id: str) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if not conn.execute("SELECT 1 FROM customers WHERE id=?", (customer_id,)).fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "客户不存在")
        rows = conn.execute("SELECT * FROM contacts WHERE customer_id=? ORDER BY created_at DESC", (customer_id,)).fetchall()
    return {"customer_id": customer_id, "items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/crm/opportunities", status_code=status.HTTP_201_CREATED)
def create_opportunity(payload: OpportunityIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    opp_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        if not conn.execute("SELECT 1 FROM customers WHERE id=?", (payload.customer_id,)).fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "客户不存在")
        conn.execute("INSERT INTO opportunities (id, customer_id, name, amount, stage, probability, owner, expected_close_date, created_at) VALUES (?,?,?,?,?,?,?,?,?)", (opp_id, payload.customer_id, payload.name, payload.amount, payload.stage, payload.probability, payload.owner, payload.expected_close_date, _now()))
        base.record_audit("opportunity.updated", "internal", f"opportunity={opp_id} stage={payload.stage}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": opp_id, "name": payload.name, "stage": payload.stage}


@app.get("/api/crm/opportunities")
def list_opportunities(stage: str | None = None) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if stage:
            rows = conn.execute("SELECT * FROM opportunities WHERE stage=? ORDER BY amount DESC", (stage,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM opportunities ORDER BY amount DESC LIMIT 200").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/crm/activities")
def log_activity(payload: ActivityIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    activity_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        conn.execute("INSERT INTO activities VALUES (?,?,?,?,?,?,?)", (activity_id, payload.entity_type, payload.entity_id, payload.activity_type, payload.note, payload.performed_by, _now()))
    return {"id": activity_id, "entity_type": payload.entity_type, "activity_type": payload.activity_type}


@app.get("/api/crm/activities/{entity_type}/{entity_id}")
def list_activities(entity_type: str, entity_id: str) -> dict[str, Any]:
    with base.db_ctx() as conn:
        rows = conn.execute("SELECT * FROM activities WHERE entity_type=? AND entity_id=? ORDER BY created_at DESC LIMIT 100", (entity_type, entity_id)).fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.get("/api/crm/stats")
def stats() -> dict[str, Any]:
    with base.db_ctx() as conn:
        def _count(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]
        row = conn.execute("SELECT COALESCE(SUM(amount),0) AS pipeline FROM opportunities WHERE stage NOT IN ('closed_won','closed_lost')").fetchone()
        return {
            "leads": _count("SELECT COUNT(*) FROM leads"),
            "customers": _count("SELECT COUNT(*) FROM customers"),
            "contacts": _count("SELECT COUNT(*) FROM contacts"),
            "open_opportunities": _count("SELECT COUNT(*) FROM opportunities WHERE stage NOT IN ('closed_won','closed_lost')"),
            "won": _count("SELECT COUNT(*) FROM opportunities WHERE stage='closed_won'"),
            "pipeline_value": row["pipeline"],
        }