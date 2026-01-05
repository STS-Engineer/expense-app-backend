import os
import uuid
from typing import List
from app.ocr.ui_summary import build_ui_summary
import uuid
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    status,
    BackgroundTasks,
)
from sqlalchemy.orm import Session
from datetime import date
from app.services.amount_service import resolve_amount
from app.db.session import get_db, SessionLocal
from app.api.auth import get_current_user
from app.core.roles import ROLE_EMPLOYEE
from app.core.permissions import require_roles
from app.utils.calculations import recalculate_report_total_eur

from app.models.user import User
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport, ExpenseReportStatus
from app.models.attachment import Attachment
from app.schemas.attachment import AttachmentResponse
from app.ocr.service import extract_receipt

from datetime import date
from app.services.amount_service import resolve_amount
from app.models.expense_item import ExpenseItem
from fastapi.responses import FileResponse
from mimetypes import guess_type

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# IMPORTANT:
# main.py mounts this router with prefix="/api/attachments"
# so DO NOT put prefix="/attachments" here (otherwise you get /api/attachments/attachments/...)
router = APIRouter(tags=["attachments"])


# -------------------------------------------------------------------
# INTERNAL GUARD
# -------------------------------------------------------------------

def get_item_and_report(db: Session, item_id: str, current_user: User) -> ExpenseItem:
    item = db.query(ExpenseItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense item not found")

    report = db.query(ExpenseReport).filter_by(id=item.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Expense report not found")

    # ✅ correct ownership check
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # ✅ correct draft check (Enum)
    if report.status != ExpenseReportStatus.draft:
        raise HTTPException(status_code=403, detail="Expense report is locked")

    return item


# -------------------------------------------------------------------
# OCR BACKGROUND TASK (KEEPING YOUR LOGIC)
# -------------------------------------------------------------------
def run_ocr_task(attachment_id: str):
    db: Session = SessionLocal()
    attachment = None

    try:
        attachment = db.query(Attachment).filter_by(id=attachment_id).first()
        if not attachment:
            return

        attachment.ocr_status = "PROCESSING"
        attachment.ocr_error = None
        attachment.ocr_text = None
        attachment.ocr_json = None
        db.commit()

        result = extract_receipt(attachment.file_path)
        if not result or not result.get("ocr_text"):
            raise RuntimeError("OCR returned empty text")

        # ---- OCR RAW DATA
        attachment.ocr_text = result["ocr_text"]

        # ---- BUILD UI SUMMARY
        ui_summary = build_ui_summary(result["ocr_json"])

        # ---- STORE FULL OCR JSON
        attachment.ocr_json = {
            **result["ocr_json"],
            "ui_summary": ui_summary,
        }
        attachment.ocr_status = "DONE"
        db.commit()

        # ---- APPLY AMOUNT + FX
        item = db.query(ExpenseItem).filter_by(
            id=attachment.expense_item_id
        ).first()

        if not item:
            return

        ocr = result["ocr_json"]
        if ocr.get("total") and ocr.get("currency"):
            item.amount = float(ocr["total"])
            item.currency = ocr["currency"].upper()

            resolved = resolve_amount(
                amount=item.amount,
                currency=item.currency,
                source="ocr",
                conversion_date=date.today(),
            )

            item.amount_eur = resolved["amount_eur"]
            item.exchange_rate = resolved["exchange_rate"]
            item.exchange_rate_date = resolved["exchange_rate_date"]
            item.amount_source = "ocr"

            db.commit()
            recalculate_report_total_eur(db, item.report_id)

    except Exception as e:
        if attachment:
            attachment.ocr_status = "FAILED"
            attachment.ocr_error = str(e)[:2000]
            db.commit()
        print("[OCR FAILED]", repr(e))

    finally:
        db.close()


# -------------------------------------------------------------------
# UPLOAD ATTACHMENTS (MULTI-FILE)
# POST /api/attachments/items/{item_id}
# form-data key: files (repeatable)
# -------------------------------------------------------------------

@router.post(
    "/items/{item_id}",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles([ROLE_EMPLOYEE]))],
)
def upload_attachment(
    item_id: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_item_and_report(db, item_id, current_user)

    # 🚨 BUSINESS RULE: only ONE attachment per expense item
    if len(item.attachments) >= 1:
        raise HTTPException(
            status_code=400,
            detail="Only one attachment is allowed per expense item"
        )

    ext = (file.filename.split(".")[-1] if file.filename else "").lower()
    if ext not in ["jpg", "jpeg", "png", "pdf"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    attachment = Attachment(
        expense_item_id=item.id,
        filename=file.filename,
        content_type=file.content_type,
        file_path=file_path,
        ocr_status="PENDING",
        ocr_error=None,
    )

    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    if background_tasks:
        background_tasks.add_task(run_ocr_task, str(attachment.id))

    return {
        "id": str(attachment.id),
        "expense_item_id": str(attachment.expense_item_id),
        "filename": attachment.filename,
        "content_type": attachment.content_type,
        "file_path": attachment.file_path,
        "ocr_status": attachment.ocr_status,
        "ocr_json": None, 
    }

        


# -------------------------------------------------------------------
# GET OCR RESULT
# GET /api/attachments/{attachment_id}/ocr
# -------------------------------------------------------------------

@router.get(
    "/{attachment_id}/ocr",
    dependencies=[Depends(require_roles([ROLE_EMPLOYEE]))],
)
def get_attachment_ocr(
    attachment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = db.query(Attachment).filter_by(id=attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # ownership + draft lock (via item -> report)
    item = db.query(ExpenseItem).filter_by(id=attachment.expense_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense item not found")

    report = db.query(ExpenseReport).filter_by(id=item.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Expense report not found")

    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "status": attachment.ocr_status,
        "data": attachment.ocr_json,
        "error": attachment.ocr_error,
    }



@router.get(
    "/{attachment_id}/file",
    dependencies=[Depends(require_roles([ROLE_EMPLOYEE]))],
)
def get_attachment_file(
    attachment_id: str,
    inline: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = db.query(Attachment).filter_by(id=attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    item = db.query(ExpenseItem).filter_by(id=attachment.expense_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense item not found")

    report = db.query(ExpenseReport).filter_by(id=item.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Expense report not found")

    # ownership check
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not attachment.file_path or not os.path.exists(attachment.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    media_type, _ = guess_type(attachment.filename)
    media_type = media_type or "application/octet-stream"

    return FileResponse(
        path=attachment.file_path,
        media_type=media_type,
        filename=attachment.filename,
        headers={
            "Content-Disposition": (
                f'inline; filename="{attachment.filename}"'
                if inline
                else f'attachment; filename="{attachment.filename}"'
            )
        },
    )
# -------------------------------------------------------------------
# DELETE ATTACHMENT
# DELETE /api/attachments/{attachment_id}
# -------------------------------------------------------------------

@router.delete(
    "/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles([ROLE_EMPLOYEE]))],
)
def delete_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = db.query(Attachment).filter_by(id=attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    item = db.query(ExpenseItem).filter_by(id=attachment.expense_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Expense item not found")

    report = db.query(ExpenseReport).filter_by(id=item.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Expense report not found")

    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if report.status != ExpenseReportStatus.draft:
        raise HTTPException(status_code=403, detail="Expense report is locked")

    # delete file from disk (optional safe cleanup)
    try:
        if attachment.file_path and os.path.exists(attachment.file_path):
            os.remove(attachment.file_path)
    except Exception:
        pass

    db.delete(attachment)
    db.commit()
    db.refresh(item)
    return None
