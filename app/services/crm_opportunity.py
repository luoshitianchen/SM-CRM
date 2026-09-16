"""CRM 商机服务层：阶段状态机与金额校验。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.crm_opportunity import CrmOpportunity
from app.repositories import crm_customer as customer_repo
from app.repositories import crm_opportunity as repo
from app.schemas.crm_opportunity import OpportunityCreate, OpportunityUpdate
from app.services.audit import record_audit

# 阶段流转顺序，won/lost 为终态
STAGE_ORDER = ["lead", "qualified", "proposal", "negotiation"]
TERMINAL_STAGES = {"won", "lost"}


def _to_dict(o: CrmOpportunity) -> dict:
    return {
        "id": o.id, "customer_id": o.customer_id, "name": o.name,
        "stage": o.stage, "amount": o.amount,
        "expected_close_date": o.expected_close_date, "owner": o.owner,
        "remark": o.remark,
        "created_at": o.created_at.isoformat() if o.created_at else "",
        "updated_at": o.updated_at.isoformat() if o.updated_at else "",
    }


class OpportunityService:
    @staticmethod
    async def list_opportunities(
        session: AsyncSession, limit: int, offset: int,
        stage: str | None, customer_id: str | None,
    ) -> dict:
        rows = await repo.list_opportunities(
            session, limit=limit, offset=offset, stage=stage, customer_id=customer_id
        )
        total = await repo.count_opportunities(session, stage=stage, customer_id=customer_id)
        return {"total": total, "items": [_to_dict(o) for o in rows]}

    @staticmethod
    async def get_opportunity(session: AsyncSession, opp_id: str) -> dict:
        o = await repo.get_opportunity(session, opp_id)
        if not o:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "商机不存在")
        return _to_dict(o)

    @staticmethod
    async def create_opportunity(
        session: AsyncSession, payload: OpportunityCreate, request: Request,
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if payload.amount < 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "商机金额不能为负")
        if not await customer_repo.get_customer(session, payload.customer_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "关联客户不存在")
        opp = CrmOpportunity(
            id=str(uuid.uuid4()), customer_id=payload.customer_id, name=payload.name,
            stage="lead", amount=payload.amount,
            expected_close_date=payload.expected_close_date, owner=payload.owner,
            remark=payload.remark,
        )
        opp = await repo.create_opportunity(session, opp)
        await record_audit(session, "crm.opportunity.created", "internal",
                           f"opportunity_id={opp.id}", request)
        return _to_dict(opp)

    @staticmethod
    async def update_opportunity(
        session: AsyncSession, opp_id: str, payload: OpportunityUpdate, request: Request,
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        o = await repo.get_opportunity(session, opp_id)
        if not o:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "商机不存在")
        if payload.amount is not None and payload.amount < 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "商机金额不能为负")
        for field in ("name", "amount", "expected_close_date", "owner", "remark"):
            value = getattr(payload, field)
            if value is not None:
                setattr(o, field, value)
        o = await repo.update_opportunity(session, o)
        await record_audit(session, "crm.opportunity.updated", "internal",
                           f"opportunity_id={opp_id}", request)
        return _to_dict(o)

    @staticmethod
    async def change_stage(
        session: AsyncSession, opp_id: str, new_stage: str, request: Request,
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        o = await repo.get_opportunity(session, opp_id)
        if not o:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "商机不存在")
        if o.stage in TERMINAL_STAGES:
            raise HTTPException(status.HTTP_409_CONFLICT, f"商机已结案({o.stage})，不可再变更阶段")
        o.stage = new_stage
        o = await repo.update_opportunity(session, o)
        await record_audit(session, "crm.opportunity.stage_changed", "internal",
                           f"opportunity_id={opp_id} stage={new_stage}", request)
        return _to_dict(o)

    @staticmethod
    async def delete_opportunity(session: AsyncSession, opp_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        o = await repo.get_opportunity(session, opp_id)
        if not o:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "商机不存在")
        await repo.delete_opportunity(session, o)
        await record_audit(session, "crm.opportunity.deleted", "internal",
                           f"opportunity_id={opp_id}", request)
        return {"deleted": True, "id": opp_id}
