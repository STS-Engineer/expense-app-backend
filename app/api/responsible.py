from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from app.models.user import User
from fastapi.responses import Response
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from mimetypes import guess_type
from uuid import UUID
from app.db.session import get_db
from app.models.expense_report import ExpenseReport, ExpenseReportStatus
from app.models.expense_item import ExpenseItem
from app.models.attachment import Attachment
from app.api.auth import get_current_user
from app.core.roles import ROLE_EMPLOYEE
from app.core.permissions import require_roles
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/responsible", tags=["responsible"])


@router.get("/reports/{token}")
def get_report_by_token(token: str, db: Session = Depends(get_db)):
    report = (
        db.query(ExpenseReport)
        .options(
            joinedload(ExpenseReport.items)
            .joinedload(ExpenseItem.attachments)
        )
        .filter(ExpenseReport.approval_token == token)
        .first()
    )

    if not report:
        raise HTTPException(status_code=404, detail="Invalid or expired link")

    return {
        "id": str(report.id),
        "status": report.status,
        "concerned_person": report.concerned_person,
        "hierarchical_responsible": report.hierarchical_plant,
        "plant_department": report.plant_department,
        "date_start": report.date_start,
        "date_end": report.date_end,
        "total_amount_eur": float(report.total_amount_eur or 0),

        "items": [
            {
                "id": str(item.id),
                "topic": item.topic,
                "type": item.type,
                "payment_type": item.payment_type,
                "date": item.date,
                "amount": item.amount,
                "currency": item.currency,
                "amount_eur": item.amount_eur,
                "comment": item.comment,

                "attachments": [
                    {
                        "id": str(att.id),
                        "filename": att.filename,
                        "content_type": att.content_type,
                        "ocr_status": att.ocr_status,
                        "ocr_text": att.ocr_text,
                        "ocr_json": att.ocr_json,
                        # ✅ RESPONSIBLE-SAFE FILE URL
                        "view_url": f"/responsible/reports/{token}/attachments/{att.id}/file",
                    }
                    for att in item.attachments
                ],
            }
            for item in report.items
        ],
    }


# --------------------------------------------------
# DECIDE (APPROVE / REJECT)
# --------------------------------------------------
@router.post("/reports/{token}/decision")
def decide_report(
    token: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    report = db.query(ExpenseReport).filter_by(approval_token=token).first()
    if not report:
        raise HTTPException(status_code=404, detail="Invalid or expired link")

    if report.status != ExpenseReportStatus.pending:
        raise HTTPException(status_code=400, detail="Report already decided")

    decision = payload.get("decision")
    comment = payload.get("comment")

    if decision not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid decision")

    if decision == "reject" and not comment:
        raise HTTPException(status_code=400, detail="Comment required when rejecting")

    report.status = (
        ExpenseReportStatus.approved
        if decision == "approve"
        else ExpenseReportStatus.rejected
    )
    report.decision_comment = comment
    report.decision_at = datetime.utcnow()

    # 🔒 invalidate token
    report.approval_token = None

    db.commit()

    return {"status": report.status}


@router.get(
    "/{report_id}/approval-link",
    dependencies=[Depends(require_roles([ROLE_EMPLOYEE]))],
)
def get_approval_link(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(ExpenseReport).filter_by(id=report_id).first()
    if not report:
        raise HTTPException(status_code=404)

    if report.user_id != current_user.id:
        raise HTTPException(status_code=403)

    if report.status != ExpenseReportStatus.pending:
        raise HTTPException(status_code=400, detail="Report not pending")

    if not report.approval_token:
        raise HTTPException(status_code=400, detail="No approval token")

    return {
        "approval_url": f"http://localhost:5173/responsible/reports/{report.approval_token}"
    }
@router.get("/reports/{token}/pdf")
def download_report_pdf(
    token: str,
    db: Session = Depends(get_db),
):
    report = db.query(ExpenseReport).filter_by(approval_token=token).first()
    if not report:
        raise HTTPException(status_code=404, detail="Invalid or expired link")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40

    # HEADER
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "Expense Report")
    y -= 30

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Concerned person: {report.concerned_person}")
    y -= 15
    pdf.drawString(40, y, f"Department: {report.plant_department}")
    y -= 15
    pdf.drawString(40, y, f"Period: {report.date_start} → {report.date_end}")
    y -= 15
    pdf.drawString(40, y, f"Total: {float(report.total_amount_eur or 0):.2f} EUR")
    y -= 30

    # ITEMS
    for item in report.items:
        if y < 80:
            pdf.showPage()
            y = height - 40

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(40, y, f"{item.topic} — {item.type}")
        y -= 14

        pdf.setFont("Helvetica", 9)
        pdf.drawString(
            40,
            y,
            f"Date: {item.date} | Payment: {item.payment_type}",
        )
        y -= 12

        if item.amount_eur is not None:
            pdf.drawString(
                40,
                y,
                f"Amount: {item.amount_eur:.2f} EUR",
            )
        else:
            pdf.drawString(40, y, "Amount: pending")
        y -= 12

        for att in item.attachments:
            pdf.drawString(
                60,
                y,
                f"Attachment: {att.filename} (OCR: {att.ocr_status})",
            )
            y -= 12

        y -= 10

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=expense_report.pdf"
        },
    )
@router.get("/reports/{token}/attachments/{attachment_id}/file")
def responsible_view_attachment(
    token: str,
    attachment_id: UUID,
    db: Session = Depends(get_db),
):
    # 1️⃣ Validate approval token
    report = (
        db.query(ExpenseReport)
        .filter(ExpenseReport.approval_token == token)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Invalid or expired link")

    # 2️⃣ Ensure attachment belongs to this report
    attachment = (
        db.query(Attachment)
        .join(ExpenseItem)
        .filter(
            Attachment.id == attachment_id,
            ExpenseItem.report_id == report.id,
        )
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    media_type, _ = guess_type(attachment.filename)
    media_type = media_type or attachment.content_type or "application/octet-stream"

    return FileResponse(
        path=attachment.file_path,
        media_type=media_type,
        filename=attachment.filename,
        headers={"Content-Disposition": "inline"},
    )