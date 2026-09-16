"""CRM 合同管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.crm_contract import ContractCreate, ContractStatusUpdate, ContractUpdate
from app.services.crm_contract import ContractService

router = APIRouter(prefix="/api/crm/contracts", tags=["crm-contracts"])


@router.get("")
async def list_contracts(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    customer_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ContractService.list_contracts(
        session, limit=limit, offset=offset,
        status_filter=status_filter, customer_id=customer_id
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: ContractCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ContractService.create_contract(session, payload, request)


@router.get("/{contract_id}")
async def get_contract(
    contract_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ContractService.get_contract(session, contract_id)


@router.patch("/{contract_id}")
async def update_contract(
    contract_id: str, payload: ContractUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ContractService.update_contract(session, contract_id, payload, request)


@router.patch("/{contract_id}/status")
async def change_contract_status(
    contract_id: str, payload: ContractStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ContractService.change_status(session, contract_id, payload.status, request)


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ContractService.delete_contract(session, contract_id, request)
