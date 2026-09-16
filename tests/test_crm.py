"""CRM 业务深化测试：客户/商机/合同/回款全生命周期与业务规则。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

INTERNAL_TOKEN = "test-internal-key-12345"
AUTH_HEADERS = {"X-Internal-Token": INTERNAL_TOKEN}

# 共享内存库跨用例持久化，编码需全局唯一
_counter = {"n": 0}


def uniq(prefix: str) -> str:
    _counter["n"] += 1
    return f"{prefix}-{_counter['n']}"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════
# 客户管理
# ═══════════════════════════════════════════════════════════

class TestCustomerManagement:
    def test_create_customer_success(self, client):
        resp = client.post("/api/crm/customers", json={
            "code": "CUST-001", "name": "武汉示例科技有限公司",
            "level": "regular", "industry": "制造", "owner": "张三",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "CUST-001"
        assert data["status"] == "active"
        assert "id" in data

    def test_create_customer_requires_internal_token(self, client):
        resp = client.post("/api/crm/customers", json={
            "code": "CUST-NOAUTH", "name": "无令牌客户",
        })
        assert resp.status_code in (401, 403)

    def test_create_customer_duplicate_code(self, client):
        resp = client.post("/api/crm/customers", json={
            "code": "CUST-001", "name": "重复编码客户",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_list_customers(self, client):
        resp = client.get("/api/crm/customers", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_customers_keyword_search(self, client):
        resp = client.get("/api/crm/customers?keyword=示例", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert any("示例" in item["name"] for item in resp.json()["items"])

    def test_list_customers_filter_level(self, client):
        resp = client.get("/api/crm/customers?level=vip", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert all(item["level"] == "vip" for item in resp.json()["items"])

    def test_get_customer_by_id(self, client):
        list_resp = client.get("/api/crm/customers", headers=AUTH_HEADERS)
        cid = list_resp.json()["items"][0]["id"]
        resp = client.get(f"/api/crm/customers/{cid}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["id"] == cid

    def test_get_customer_not_found(self, client):
        resp = client.get("/api/crm/customers/nonexistent-id", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_update_customer(self, client):
        list_resp = client.get("/api/crm/customers", headers=AUTH_HEADERS)
        cid = list_resp.json()["items"][0]["id"]
        resp = client.patch(f"/api/crm/customers/{cid}", json={
            "owner": "李四", "level": "vip",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["owner"] == "李四"
        assert resp.json()["level"] == "vip"

    def test_update_customer_status_inactive(self, client):
        list_resp = client.get("/api/crm/customers", headers=AUTH_HEADERS)
        cid = list_resp.json()["items"][0]["id"]
        resp = client.patch(f"/api/crm/customers/{cid}/status", json={
            "status": "inactive",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "inactive"


# ═══════════════════════════════════════════════════════════
# 商机管理
# ═══════════════════════════════════════════════════════════

class TestOpportunityManagement:
    def _customer_id(self, client) -> str:
        resp = client.post("/api/crm/customers", json={
            "code": uniq("CUST-OPP"), "name": "商机客户",
        }, headers=AUTH_HEADERS)
        return resp.json()["id"]

    def test_create_opportunity_success(self, client):
        cid = self._customer_id(client)
        resp = client.post("/api/crm/opportunities", json={
            "customer_id": cid, "name": "年度框架商机", "amount": 500000,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["stage"] == "lead"
        assert data["amount"] == 500000

    def test_create_opportunity_require_token(self, client):
        cid = self._customer_id(client)
        resp = client.post("/api/crm/opportunities", json={
            "customer_id": cid, "name": "无令牌商机",
        })
        assert resp.status_code in (401, 403)

    def test_create_opportunity_customer_not_found(self, client):
        resp = client.post("/api/crm/opportunities", json={
            "customer_id": "not-exist", "name": "幽灵客户商机",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 400

    def test_list_opportunities_filter_stage(self, client):
        resp = client.get("/api/crm/opportunities?stage=lead", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert all(item["stage"] == "lead" for item in resp.json()["items"])

    def test_change_opportunity_stage(self, client):
        cid = self._customer_id(client)
        create = client.post("/api/crm/opportunities", json={
            "customer_id": cid, "name": "阶段流转商机",
        }, headers=AUTH_HEADERS).json()
        resp = client.patch(f"/api/crm/opportunities/{create['id']}/stage", json={
            "stage": "qualified",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["stage"] == "qualified"

    def test_terminal_opportunity_locked(self, client):
        cid = self._customer_id(client)
        create = client.post("/api/crm/opportunities", json={
            "customer_id": cid, "name": "终态商机",
        }, headers=AUTH_HEADERS).json()
        client.patch(f"/api/crm/opportunities/{create['id']}/stage", json={
            "stage": "won",
        }, headers=AUTH_HEADERS)
        resp = client.patch(f"/api/crm/opportunities/{create['id']}/stage", json={
            "stage": "negotiation",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_delete_opportunity(self, client):
        cid = self._customer_id(client)
        create = client.post("/api/crm/opportunities", json={
            "customer_id": cid, "name": "待删除商机",
        }, headers=AUTH_HEADERS).json()
        resp = client.delete(f"/api/crm/opportunities/{create['id']}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════════════════
# 合同管理
# ═══════════════════════════════════════════════════════════

class TestContractManagement:
    def _customer_id(self, client) -> str:
        resp = client.post("/api/crm/customers", json={
            "code": uniq("CUST-CTR"), "name": "合同客户",
        }, headers=AUTH_HEADERS)
        return resp.json()["id"]

    def test_create_contract_success(self, client):
        cid = self._customer_id(client)
        resp = client.post("/api/crm/contracts", json={
            "customer_id": cid, "code": "CTR-001", "title": "年度服务合同",
            "amount": 120000, "start_date": "2026-01-01", "end_date": "2026-12-31",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        assert resp.json()["status"] == "draft"
        assert resp.json()["code"] == "CTR-001"

    def test_create_contract_duplicate_code(self, client):
        cid = self._customer_id(client)
        resp = client.post("/api/crm/contracts", json={
            "customer_id": cid, "code": "CTR-001", "title": "重复编码",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_create_contract_invalid_date_range(self, client):
        cid = self._customer_id(client)
        resp = client.post("/api/crm/contracts", json={
            "customer_id": cid, "code": "CTR-BAD", "title": "日期倒置",
            "start_date": "2026-12-31", "end_date": "2026-01-01",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 400

    def test_contract_status_transition(self, client):
        cid = self._customer_id(client)
        create = client.post("/api/crm/contracts", json={
            "customer_id": cid, "code": "CTR-TR", "title": "状态机合同",
        }, headers=AUTH_HEADERS).json()
        ok = client.patch(f"/api/crm/contracts/{create['id']}/status", json={
            "status": "active",
        }, headers=AUTH_HEADERS)
        assert ok.status_code == 200
        assert ok.json()["status"] == "active"

    def test_contract_invalid_transition_rejected(self, client):
        cid = self._customer_id(client)
        create = client.post("/api/crm/contracts", json={
            "customer_id": cid, "code": "CTR-BADTR", "title": "非法流转合同",
        }, headers=AUTH_HEADERS).json()
        # draft 不允许直接 completed
        resp = client.patch(f"/api/crm/contracts/{create['id']}/status", json={
            "status": "completed",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_get_contract_not_found(self, client):
        resp = client.get("/api/crm/contracts/nonexistent", headers=AUTH_HEADERS)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════
# 回款管理
# ═══════════════════════════════════════════════════════════

class TestPaymentManagement:
    def _contract_id(self, client) -> str:
        cust = client.post("/api/crm/customers", json={
            "code": uniq("CUST-PAY"), "name": "回款客户",
        }, headers=AUTH_HEADERS).json()
        contract = client.post("/api/crm/contracts", json={
            "customer_id": cust["id"], "code": uniq("CTR-PAY"), "title": "回款合同",
            "amount": 80000,
        }, headers=AUTH_HEADERS).json()
        return contract["id"]

    def test_create_payment_success(self, client):
        cid = self._contract_id(client)
        resp = client.post("/api/crm/payments", json={
            "contract_id": cid, "amount": 40000,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["amount"] == 40000

    def test_create_payment_nonpositive_amount(self, client):
        cid = self._contract_id(client)
        resp = client.post("/api/crm/payments", json={
            "contract_id": cid, "amount": 0,
        }, headers=AUTH_HEADERS)
        # schema 层 gt=0 直接 422
        assert resp.status_code == 422

    def test_create_payment_contract_not_found(self, client):
        resp = client.post("/api/crm/payments", json={
            "contract_id": "ghost-contract", "amount": 100,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 400

    def test_list_payments_filter_status(self, client):
        resp = client.get("/api/crm/payments?status=pending", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert all(item["status"] == "pending" for item in resp.json()["items"])

    def test_mark_payment_received(self, client):
        cid = self._contract_id(client)
        create = client.post("/api/crm/payments", json={
            "contract_id": cid, "amount": 1000,
        }, headers=AUTH_HEADERS).json()
        resp = client.patch(f"/api/crm/payments/{create['id']}/status", json={
            "status": "received",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

    def test_delete_payment(self, client):
        cid = self._contract_id(client)
        create = client.post("/api/crm/payments", json={
            "contract_id": cid, "amount": 2000,
        }, headers=AUTH_HEADERS).json()
        resp = client.delete(f"/api/crm/payments/{create['id']}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True
