from datetime import date
from typing import Optional
from fastapi import HTTPException

from app.services.currency_service import convert_to_eur


def resolve_amount(
    amount: Optional[float],
    currency: Optional[str],
    source: str,
    conversion_date: date,
):
    if amount is None or currency is None:
        return None

    try:
        eur, rate = convert_to_eur(amount, currency, conversion_date)
    except ValueError as e:
        # ❌ never crash submit
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "amount": amount,
        "currency": currency.upper(),
        "amount_eur": eur,
        "exchange_rate": rate,
        "exchange_rate_date": conversion_date,
        "amount_source": source,
    }
