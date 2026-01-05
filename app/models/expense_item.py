import uuid
from sqlalchemy import (
    Column,
    String,
    Date,
    Numeric,
    ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ExpenseItem(Base):
    __tablename__ = "expense_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("expense_reports.id", ondelete="CASCADE"),
        nullable=False
    )

    topic = Column(String, nullable=False)
    type = Column(String, nullable=False)

    currency = Column(String, nullable=True)
    amount = Column(Numeric(10, 2), nullable=True)

    # 🔴 AUTHORITATIVE ACCOUNTING FIELDS
    amount_eur = Column(Numeric(10, 2), nullable=True)
    exchange_rate = Column(Numeric(12, 6), nullable=True)
    exchange_rate_date = Column(Date, nullable=True)
    amount_source = Column(String, nullable=True)  # "ocr" | "manual"

    payment_type = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    comment = Column(String, nullable=True)

    report = relationship("ExpenseReport", back_populates="items")

    attachments = relationship(
        "Attachment",
        back_populates="expense_item",
        cascade="all, delete-orphan"
    )
