"""CRM 回款管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.crm_payment import PaymentCreate, PaymentStatusUpdate, PaymentUpdate
from app.services.crm_payment import PaymentService

router = APIRouter(prefix="/api/crm/payments", tags=["crm-payments"])


@router.get("")
async def list_payments(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    contract_id: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await PaymentService.list_payments(
        session, limit=limit, offset=offset,
        status_filter=status_filter, contract_id=contract_id, customer_id=customer_id
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await PaymentService.create_payment(session, payload, request)


@router.get("/{payment_id}")
async def get_payment(
    payment_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await PaymentService.get_payment(session, payment_id)


@router.patch("/{payment_id}")
async def update_payment(
    payment_id: str, payload: PaymentUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await PaymentService.update_payment(session, payment_id, payload, request)


@router.patch("/{payment_id}/status")
async def update_payment_status(
    payment_id: str, payload: PaymentStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await PaymentService.update_status(session, payment_id, payload.status, request)


@router.delete("/{payment_id}")
async def delete_payment(
    payment_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await PaymentService.delete_payment(session, payment_id, request)
