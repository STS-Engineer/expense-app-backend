from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID


class AttachmentResponse(BaseModel):
    id: UUID
    expense_item_id: UUID
    filename: str
    content_type: str
    ocr_status: Optional[str]
    ocr_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
