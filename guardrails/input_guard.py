"""Input guardrail: redact PII, then restrict the topic.

Allowed: questions about the COST of Philippine medical procedures / outpatient services,
PhilHealth case-rate coverage, and out-of-pocket estimates.
Refused (status=out_of_scope):
  - medical / clinical / diagnostic / treatment advice ("should I get surgery?", symptoms)
  - anything unrelated, plus HMO / private insurance and PhilHealth policy/eligibility.

Topic classification uses a single cheap gpt-4o-mini call returning strict JSON. PII
redaction is deterministic regex and happens first, so raw PII never hits the classifier.
"""

import json
from dataclasses import dataclass

from config import CHAT_MODEL, get_openai_client
from guardrails.pii import redact

_CLASSIFIER_SYSTEM = """You are a strict input classifier for "Dr. Mundo", a Philippine \
medical-COST assistant. Classify the user's message into exactly one category:

- "cost": asking about the price/cost of a medical procedure or outpatient service in the \
Philippines, PhilHealth case-rate coverage, or out-of-pocket estimates. Taglish is fine. \
Follow-up fragments like "and at Chong Hua?" or "how about an MRI?" are "cost". This ALSO \
includes the user telling us about their HMO plan, provider or remaining benefit balance, \
and answering our questions about senior citizen / PWD status -- those are inputs to a \
cost estimate, not a separate topic.
- "medical_advice": asking for clinical/medical guidance - symptoms, diagnosis, whether to \
undergo a procedure, medications, what treatment to get, is it safe, etc.
- "out_of_scope": anything else, including PhilHealth eligibility/policy/membership \
questions, HMO policy or claims disputes, and unrelated topics.

Respond with ONLY JSON: {"category": "cost|medical_advice|out_of_scope", "reason": "..."}."""

_REFUSALS = {
    "medical_advice": (
        "I can only help with the *cost* of procedures and services -- I can't give "
        "medical or clinical advice. Please consult a licensed physician for that. "
        "I'd be glad to estimate the cost of a procedure, though."
    ),
    "out_of_scope": (
        "I can only help with the cost of medical procedures and outpatient services in "
        "the Philippines (including PhilHealth case rates and out-of-pocket estimates). "
        "I can't help with that topic."
    ),
}


@dataclass
class InputVerdict:
    allowed: bool
    category: str            # "cost" | "medical_advice" | "out_of_scope"
    clean_text: str          # PII-redacted text to feed downstream
    pii_found: list[str]
    refusal_message: str | None = None


def check_input(
    text: str,
    has_attachment: bool = False,
    attachment_pii: list[str] | None = None,
) -> InputVerdict:
    """Redact, then classify. `has_attachment` short-circuits the topic classifier.

    An uploaded request slip with no caption hands the classifier an empty string, which
    it cannot meaningfully categorise -- and a refusal there would block the app's own
    primary flow. An attachment IS the question, so it is allowed through; the document
    itself is still checked downstream (Phase 5 rejects non-medical images).

    `attachment_pii` carries labels from RASTER redaction, which is a separate mechanism
    from the text regexes below -- a name burned into pixels is invisible to them. Merging
    it here keeps every redaction visible in one place, including MLflow.
    """
    clean_text, pii_found = redact(text or "")
    if attachment_pii:
        pii_found = sorted(set(pii_found) | set(attachment_pii))

    # No text to classify. Refusing here would reject a bare slip upload.
    if not clean_text.strip():
        if has_attachment:
            return InputVerdict(True, "cost", clean_text, pii_found)
        return InputVerdict(
            False, "out_of_scope", clean_text, pii_found,
            "I didn't get a question. Ask me what something costs, or upload a photo of "
            "your doctor's request.",
        )

    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _CLASSIFIER_SYSTEM},
                {"role": "user", "content": clean_text},
            ],
        )
        category = json.loads(resp.choices[0].message.content).get("category", "cost")
    except Exception:
        # Fail open to "cost" so a classifier hiccup doesn't block a legitimate question;
        # the downstream honesty rules + output guard still constrain the answer.
        category = "cost"

    if category not in ("cost", "medical_advice", "out_of_scope"):
        category = "cost"

    if category == "cost":
        return InputVerdict(True, category, clean_text, pii_found)
    return InputVerdict(False, category, clean_text, pii_found, _REFUSALS[category])
