"""SM CRM 领域测试：线索、客户、联系人、商机、活动与统计。"""

import pytest
from fastapi.testclient import TestClient

from app import base
from app.main import VERSION, app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(base, "internal_api_key", lambda: "TEST")
    base.reset_state()
    from app.main import _init as init_db
    init_db()
    with TestClient(app) as c:
        c.headers["X-Internal-Token"] = "TEST"
        yield c


def _customer(client, name="云启科技"):
    return client.post("/api/crm/customers", json={"name": name, "industry": "软件", "tier": "gold"}).json()["id"]


def test_health_and_version(client):
    r = client.get("/health", headers={"X-Request-Id": "suite-test"})
    assert r.status_code == 200
    assert r.json()["version"] == VERSION


def test_lead_and_customer(client):
    assert client.post("/api/crm/leads", json={"name": "李雷", "source": "展会"}).json()["status"] == "new"
    _customer(client)
    assert client.post("/api/crm/customers", json={"name": "云启科技", "industry": "x"}).status_code == 409
    assert client.get("/api/crm/leads").json()["total"] == 1
    assert client.get("/api/crm/customers").json()["total"] == 1


def test_contact(client):
    customer_id = _customer(client)
    assert client.post("/api/crm/contacts", json={"customer_id": customer_id, "name": "韩梅梅", "role": "采购经理"}).status_code == 201
    assert client.get(f"/api/crm/customers/{customer_id}/contacts").json()["total"] == 1
    assert client.post("/api/crm/contacts", json={"customer_id": "no-such-ct", "name": "xx", "role": "r"}).status_code == 404


def test_opportunity(client):
    customer_id = _customer(client)
    opp = client.post("/api/crm/opportunities", json={"customer_id": customer_id, "name": "ERP 实施", "amount": 500000, "stage": "proposal", "probability": 60, "owner": "王销售"})
    assert opp.status_code == 201
    assert client.get("/api/crm/opportunities").json()["total"] == 1
    assert client.get("/api/crm/opportunities", params={"stage": "proposal"}).json()["total"] == 1


def test_activity(client):
    customer_id = _customer(client)
    assert client.post("/api/crm/activities", json={"entity_type": "customer", "entity_id": customer_id, "activity_type": "call", "note": "沟通需求"}).status_code == 200
    assert client.get(f"/api/crm/activities/customer/{customer_id}").json()["total"] == 1


def test_stats(client):
    customer_id = _customer(client)
    client.post("/api/crm/opportunities", json={"customer_id": customer_id, "name": "商机", "amount": 100000, "stage": "closed_won", "probability": 100})
    stats = client.get("/api/crm/stats").json()
    assert stats["customers"] == 1
    assert stats["won"] == 1
    assert stats["open_opportunities"] == 0


def test_manifest_and_crypto(client):
    assert client.get("/api/integration/manifest").json()["version"] == VERSION
    enc = client.post("/api/crypto/encrypt", json={"value": "x"}).json()["ciphertext"]
    assert client.post("/api/crypto/decrypt", json={"value": enc}).json()["plaintext"] == "x"


def test_write_requires_auth(client):
    del client.headers["X-Internal-Token"]
    assert client.post("/api/crm/leads", json={"name": "x", "source": "s"}).status_code == 401
