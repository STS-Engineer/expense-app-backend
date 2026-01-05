import uuid
from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    expense_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("expense_items.id", ondelete="CASCADE"),
        nullable=False
    )

    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)

    ocr_status = Column(String, nullable=True)
    ocr_json = Column(JSON, nullable=True)
    ocr_error = Column(String, nullable=True)
    ocr_text = Column(String, nullable=True)

    expense_item = relationship(
        "ExpenseItem",
        back_populates="attachments"
    )
