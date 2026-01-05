# app/ocr/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional


class ReceiptItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class ReceiptData(BaseModel):
    document_type: Optional[str] = None
    merchant_name: Optional[str] = None
    merchant_address: Optional[str] = None
    merchant_country: Optional[str] = None
    document_id: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None

    currency: Optional[str] = None
    total: Optional[float] = None

    # TEMPORARY FX (LLM-BASED)
    eur_rate_hint: Optional[float] = None
    eur_estimate: Optional[float] = None

    payment_method: Optional[str] = None
    payment_status: Optional[str] = None

    confidence_notes: Optional[str] = None
    raw_notes: Optional[str] = None