"""CRM 客户服务层：客户全生命周期管理。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.crm_customer import CrmCustomer
from app.repositories import crm_customer as repo
from app.schemas.crm_customer import CustomerCreate, CustomerUpdate
from app.services.audit import record_audit


def _to_dict(c: CrmCustomer) -> dict:
    return {
        "id": c.id, "code": c.code, "name": c.name, "level": c.level,
        "industry": c.industry, "owner": c.owner, "phone": c.phone,
        "email": c.email or "", "address": c.address, "status": c.status,
        "remark": c.remark,
        "created_at": c.created_at.isoformat() if c.created_at else "",
        "updated_at": c.updated_at.isoformat() if c.updated_at else "",
    }


class CustomerService:
    @staticmethod
    async def list_customers(
        session: AsyncSession, limit: int, offset: int,
        status_filter: str | None, level: str | None, keyword: str | None,
    ) -> dict:
        rows = await repo.list_customers(
            session, limit=limit, offset=offset, status=status_filter,
            level=level, keyword=keyword,
        )
        total = await repo.count_customers(
            session, status=status_filter, level=level, keyword=keyword
        )
        return {"total": total, "items": [_to_dict(c) for c in rows]}

    @staticmethod
    async def get_customer(session: AsyncSession, customer_id: str) -> dict:
        c = await repo.get_customer(session, customer_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "客户不存在")
        return _to_dict(c)

    @staticmethod
    async def create_customer(session: AsyncSession, payload: CustomerCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if await repo.get_customer_by_code(session, payload.code):
            raise HTTPException(status.HTTP_409_CONFLICT, "客户编码已存在")
        customer = CrmCustomer(
            id=str(uuid.uuid4()), code=payload.code, name=payload.name,
            level=payload.level, industry=payload.industry, owner=payload.owner,
            phone=payload.phone, email=payload.email, address=payload.address,
            remark=payload.remark, status="active",
        )
        customer = await repo.create_customer(session, customer)
        await record_audit(session, "crm.customer.created", "internal",
                           f"code={payload.code}", request)
        return _to_dict(customer)

    @staticmethod
    async def update_customer(
        session: AsyncSession, customer_id: str, payload: CustomerUpdate, request: Request,
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        c = await repo.get_customer(session, customer_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "客户不存在")
        for field in ("name", "level", "industry", "owner", "phone", "email", "address", "remark"):
            value = getattr(payload, field)
            if value is not None:
                setattr(c, field, value)
        c = await repo.update_customer(session, c)
        await record_audit(session, "crm.customer.updated", "internal",
                           f"customer_id={customer_id}", request)
        return _to_dict(c)

    @staticmethod
    async def update_status(
        session: AsyncSession, customer_id: str, new_status: str, request: Request,
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        c = await repo.get_customer(session, customer_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "客户不存在")
        c.status = new_status
        c = await repo.update_customer(session, c)
        await record_audit(session, "crm.customer.status_changed", "internal",
                           f"customer_id={customer_id} status={new_status}", request)
        return _to_dict(c)

    @staticmethod
    async def delete_customer(session: AsyncSession, customer_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        c = await repo.get_customer(session, customer_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "客户不存在")
        code = c.code
        await repo.delete_customer(session, c)
        await record_audit(session, "crm.customer.deleted", "internal",
                           f"customer_id={customer_id} code={code}", request)
        return {"deleted": True, "id": customer_id}
