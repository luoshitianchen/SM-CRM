"""CRM 回款仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm_payment import CrmPayment


async def get_payment(session: AsyncSession, payment_id: str) -> CrmPayment | None:
    result = await session.execute(select(CrmPayment).where(CrmPayment.id == payment_id))
    return result.scalar_one_or_none()


async def list_payments(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None, contract_id: str | None = None,
    customer_id: str | None = None,
) -> list[CrmPayment]:
    stmt = select(CrmPayment).order_by(CrmPayment.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(CrmPayment.status == status)
    if contract_id:
        stmt = stmt.where(CrmPayment.contract_id == contract_id)
    if customer_id:
        stmt = stmt.where(CrmPayment.customer_id == customer_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_payments(
    session: AsyncSession, status: str | None = None,
    contract_id: str | None = None, customer_id: str | None = None,
) -> int:
    stmt = select(func.count(CrmPayment.id))
    if status:
        stmt = stmt.where(CrmPayment.status == status)
    if contract_id:
        stmt = stmt.where(CrmPayment.contract_id == contract_id)
    if customer_id:
        stmt = stmt.where(CrmPayment.customer_id == customer_id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_payment(session: AsyncSession, payment: CrmPayment) -> CrmPayment:
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def update_payment(session: AsyncSession, payment: CrmPayment) -> CrmPayment:
    await session.commit()
    await session.refresh(payment)
    return payment


async def delete_payment(session: AsyncSession, payment: CrmPayment) -> None:
    await session.delete(payment)
    await session.commit()
