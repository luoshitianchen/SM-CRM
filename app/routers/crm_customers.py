"""CRM 客户管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.crm_customer import CustomerCreate, CustomerStatusUpdate, CustomerUpdate
from app.services.crm_customer import CustomerService

router = APIRouter(prefix="/api/crm/customers", tags=["crm-customers"])


@router.get("")
async def list_customers(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    level: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CustomerService.list_customers(
        session, limit=limit, offset=offset,
        status_filter=status_filter, level=level, keyword=keyword,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CustomerService.create_customer(session, payload, request)


@router.get("/{customer_id}")
async def get_customer(
    customer_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CustomerService.get_customer(session, customer_id)


@router.patch("/{customer_id}")
async def update_customer(
    customer_id: str, payload: CustomerUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CustomerService.update_customer(session, customer_id, payload, request)


@router.patch("/{customer_id}/status")
async def update_customer_status(
    customer_id: str, payload: CustomerStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CustomerService.update_status(session, customer_id, payload.status, request)


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CustomerService.delete_customer(session, customer_id, request)
