# app/ocr/service.py
from pathlib import Path
from app.ocr.paddle import init_ocr, pdf_to_images, run_ocr
from app.ocr.groq_llm import parse_receipt_with_llm

_ocr_instance = None


def extract_receipt(file_path: str) -> dict:
    global _ocr_instance

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(file_path)

    if _ocr_instance is None:
        _ocr_instance = init_ocr(lang="fr")

    texts = []

    if path.suffix.lower() == ".pdf":
        pages = pdf_to_images(path)
        for p in pages:
            t = run_ocr(_ocr_instance, p)
            if t:
                texts.append(t)
    else:
        t = run_ocr(_ocr_instance, path)
        if t:
            texts.append(t)

    ocr_text = "\n\n".join(texts).strip()
    if not ocr_text:
        raise RuntimeError("OCR produced empty text")

    parsed = parse_receipt_with_llm(ocr_text)

    return {
        "ocr_text": ocr_text,
        "ocr_json": parsed,
    }
