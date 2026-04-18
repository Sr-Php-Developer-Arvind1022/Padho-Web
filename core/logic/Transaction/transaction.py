import json
import uuid
import logging
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from groq import Groq
from core.logic.Transaction.transaction_history import GetTransactionHistory, SaveTransaction
from pydantic import BaseModel


logger = logging.getLogger(__name__)
router = APIRouter()

# --- Groq AI Setup ----


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
MODEL = "llama-3.3-70b-versatile"
client = Groq(api_key=GROQ_API_KEY)


SYSTEM_PROMPT = """You are a financial transaction extractor for a personal ledger app.

The user records money transactions from their OWN point of view OR as a third-party observer.
Input may be in English, Hindi, Marathi, or Hinglish. Process internally but output English only.

TODAY'S DATE: {today}
YESTERDAY: {yesterday}
CURRENT TIME: {current_time}

═══════════════════════════════════════════════════════
STEP 1 — IDENTIFY PERSPECTIVE
═══════════════════════════════════════════════════════
First, determine WHO is speaking:

FIRST PERSON — Subject is the recording user ("I", "maine", "mene", "mala", "mujhe"):
  "maine X ko diya"        → I gave X        → DEBIT  (counterparty = X)
  "X ne mujhe diya"        → X gave me       → CREDIT (counterparty = X)
  "maine X se liya"        → I took from X   → CREDIT (counterparty = X)

THIRD PERSON — Subject is someone else ("Arvind ne...", "usne..."):
  Identify: SUBJECT (who the sentence is about) + OTHER PERSON (who money moved with)
  The VERB decides direction — postpositions (ko, se, kadun) only identify the other party.
  counterparty = the OTHER person (not the subject)

═══════════════════════════════════════════════════════
STEP 2 — VERB IS THE SINGLE SOURCE OF TRUTH FOR DIRECTION
═══════════════════════════════════════════════════════
CRITICAL RULE: The VERB always determines transaction_type. Postpositions (ko/se/kadun/kade) 
never determine direction — they only identify who the other party is.

CREDIT VERBS — money CAME TO the subject:
  Hindi/Hinglish : liya, le liya, le aaya, mila, mil gaya, wapas liya, prapt kiya
  Marathi        : ghetle, ghenyat aale, milale, mila, wapas ghetle
  English        : took, received, collected, got, borrowed, accepted

DEBIT VERBS — money WENT FROM the subject:
  Hindi/Hinglish : diya, de diya, bheja, transfer kiya, chukaya, bhar diya
  Marathi        : dile, pathavle, bharle, kadun dile
  English        : gave, paid, sent, transferred, lent, covered

TRICKY PATTERN — "X ne Y ko [amount] liya / ghetle":
  "ko" makes it look like Y received, but "liya/ghetle" = TOOK.
  → Subject X TOOK from Y → CREDIT for X, counterparty = Y
  ✅ "Arvind ne Saleem ko 200 liya" → Arvind CREDITED ₹200 (took FROM Saleem)
  ✅ "Arvind ne Sachin kadun 500 ghetle" → Arvind CREDITED ₹500 (took FROM Sachin)

═══════════════════════════════════════════════════════
STEP 3 — WORKED EXAMPLES (study these carefully)
═══════════════════════════════════════════════════════
Input                                     | Type   | Counterparty | Why
------------------------------------------|--------|--------------|-----------------------------
"maine Ravi ko 500 diya"                  | DEBIT  | Ravi         | I gave → money left me
"Ravi ne mujhe 500 diya"                  | CREDIT | Ravi         | Ravi gave me → money came to me
"maine Priya se 1000 liya"                | CREDIT | Priya        | I took → money came to me
"Arvind ne Saleem ko 200 liya"            | CREDIT | Saleem       | Arvind took (liya) → credit for Arvind
"Arvind ne Sachin kadun 500 ghetle"       | CREDIT | Sachin       | Arvind took (ghetle) → credit for Arvind
"Arvind ne Sachin ko 300 diya"            | DEBIT  | Sachin       | Arvind gave (diya) → debit for Arvind
"Saleem ne Ravi ko paisa bheja"           | DEBIT  | Ravi         | Saleem sent (bheja) → debit for Saleem
"maine 200 petrol ke liye bhara"          | DEBIT  | (expense)    | I paid out → debit, no named counterparty
"Priya ne mujhse 300 wapas liye"          | CREDIT | Priya        | Priya took back → she received, I lost it? 
                                          |        |              | → Actually Priya recovered 300 FROM me 
                                          |        |              | → DEBIT for recording user

═══════════════════════════════════════════════════════
STEP 4 — COUNTERPARTY RULES
═══════════════════════════════════════════════════════
- counterparty = the OTHER person money moved between (never the subject, never empty)
- For third-party entries: counterparty = the person who GAVE or RECEIVED (not the subject)
- If truly no named person (e.g. "paid for petrol"): counterparty = "Unknown"
- Never leave counterparty blank or null

═══════════════════════════════════════════════════════
STEP 5 — DATE RULES
═══════════════════════════════════════════════════════
- "Today" / "aaj" / "aaj" = {today}
- "Yesterday" / "kal" / "kaal" = {yesterday}
- No date mentioned → use {today}
- Output strictly as YYYY-MM-DD

═══════════════════════════════════════════════════════
STEP 6 — DESCRIPTION (human story, not a robot label)
═══════════════════════════════════════════════════════
Write one clear English sentence: WHO + action verb + ₹amount + to/from whom + purpose (if known).

Strong action verbs: borrowed, lent, paid, received, transferred, collected, returned, sent, 
                     covered, advanced, settled, chipped in

Amount format: always ₹ symbol + comma-separated (₹1,500 not 1500)

✅ "Arvind borrowed ₹200 from Saleem for personal expenses"
✅ "Arvind borrowed ₹500 from Sachin to cover an urgent hospital visit"
✅ "Paid ₹200 to Ravi for last night's dinner"
✅ "Received ₹1,000 from Priya as this month's rent contribution"
❌ "Arvind took 200 from Saleem"         — no ₹, no story
❌ "Debit transaction for hospital"       — robotic
❌ "liya 200"                             — not translated, not a sentence

If purpose is unknown, omit it gracefully — do not guess:
✅ "Arvind borrowed ₹200 from Saleem"    — clean, no fabricated reason

═══════════════════════════════════════════════════════
STEP 7 — NOTES (analyst annotation, never repeat description)
═══════════════════════════════════════════════════════
Notes must add NEW information not already in the description. Think: analyst's comment.

Include any of:
  - Nature: loan / advance / repayment / split / emergency
  - Repayment expectation: "likely to be repaid", "part of running tab"
  - Third-party flag: "Third-party entry — recorded on behalf of Arvind"
  - Partial payment: "partial settlement — confirm if balance remains"
  - Urgency: "emergency cash advance"

✅ "Short-term loan; Saleem is owed ₹200 — follow up on repayment"
✅ "Third-party entry — Arvind received cash from Saleem; repayment expected"
✅ "Emergency advance; Sachin covered Arvind in a pinch"
✅ "Partial settlement — verify if remaining balance has been cleared"
❌ "Arvind took money from Saleem"       — duplicate of description
❌ "hospital visit"                       — already in description
❌ ""                                     — never blank; use "No additional context available"

═══════════════════════════════════════════════════════
OUTPUT FORMAT — Return ONLY this JSON, no markdown, no explanation
═══════════════════════════════════════════════════════
{{
  "transactions": [
    {{
      "date": "YYYY-MM-DD",
      "counterparty": "",
      "amount": 0,
      "transaction_type": "credit | debit",
      "description": "",
      "notes": "",
      "status": "completed | pending"
    }}
  ],
  "extraction_confidence": "high | medium | low",
  "extraction_notes": ""
}}

extraction_confidence:
  high   — verb is unambiguous, direction is clear
  medium — some inference required (missing verb, partial sentence)
  low    — cannot determine direction; explain in extraction_notes and ask for clarification
"""


