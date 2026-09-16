"""CRM 商机管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.crm_opportunity import OpportunityCreate, OpportunityStageUpdate, OpportunityUpdate
from app.services.crm_opportunity import OpportunityService

router = APIRouter(prefix="/api/crm/opportunities", tags=["crm-opportunities"])


@router.get("")
async def list_opportunities(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    stage: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await OpportunityService.list_opportunities(
        session, limit=limit, offset=offset, stage=stage, customer_id=customer_id
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    payload: OpportunityCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await OpportunityService.create_opportunity(session, payload, request)


@router.get("/{opp_id}")
async def get_opportunity(
    opp_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await OpportunityService.get_opportunity(session, opp_id)


@router.patch("/{opp_id}")
async def update_opportunity(
    opp_id: str, payload: OpportunityUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await OpportunityService.update_opportunity(session, opp_id, payload, request)


@router.patch("/{opp_id}/stage")
async def change_opportunity_stage(
    opp_id: str, payload: OpportunityStageUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await OpportunityService.change_stage(session, opp_id, payload.stage, request)


@router.delete("/{opp_id}")
async def delete_opportunity(
    opp_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await OpportunityService.delete_opportunity(session, opp_id, request)
