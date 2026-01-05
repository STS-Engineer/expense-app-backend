# app/services/currency_service.py
import requests
from datetime import date
from functools import lru_cache

FX_URL = "https://open.er-api.com/v6/latest/EUR"

SUPPORTED = {"EUR", "USD", "TND", "CNY", "KRW", "INR"}


@lru_cache(maxsize=1)
def _get_rates():
    resp = requests.get(FX_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("result") != "success":
        raise RuntimeError("FX API error")

    return data["rates"]


def convert_to_eur(amount: float, currency: str, conversion_date: date):
    currency = currency.upper()

    if currency not in SUPPORTED:
        raise ValueError(f"Unsupported currency: {currency}")

    rates = _get_rates()

    if currency == "EUR":
        return round(amount, 2), 1.0

    if currency not in rates:
        raise ValueError(f"No FX rate for {currency}")

    rate = rates[currency]

    eur_amount = round(amount / rate, 2)
    eur_rate = round(1 / rate, 6)

    return eur_amount, eur_rate