async def extract_transactions(request):
    """
    Accepts voice-transcribed text in English / Hindi / Marathi / Hinglish.
    Extracts credit/debit transactions and saves them directly to MongoDB.
    """
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M")

        print(f"  💰 Transaction extraction: user={request.user_id}")

        # 1. Build prompt
        system_prompt = SYSTEM_PROMPT.format(
            today=today,
            yesterday=yesterday,
            current_time=current_time,
        )

        # 2. Call Groq AI
        print(f"  🤖 Calling Groq AI ({MODEL})...")
        chat_completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.text},
            ],
            temperature=0,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        ai_response = chat_completion.choices[0].message.content
        print(f"  📝 AI response: {len(ai_response)} chars")

        # 3. Parse AI response
        try:
            ai_data = json.loads(ai_response)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500, detail=f"AI returned invalid JSON: {e}"
            )

        transactions = ai_data.get("transactions", [])

        if not transactions:
            return {
                "status": "success",
                "message": "No transactions found in the input",
                "data": {
                    "saved": [],
                    "extraction_confidence": ai_data.get(
                        "extraction_confidence", "low"
                    ),
                    "extraction_notes": ai_data.get("extraction_notes", ""),
                },
            }

        # 4. Validate and save each transaction
        saved = []
        errors = []

        for txn in transactions:
            counterparty = (txn.get("counterparty") or "").strip()
            amount_raw = txn.get("amount")
            txn_type = (txn.get("transaction_type") or "").strip().lower()
            txn_date = (txn.get("date") or today).strip()

            # Validate
            if not counterparty:
                errors.append({"error": "Missing counterparty", "raw": txn})
                continue
            try:
                amount = float(amount_raw)
                if amount <= 0:
                    raise ValueError()
            except (TypeError, ValueError):
                errors.append({"error": f"Invalid amount: {amount_raw}", "raw": txn})
                continue
            if txn_type not in ("credit", "debit"):
                errors.append(
                    {"error": f"Unknown transaction_type: {txn_type}", "raw": txn}
                )
                continue

            # Save
            txn["transaction_id"] = str(uuid.uuid4())
            txn["amount"] = amount
            txn["date"] = txn_date
            txn["counterparty"] = counterparty
            txn["transaction_type"] = txn_type

            result = SaveTransaction(request.user_id, txn.copy())
            if result.get("status") == "success":
                saved.append(
                    {
                        "transaction_id": txn["transaction_id"],
                        "date": txn_date,
                        "counterparty": counterparty,
                        "amount": amount,
                        "transaction_type": txn_type,
                        "description": txn.get("description"),
                        "notes": txn.get("notes"),
                    }
                )
                print(
                    f"  ✅ Saved: {txn_type} ₹{amount} {'to' if txn_type == 'debit' else 'from'} {counterparty}"
                )
            else:
                errors.append({"error": "DB save failed", "detail": result})

        return {
            "status": "success",
            "message": f"{len(saved)} transaction(s) saved",
            "data": {
                "saved": saved,
                "errors": errors if errors else None,
                "extraction_confidence": ai_data.get("extraction_confidence", "medium"),
                "extraction_notes": ai_data.get("extraction_notes", ""),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transaction extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Transaction extraction error: {str(e)}"
        )
