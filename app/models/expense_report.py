# app/models/expense_report.py

import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Date,
    DateTime,
    Enum,
    Numeric,
    ForeignKey,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ExpenseReportStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ExpenseReport(Base):
    __tablename__ = "expense_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    concerned_person = Column(String, nullable=False)

    # ✅ Responsible PERSON (email or username)
    hierarchical_plant = Column(String, nullable=False)
    hierarchical_plant_other = Column(String, nullable=True)

    plant_department = Column(String, nullable=False)

    date_start = Column(Date, nullable=False)
    date_end = Column(Date, nullable=False)

    status = Column(
        Enum(ExpenseReportStatus),
        default=ExpenseReportStatus.draft,
        nullable=False,
    )

    total_amount_eur = Column(Numeric(12, 2), default=0)

    submitted_at = Column(DateTime, nullable=True)

    # ✅ FINAL decision fields (ONLY ONCE)
    decision_at = Column(DateTime, nullable=True)
    decision_comment = Column(Text, nullable=True)

    # 🔐 Approval by email
    approval_token = Column(String(64), unique=True, index=True, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="expense_reports")

    items = relationship(
        "ExpenseItem",
        back_populates="report",
        cascade="all, delete-orphan",
    )
