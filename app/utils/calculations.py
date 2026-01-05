from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport


def recalculate_report_total_eur(db: Session, report_id):
    total = (
        db.query(func.coalesce(func.sum(ExpenseItem.amount_eur), 0))
        .filter(ExpenseItem.report_id == report_id)
        .scalar()
    )

    report = db.query(ExpenseReport).filter_by(id=report_id).first()
    report.total_amount_eur = total
    db.commit()
