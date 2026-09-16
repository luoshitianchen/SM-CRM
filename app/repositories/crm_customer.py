"""CRM 客户仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm_customer import CrmCustomer


async def get_customer(session: AsyncSession, customer_id: str) -> CrmCustomer | None:
    result = await session.execute(select(CrmCustomer).where(CrmCustomer.id == customer_id))
    return result.scalar_one_or_none()


async def get_customer_by_code(session: AsyncSession, code: str) -> CrmCustomer | None:
    result = await session.execute(select(CrmCustomer).where(CrmCustomer.code == code))
    return result.scalar_one_or_none()


async def list_customers(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None, level: str | None = None,
    keyword: str | None = None,
) -> list[CrmCustomer]:
    stmt = select(CrmCustomer).order_by(CrmCustomer.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(CrmCustomer.status == status)
    if level:
        stmt = stmt.where(CrmCustomer.level == level)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(CrmCustomer.name.like(like), CrmCustomer.code.like(like)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_customers(
    session: AsyncSession, status: str | None = None,
    level: str | None = None, keyword: str | None = None,
) -> int:
    stmt = select(func.count(CrmCustomer.id))
    if status:
        stmt = stmt.where(CrmCustomer.status == status)
    if level:
        stmt = stmt.where(CrmCustomer.level == level)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(CrmCustomer.name.like(like), CrmCustomer.code.like(like)))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_customer(session: AsyncSession, customer: CrmCustomer) -> CrmCustomer:
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer


async def update_customer(session: AsyncSession, customer: CrmCustomer) -> CrmCustomer:
    await session.commit()
    await session.refresh(customer)
    return customer


async def delete_customer(session: AsyncSession, customer: CrmCustomer) -> None:
    await session.delete(customer)
    await session.commit()
