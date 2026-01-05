def build_ui_summary(llm_output: dict) -> dict | None:
    if not llm_output:
        return None

    title = llm_output.get("expense_category") or "Expense"
    merchant = llm_output.get("merchant_name")
    total = llm_output.get("total")
    currency = llm_output.get("currency")
    payment = llm_output.get("payment_method")
    explanation = llm_output.get("explanation")
    confidence = llm_output.get("confidence_level")

    amount_str = None
    if total is not None and currency:
        amount_str = f"{float(total):.2f} {currency}"

    return {
        "title": title,
        "merchant": merchant,
        "amount": amount_str,
        "explanation": explanation,
        "confidence": confidence,
    }
