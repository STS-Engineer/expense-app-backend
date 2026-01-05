# app/ocr/groq_llm.py
import os, json, re
from groq import Groq
from app.ocr.schemas import ReceiptData

SYSTEM_PROMPT = """Tu es un extracteur universel de justificatifs de dépense.

À partir du texte OCR fourni, tu dois extraire les informations financières
principales d’un justificatif (reçu, facture, ticket, email de paiement).

⚠️ Tu dois renvoyer UNIQUEMENT un JSON valide conforme exactement à ce schéma :

{
  "document_type": string|null,
  "merchant_name": string|null,
  "merchant_address": string|null,
  "merchant_country": string|null,
  "document_id": string|null,
  "date": string|null,
  "time": string|null,

  "currency": string|null,
  "total": number|null,

  "eur_rate_hint": number|null,
  "eur_estimate": number|null,

  "payment_method": string|null,
  "payment_status": string|null,

  "confidence_notes": string|null,
  "raw_notes": string|null
}

🎯 OBJECTIF
- Identifier le montant total payé et sa devise.
- Fournir une estimation du montant en EUR lorsque la devise n’est pas EUR.

📌 RÈGLES IMPORTANTES (FX)
- Si currency ≠ EUR :
  - FOURNIS le taux de change EUR du jour (eur_rate_hint)
  - CALCULE une estimation du total en EUR (eur_estimate)
- L’estimation peut être approximative mais DOIT être fournie
- Utilise les taux de change courants connus (ordre de grandeur correct)
- Si vraiment impossible → mets null (cas très rare)

📌 AUTRES RÈGLES
- Ne jamais inventer un montant total
- Les montants doivent être des NOMBRES
- Ignore les détails inutiles (timbres, taxes locales, lignes secondaires)
- Ne produis aucun texte hors du JSON

❌ INTERDIT
- Markdown
- Commentaires
- Texte hors JSON
"""



def _extract_json_str(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("{") and s.endswith("}"):
        return s
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        raise ValueError("LLM response does not contain JSON.")
    return m.group(0)


def get_groq_client() -> Groq:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("Missing GROQ_API_KEY")
    return Groq(api_key=key)


def parse_receipt_with_llm(ocr_text: str, model: str = "llama-3.3-70b-versatile") -> dict:
    client = get_groq_client()

    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Texte OCR:\n{ocr_text}\n\nRenvoie le JSON du reçu."},
        ],
    )

    content = resp.choices[0].message.content
    data = json.loads(_extract_json_str(content))
    receipt = ReceiptData.model_validate(data)
    return receipt.model_dump()
