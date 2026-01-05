# app/api/expense_reports.py

from datetime import datetime
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.expense_report import ExpenseReport, ExpenseReportStatus
from app.models.expense_item import ExpenseItem
from app.schemas.expense_report import (
    ExpenseReportCreate,
    ExpenseReportUpdate,
    ExpenseReportOut,
)
from app.core.roles import ROLE_EMPLOYEE
from app.core.permissions import require_roles
from app.services.email_service import send_responsible_email

router = APIRouter(tags=["Expense Reports"])


# --------------------------------------------------
# CREATE DRAFT
# --------------------------------------------------
@router.post("", response_model=ExpenseReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ExpenseReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = ExpenseReport(
        id=uuid.uuid4(),
        user_id=current_user.id,
        concerned_person=payload.concerned_person,
        hierarchical_plant=payload.hierarchical_plant,
        hierarchical_plant_other=payload.hierarchical_plant_other,
        plant_department=payload.plant_department,
        date_start=payload.date_start,
        date_end=payload.date_end,
        status=ExpenseReportStatus.draft,
    )

    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# --------------------------------------------------
# LIST MY REPORTS
# --------------------------------------------------
@router.get("", response_model=list[ExpenseReportOut])
def list_my_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(ExpenseReport)
        .options(joinedload(ExpenseReport.items).joinedload(ExpenseItem.attachments))
        .filter(ExpenseReport.user_id == current_user.id)
        .order_by(ExpenseReport.created_at.desc())
        .all()
    )


# --------------------------------------------------
# GET ONE REPORT
# --------------------------------------------------
@router.get("/{report_id}", response_model=ExpenseReportOut)
def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = (
        db.query(ExpenseReport)
        .options(joinedload(ExpenseReport.items).joinedload(ExpenseItem.attachments))
        .filter(ExpenseReport.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return report


# --------------------------------------------------
# UPDATE DRAFT HEADER
# --------------------------------------------------
@router.put("/{report_id}", response_model=ExpenseReportOut)
def update_draft(
    report_id: UUID,
    payload: ExpenseReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(ExpenseReport).filter_by(id=report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if report.status != ExpenseReportStatus.draft:
        raise HTTPException(status_code=403, detail="Report is locked")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(report, k, v)

    db.commit()
    db.refresh(report)
    return report


# --------------------------------------------------
# DELETE DRAFT
# --------------------------------------------------
@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(ExpenseReport).filter_by(id=report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if report.status != ExpenseReportStatus.draft:
        raise HTTPException(status_code=403, detail="Only drafts can be deleted")

    db.delete(report)
    db.commit()
    return None


# --------------------------------------------------
# SUBMIT REPORT (SEND EMAIL)
# --------------------------------------------------
@router.post(
    "/{report_id}/submit",
    status_code=200,
    dependencies=[Depends(require_roles([ROLE_EMPLOYEE]))],
)
def submit_expense_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(ExpenseReport).filter_by(id=report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Expense report not found")
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if report.status != ExpenseReportStatus.draft:
        raise HTTPException(status_code=400, detail="Only draft reports can be submitted")
    if not report.items:
        raise HTTPException(status_code=400, detail="Cannot submit an empty report")

    # 🔐 Generate approval token
    report.status = ExpenseReportStatus.pending
    report.submitted_at = datetime.utcnow()
    report.approval_token = uuid.uuid4().hex

    db.commit()
    db.refresh(report)

    # 📩 SEND EMAIL (SAFE – NEVER BLOCK)
    try:
        responsible_email = report.hierarchical_plant.strip()
        if "@" not in responsible_email:
            responsible_email = f"{responsible_email}@avocarbon.com"

        send_responsible_email(
            to_email=responsible_email,
            concerned_person=report.concerned_person,
            total_eur=float(report.total_amount_eur or 0),
            approval_token=report.approval_token,
        )

        # ✅ TEMP DEBUG LOG (REMOVE AFTER TESTING)
        print(
            f"[EMAIL SENT] to={responsible_email} "
            f"report_id={report.id}"
        )

    except Exception as e:
        print("[EMAIL ERROR]", repr(e))

    return {"status": report.status}
