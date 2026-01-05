from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine
from app.db.base import Base

from app.api.auth import router as auth_router
from app.api.expense_reports import router as expense_reports_router
from app.api.expense_items import router as expense_items_router
from app.api.attachments import router as attachments_router
from app.api.reference_data import router as reference_data_router
from app.api.responsible import router as responsible_router

app = FastAPI(title="Expense Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DEV ONLY
Base.metadata.create_all(bind=engine)

# ROUTERS
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(expense_reports_router, prefix="/api/expense-reports", tags=["expense-reports"])
app.include_router(expense_items_router, prefix="/api", tags=["expense-items"])
app.include_router(attachments_router, prefix="/api/attachments", tags=["attachments"])
app.include_router(reference_data_router, prefix="/api", tags=["reference-data"])

# ✅ RESPONSIBLE (ONLY ONCE)
app.include_router(responsible_router)

@app.get("/api/health")
def health():
    return {"status": "ok"}
