"""CRM 商机 Pydantic 模型。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OpportunityCreate(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=256)
    amount: float = Field(default=0.0, ge=0)
    expected_close_date: str = Field(default="", max_length=32)
    owner: str = Field(default="", max_length=128)
    remark: str = Field(default="", max_length=2000)


class OpportunityUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=256)
    amount: float | None = Field(default=None, ge=0)
    expected_close_date: str | None = Field(default=None, max_length=32)
    owner: str | None = Field(default=None, max_length=128)
    remark: str | None = Field(default=None, max_length=2000)


class OpportunityStageUpdate(BaseModel):
    stage: Literal["lead", "qualified", "proposal", "negotiation", "won", "lost"]
