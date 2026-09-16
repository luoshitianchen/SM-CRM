"""CRM 客户 Pydantic 模型。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=256)
    level: Literal["prospect", "regular", "vip"] = "prospect"
    industry: str = Field(default="", max_length=128)
    owner: str = Field(default="", max_length=128)
    phone: str = Field(default="", max_length=64)
    email: str = Field(default="", max_length=256)
    address: str = Field(default="", max_length=256)
    remark: str = Field(default="", max_length=2000)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=256)
    level: Literal["prospect", "regular", "vip"] | None = None
    industry: str | None = Field(default=None, max_length=128)
    owner: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=256)
    address: str | None = Field(default=None, max_length=256)
    remark: str | None = Field(default=None, max_length=2000)


class CustomerStatusUpdate(BaseModel):
    status: Literal["active", "inactive"]
