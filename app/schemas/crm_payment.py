"""CRM 回款 Pydantic 模型。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    contract_id: str = Field(min_length=1, max_length=64)
    amount: float = Field(gt=0)
    method: Literal["bank_transfer", "cash", "check", "card"] = "bank_transfer"
    paid_at: str = Field(default="", max_length=32)
    remark: str = Field(default="", max_length=2000)


class PaymentUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    method: Literal["bank_transfer", "cash", "check", "card"] | None = None
    paid_at: str | None = Field(default=None, max_length=32)
    remark: str | None = Field(default=None, max_length=2000)


class PaymentStatusUpdate(BaseModel):
    status: Literal["pending", "received", "overdue"]
