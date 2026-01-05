from uuid import UUID
import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport, ExpenseReportStatus
from app.schemas.expense_item import (
    ExpenseItemCreate,
    ExpenseItemUpdate,
    ExpenseItemResponse,
)
from app.utils.calculations import recalculate_report_total_eur

router = APIRouter(tags=["Expense items"])


@router.post(
    "/expense-reports/{report_id}/items",
    response_model=ExpenseItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_item(
    report_id: UUID,
    payload: ExpenseItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(ExpenseReport).filter(ExpenseReport.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    if report.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    if report.status != ExpenseReportStatus.draft:
        raise HTTPException(403, "Report is locked")

    item = ExpenseItem(
        id=uuid_lib.uuid4(),
        report_id=report.id,
        topic=payload.topic,
        type=payload.type,
        date=payload.date,
        payment_type=payload.payment_type,
        comment=payload.comment,
        currency=payload.currency.upper() if payload.currency else None,
        amount=payload.amount,
        amount_source="manual" if payload.amount and payload.currency else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    recalculate_report_total_eur(db, report.id)
    return item


@router.put("/items/{item_id}", response_model=ExpenseItemResponse)
def update_item(
    item_id: UUID,
    payload: ExpenseItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(ExpenseItem).filter(ExpenseItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")

    report = item.report
    if report.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    if report.status != ExpenseReportStatus.draft:
        raise HTTPException(403, "Only draft reports can be modified")

    data = payload.model_dump(exclude_unset=True)
    if "currency" in data and data["currency"]:
        data["currency"] = data["currency"].upper()

    for k, v in data.items():
        setattr(item, k, v)

    if ("amount" in data) or ("currency" in data):
        if item.amount is not None and item.currency is not None:
            item.amount_source = "manual"

    db.commit()
    db.refresh(item)
    recalculate_report_total_eur(db, report.id)
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(ExpenseItem).filter(ExpenseItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")

    report = item.report
    if report.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")
    if report.status != ExpenseReportStatus.draft:
        raise HTTPException(403, "Only draft reports can be modified")

    db.delete(item)
    db.commit()
    recalculate_report_total_eur(db, report.id)
    return None
