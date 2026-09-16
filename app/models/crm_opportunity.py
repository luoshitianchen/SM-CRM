"""CRM 商机模型。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class CrmOpportunity(Base):
    """销售商机：阶段 lead→qualified→proposal→negotiation→won/lost。"""

    __tablename__ = "crm_opportunities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(16), default="lead", index=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    expected_close_date: Mapped[str] = mapped_column(String(32), default="")
    owner: Mapped[str] = mapped_column(String(128), default="")
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
