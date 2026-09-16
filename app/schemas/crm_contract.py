"""CRM 合同 Pydantic 模型。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ContractCreate(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    opportunity_id: str = Field(default="", max_length=64)
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=256)
    amount: float = Field(default=0.0, ge=0)
    start_date: str = Field(default="", max_length=32)
    end_date: str = Field(default="", max_length=32)
    signed_at: str = Field(default="", max_length=32)
    remark: str = Field(default="", max_length=2000)


class ContractUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    amount: float | None = Field(default=None, ge=0)
    start_date: str | None = Field(default=None, max_length=32)
    end_date: str | None = Field(default=None, max_length=32)
    signed_at: str | None = Field(default=None, max_length=32)
    remark: str | None = Field(default=None, max_length=2000)


class ContractStatusUpdate(BaseModel):
    status: Literal["draft", "active", "completed", "terminated"]
