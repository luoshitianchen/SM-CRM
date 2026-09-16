"""CRM 商机仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm_opportunity import CrmOpportunity


async def get_opportunity(session: AsyncSession, opp_id: str) -> CrmOpportunity | None:
    result = await session.execute(select(CrmOpportunity).where(CrmOpportunity.id == opp_id))
    return result.scalar_one_or_none()


async def list_opportunities(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    stage: str | None = None, customer_id: str | None = None,
) -> list[CrmOpportunity]:
    stmt = select(CrmOpportunity).order_by(CrmOpportunity.created_at.desc()).limit(limit).offset(offset)
    if stage:
        stmt = stmt.where(CrmOpportunity.stage == stage)
    if customer_id:
        stmt = stmt.where(CrmOpportunity.customer_id == customer_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_opportunities(
    session: AsyncSession, stage: str | None = None, customer_id: str | None = None,
) -> int:
    stmt = select(func.count(CrmOpportunity.id))
    if stage:
        stmt = stmt.where(CrmOpportunity.stage == stage)
    if customer_id:
        stmt = stmt.where(CrmOpportunity.customer_id == customer_id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_opportunity(session: AsyncSession, opp: CrmOpportunity) -> CrmOpportunity:
    session.add(opp)
    await session.commit()
    await session.refresh(opp)
    return opp


async def update_opportunity(session: AsyncSession, opp: CrmOpportunity) -> CrmOpportunity:
    await session.commit()
    await session.refresh(opp)
    return opp


async def delete_opportunity(session: AsyncSession, opp: CrmOpportunity) -> None:
    await session.delete(opp)
    await session.commit()
