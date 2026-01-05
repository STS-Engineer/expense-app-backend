# app/schemas/expense_report.py

from pydantic import BaseModel, model_validator
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
import enum

from app.schemas.expense_item import ExpenseItemResponse


class ExpenseReportStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ExpenseReportCreate(BaseModel):
    concerned_person: str
    hierarchical_plant: str
    hierarchical_plant_other: Optional[str] = None
    plant_department: str
    date_start: date
    date_end: date

    @model_validator(mode="after")
    def validate_hierarchical_plant(self):
        if self.hierarchical_plant.lower() == "other":
            if not self.hierarchical_plant_other:
                raise ValueError(
                    "hierarchical_plant_other is required when hierarchical_plant is 'Other'"
                )
        else:
            self.hierarchical_plant_other = None
        return self


class ExpenseReportUpdate(BaseModel):
    concerned_person: Optional[str] = None
    hierarchical_plant: Optional[str] = None
    hierarchical_plant_other: Optional[str] = None
    plant_department: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None

    @model_validator(mode="after")
    def validate_hierarchical_plant(self):
        if self.hierarchical_plant and self.hierarchical_plant.lower() == "other":
            if not self.hierarchical_plant_other:
                raise ValueError(
                    "hierarchical_plant_other is required when hierarchical_plant is 'Other'"
                )
        return self


class ExpenseReportOut(BaseModel):
    id: UUID
    user_id: UUID
    concerned_person: str
    hierarchical_plant: str
    hierarchical_plant_other: Optional[str]
    plant_department: str
    date_start: date
    date_end: date
    status: ExpenseReportStatus
    total_amount_eur: float
    submitted_at: Optional[datetime]
    decision_at: Optional[datetime]
    decision_comment: Optional[str]
    created_at: datetime
    items: List[ExpenseItemResponse] = []

    class Config:
        from_attributes = True
