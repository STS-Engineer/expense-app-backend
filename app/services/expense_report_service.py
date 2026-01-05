from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.expense_report import ExpenseReport
from app.models.expense_item import ExpenseItem
from app.models.attachment import Attachment
from app.core.enums import ExpenseStatus
from app.services.calculations import recalculate_report_total


def save_draft(db: Session, payload, user, report_id=None):
    if report_id:
        report = db.query(ExpenseReport).filter_by(
            id=report_id,
            created_by=user.id,
            status=ExpenseStatus.DRAFT
        ).first()
        if not report:
            raise HTTPException(404, "Draft not found")
    else:
        report = ExpenseReport(
            created_by=user.id,
            status=ExpenseStatus.DRAFT,
            total_amount=0
        )
        db.add(report)
        db.flush()

    report.plant = payload.plantDepartment
    report.department = payload.department
    report.start_date = payload.dateRangeStart
    report.end_date = payload.dateRangeEnd

    db.query(ExpenseItem).filter_by(report_id=report.id).delete()

    for item in payload.expenses:
        db.add(ExpenseItem(
            report_id=report.id,
            topic=item.topic,
            type=item.type,
            currency=item.currency,
            amount=item.amount,
            payment_type=item.paymentType,
            date=item.date,
            comment=item.comment
        ))

    recalculate_report_total(db, report.id)
    db.commit()
    db.refresh(report)
    return report


def submit_report(db: Session, report_id: str, user):
    report = db.query(ExpenseReport).filter_by(
        id=report_id,
        created_by=user.id,
        status=ExpenseStatus.DRAFT
    ).first()

    if not report:
        raise HTTPException(404, "Draft not found")

    items = db.query(ExpenseItem).filter_by(report_id=report.id).all()
    if not items:
        raise HTTPException(400, "At least one expense is required")

    for item in items:
        attachments = db.query(Attachment).filter_by(expense_item_id=item.id).count()
        if attachments == 0:
            raise HTTPException(
                400,
                f"Expense '{item.topic}' must have at least one attachment"
            )

    report.status = ExpenseStatus.PENDING
    db.commit()
    return {"status": "submitted"}
