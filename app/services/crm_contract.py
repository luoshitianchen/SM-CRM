"""CRM 合同服务层：状态机、唯一编码、日期与金额校验。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.crm_contract import CrmContract
from app.repositories import crm_contract as repo
from app.repositories import crm_customer as customer_repo
from app.schemas.crm_contract import ContractCreate, ContractUpdate
from app.services.audit import record_audit

# 允许的状态流转：draft→active→completed / active→terminated
ALLOWED_TRANSITIONS = {
    "draft": {"active"},
    "active": {"completed", "terminated"},
    "completed": set(),
    "terminated": set(),
}


def _to_dict(c: CrmContract) -> dict:
    return {
        "id": c.id, "customer_id": c.customer_id, "opportunity_id": c.opportunity_id,
        "code": c.code, "title": c.title, "amount": c.amount,
        "start_date": c.start_date, "end_date": c.end_date, "status": c.status,
        "signed_at": c.signed_at, "remark": c.remark,
        "created_at": c.created_at.isoformat() if c.created_at else "",
        "updated_at": c.updated_at.isoformat() if c.updated_at else "",
    }


def _validate_dates(start_date: str, end_date: str) -> None:
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "结束日期不能早于开始日期")


class ContractService:
    @staticmethod
    async def list_contracts(
        session: AsyncSession, limit: int, offset: int,
        status_filter: str | None, customer_id: str | None,
    ) -> dict:
        rows = await repo.list_contracts(
            session, limit=limit, offset=offset,
            status=status_filter, customer_id=customer_id
        )
        total = await repo.count_contracts(session, status=status_filter, customer_id=customer_id)
        return {"total": total, "items": [_to_dict(c) for c in rows]}

    @staticmethod
    async def get_contract(session: AsyncSession, contract_id: str) -> dict:
        c = await repo.get_contract(session, contract_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "合同不存在")
        return _to_dict(c)

    @staticmethod
    async def create_contract(
        session: AsyncSession, payload: ContractCreate, request: Request,
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if payload.amount < 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "合同金额不能为负")
        _validate_dates(payload.start_date, payload.end_date)
        if await repo.get_contract_by_code(session, payload.code):
            raise HTTPException(status.HTTP_409_CONFLICT, "合同编码已存在")
        if not await customer_repo.get_customer(session, payload.customer_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "关联客户不存在")
        contract = CrmContract(
            id=str(uuid.uuid4()), customer_id=payload.customer_id,
            opportunity_id=payload.opportunity_id, code=payload.code,
            title=payload.title, amount=payload.amount,
            start_date=payload.start_date, end_date=payload.end_date,
            signed_at=payload.signed_at, remark=payload.remark, status="draft",
        )
        contract = await repo.create_contract(session, contract)
        await record_audit(session, "crm.contract.created", "internal",
                           f"code={payload.code}", request)
        return _to_dict(contract)

    @staticmethod
    async def update_contract(
        session: AsyncSession, contract_id: str, payload: ContractUpdate, request: Request,
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        c = await repo.get_contract(session, contract_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "合同不存在")
        if payload.amount is not None and payload.amount < 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "合同金额不能为负")
        start = payload.start_date if payload.start_date is not None else c.start_date
        end = payload.end_date if payload.end_date is not None else c.end_date
        _validate_dates(start, end)
        for field in ("title", "amount", "start_date", "end_date", "signed_at", "remark"):
            value = getattr(payload, field)
            if value is not None:
                setattr(c, field, value)
        c = await repo.update_contract(session, c)
        await record_audit(session, "crm.contract.updated", "internal",
                           f"contract_id={contract_id}", request)
        return _to_dict(c)

    @staticmethod
    async def change_status(
        session: AsyncSession, contract_id: str, new_status: str, request: Request,
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        c = await repo.get_contract(session, contract_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "合同不存在")
        allowed = ALLOWED_TRANSITIONS.get(c.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"不允许从 {c.status} 变更为 {new_status}",
            )
        c.status = new_status
        c = await repo.update_contract(session, c)
        await record_audit(session, "crm.contract.status_changed", "internal",
                           f"contract_id={contract_id} status={new_status}", request)
        return _to_dict(c)

    @staticmethod
    async def delete_contract(session: AsyncSession, contract_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        c = await repo.get_contract(session, contract_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "合同不存在")
        await repo.delete_contract(session, c)
        await record_audit(session, "crm.contract.deleted", "internal",
                           f"contract_id={contract_id}", request)
        return {"deleted": True, "id": contract_id}
