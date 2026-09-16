"""CRM 合同仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm_contract import CrmContract


async def get_contract(session: AsyncSession, contract_id: str) -> CrmContract | None:
    result = await session.execute(select(CrmContract).where(CrmContract.id == contract_id))
    return result.scalar_one_or_none()


async def get_contract_by_code(session: AsyncSession, code: str) -> CrmContract | None:
    result = await session.execute(select(CrmContract).where(CrmContract.code == code))
    return result.scalar_one_or_none()


async def list_contracts(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None, customer_id: str | None = None,
) -> list[CrmContract]:
    stmt = select(CrmContract).order_by(CrmContract.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(CrmContract.status == status)
    if customer_id:
        stmt = stmt.where(CrmContract.customer_id == customer_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_contracts(
    session: AsyncSession, status: str | None = None, customer_id: str | None = None,
) -> int:
    stmt = select(func.count(CrmContract.id))
    if status:
        stmt = stmt.where(CrmContract.status == status)
    if customer_id:
        stmt = stmt.where(CrmContract.customer_id == customer_id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_contract(session: AsyncSession, contract: CrmContract) -> CrmContract:
    session.add(contract)
    await session.commit()
    await session.refresh(contract)
    return contract


async def update_contract(session: AsyncSession, contract: CrmContract) -> CrmContract:
    await session.commit()
    await session.refresh(contract)
    return contract


async def delete_contract(session: AsyncSession, contract: CrmContract) -> None:
    await session.delete(contract)
    await session.commit()
