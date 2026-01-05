from fastapi import APIRouter

from app.core.constants import (
    PLANTS,
    DEPARTMENTS,
    EXPENSE_TOPICS,
    EXPENSE_TYPES,
    CURRENCIES,
    PAYMENT_TYPES,
)

router = APIRouter(prefix="/reference-data", tags=["Reference Data"])


@router.get("")
def get_reference_data():
    return {
        "plants": PLANTS,
        "departments": DEPARTMENTS,
        "expense_topics": EXPENSE_TOPICS,
        "expense_types": EXPENSE_TYPES,
        "currencies": CURRENCIES,
        "payment_types": PAYMENT_TYPES,
    }
