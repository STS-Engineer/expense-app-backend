# app/ocr/paddle.py
from pathlib import Path
import tempfile
from typing import Any, Dict, List

import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR


# -------------------------------------------------
# OCR INIT (same logic as your working project)
# -------------------------------------------------

def init_ocr(lang: str = "fr") -> PaddleOCR:
    return PaddleOCR(
        lang=lang,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=True,
    )


# -------------------------------------------------
# PDF → IMAGES (same as your project)
# -------------------------------------------------

def pdf_to_images(pdf_path: Path, dpi: int = 250) -> List[Path]:
    tmp = Path(tempfile.mkdtemp(prefix="receipt_pdf_"))
    doc = fitz.open(str(pdf_path))
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    out_paths: List[Path] = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        out = tmp / f"page_{i+1:03d}.png"
        img.save(out)
        out_paths.append(out)

    return out_paths


# -------------------------------------------------
# OCR RUN (ROBUST, VERSION-SAFE)
# -------------------------------------------------

def run_ocr(ocr: PaddleOCR, img_path: Path) -> str:
    result = ocr.predict(
        str(img_path),
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=True,
        return_word_box=False,
    )

    lines: List[str] = []

    for res in (result or []):
        # EXACT SAME LOGIC AS YOUR WORKING SCRIPT
        d = res.to_dict() if hasattr(res, "to_dict") else res
        if not isinstance(d, dict):
            continue

        payload = d.get("res", d)
        texts = payload.get("rec_texts") or []

        for txt in texts:
            if txt:
                lines.append(str(txt))

    return "\n".join(lines).strip()
