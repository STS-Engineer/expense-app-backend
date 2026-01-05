# app/ocr/groq_llm.py
import os, json, re
from groq import Groq
from app.ocr.schemas import ReceiptData

SYSTEM_PROMPT = """Tu es un interprète de justificatifs de dépense destiné à un système de validation comptable en production.

Le document analysé peut être :
- un reçu
- une facture
- un ticket
- un écran de terminal de paiement
- une confirmation de paiement

🎯 OBJECTIF PRINCIPAL
Identifier et expliquer de manière claire et professionnelle :
- le montant payé
- la devise
- le type de dépense
- le contexte de paiement

Le résultat sera présenté à un responsable hiérarchique pour validation.

---

🧠 RÈGLES DE RAISONNEMENT (IMPORTANT)

Tu es AUTORISÉ à interpréter le document à partir :
- du contexte global
- des symboles monétaires (€ $ etc.)
- du format des montants (ex : 6,50 = 6.50)
- du vocabulaire de paiement (DEBIT, CREDIT, PAYÉ, APPROUVÉ, etc.)
- de la structure visuelle implicite (terminal, facture, ticket)

Si un seul montant est clairement visible sur un document de paiement,
alors ce montant correspond au total payé.

---

📌 RÈGLES DE FIABILITÉ

- N’invente jamais un montant absent
- N’invente jamais une devise absente
- Si une information est incertaine, indique-le explicitement
- N’utilise JAMAIS le texte OCR brut dans la sortie
- N’expose JAMAIS de raisonnement technique ou d’hypothèses internes

---

📤 FORMAT DE SORTIE (STRICT)

Tu dois produire UNIQUEMENT un JSON valide conforme EXACTEMENT à ce schéma :

{
  "document_type": string | null,
  "expense_category": string | null,
  "merchant_name": string | null,
  "date": string | null,

  "currency": string | null,
  "total": number | null,

  "payment_method": string | null,

  "explanation": string | null,
  "confidence_level": "high" | "medium" | "low"
}

Aucun texte hors JSON.
Aucun champ supplémentaire.

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


def parse_receipt_with_llm(
    ocr_text: str,
    model: str = "llama-3.3-70b-versatile"
) -> dict:
    client = get_groq_client()

    user_prompt = f"""
Texte OCR du justificatif :

{ocr_text}

Interprète ce document comme un justificatif de dépense professionnelle
et retourne uniquement le JSON demandé.
"""

    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = resp.choices[0].message.content
    data = json.loads(_extract_json_str(content))
    return data
