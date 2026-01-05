from pydantic import BaseModel
from datetime import date
from typing import Optional, List
from uuid import UUID
from app.schemas.attachment import AttachmentResponse


class ExpenseItemCreate(BaseModel):
    topic: str
    type: str
    date: date
    payment_type: str
    currency: Optional[str] = None
    amount: Optional[float] = None
    comment: Optional[str] = None


class ExpenseItemUpdate(BaseModel):
    topic: Optional[str] = None
    type: Optional[str] = None
    date: Optional[date] = None
    payment_type: Optional[str] = None
    currency: Optional[str] = None
    amount: Optional[float] = None
    comment: Optional[str] = None


class ExpenseItemResponse(BaseModel):
    id: UUID
    report_id: UUID

    topic: str
    type: str
    payment_type: str
    date: date
    comment: Optional[str]

    amount: Optional[float]
    currency: Optional[str]

    # ✅ ADD THESE
    amount_eur: Optional[float]
    exchange_rate: Optional[float]
    exchange_rate_date: Optional[date]
    amount_source: Optional[str]

    attachments: List[AttachmentResponse] = []

    class Config:
        from_attributes = True

