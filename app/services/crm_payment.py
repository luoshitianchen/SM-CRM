"""CRM 回款服务层：合同关联校验与金额正数约束。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.crm_payment import CrmPayment
from app.repositories import crm_contract as contract_repo
from app.repositories import crm_payment as repo
from app.schemas.crm_payment import PaymentCreate, PaymentUpdate
from app.services.audit import record_audit


def _to_dict(p: CrmPayment) -> dict:
    return {
        "id": p.id, "contract_id": p.contract_id, "customer_id": p.customer_id,
        "amount": p.amount, "method": p.method, "paid_at": p.paid_at,
        "status": p.status, "remark": p.remark,
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
    }


class PaymentService:
    @staticmethod
    async def list_payments(
        session: AsyncSession, limit: int, offset: int,
        status_filter: str | None, contract_id: str | None, customer_id: str | None,
    ) -> dict:
        rows = await repo.list_payments(
            session, limit=limit, offset=offset, status=status_filter,
            contract_id=contract_id, customer_id=customer_id
        )
        total = await repo.count_payments(
            session, status=status_filter, contract_id=contract_id, customer_id=customer_id
        )
        return {"total": total, "items": [_to_dict(p) for p in rows]}

    @staticmethod
    async def get_payment(session: AsyncSession, payment_id: str) -> dict:
        p = await repo.get_payment(session, payment_id)
        if not p:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "回款单不存在")
        return _to_dict(p)

    @staticmethod
    async def create_payment(
        session: AsyncSession, payload: PaymentCreate, request: Request,
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if payload.amount <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "回款金额必须大于 0")
        contract = await contract_repo.get_contract(session, payload.contract_id)
        if not contract:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "关联合同不存在")
        payment = CrmPayment(
            id=str(uuid.uuid4()), contract_id=contract.id, customer_id=contract.customer_id,
            amount=payload.amount, method=payload.method, paid_at=payload.paid_at,
            remark=payload.remark, status="pending",
        )
        payment = await repo.create_payment(session, payment)
        await record_audit(session, "crm.payment.created", "internal",
                           f"payment_id={payment.id}", request)
        return _to_dict(payment)

    @staticmethod
    async def update_payment(
        session: AsyncSession, payment_id: str, payload: PaymentUpdate, request: Request,
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        p = await repo.get_payment(session, payment_id)
        if not p:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "回款单不存在")
        if payload.amount is not None and payload.amount <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "回款金额必须大于 0")
        for field in ("amount", "method", "paid_at", "remark"):
            value = getattr(payload, field)
            if value is not None:
                setattr(p, field, value)
        p = await repo.update_payment(session, p)
        await record_audit(session, "crm.payment.updated", "internal",
                           f"payment_id={payment_id}", request)
        return _to_dict(p)

    @staticmethod
    async def update_status(
        session: AsyncSession, payment_id: str, new_status: str, request: Request,
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        p = await repo.get_payment(session, payment_id)
        if not p:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "回款单不存在")
        p.status = new_status
        p = await repo.update_payment(session, p)
        await record_audit(session, "crm.payment.status_changed", "internal",
                           f"payment_id={payment_id} status={new_status}", request)
        return _to_dict(p)

    @staticmethod
    async def delete_payment(session: AsyncSession, payment_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        p = await repo.get_payment(session, payment_id)
        if not p:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "回款单不存在")
        await repo.delete_payment(session, p)
        await record_audit(session, "crm.payment.deleted", "internal",
                           f"payment_id={payment_id}", request)
        return {"deleted": True, "id": payment_id}
