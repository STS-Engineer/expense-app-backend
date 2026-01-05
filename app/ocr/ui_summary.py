def build_ui_summary(ocr_json: dict) -> dict | None:
    if not ocr_json:
        return None

    merchant = ocr_json.get("merchant_name")
    doc_type = ocr_json.get("document_type")
    total = ocr_json.get("total")
    currency = ocr_json.get("currency")

    summary = None
    if doc_type:
        dt = doc_type.lower()
        if "food" in dt or "restaurant" in dt or "meal" in dt:
            summary = "Food receipt – restaurant expense"
        elif "hotel" in dt:
            summary = "Hotel expense"
        elif "transport" in dt or "taxi" in dt or "uber" in dt:
            summary = "Transport expense"
        else:
            summary = f"{doc_type.capitalize()} expense"

    amount_str = None
    if total and currency:
        amount_str = f"{float(total):.2f} {currency}"

    return {
        "name": merchant,
        "summary": summary,
        "amount": amount_str,
    }
