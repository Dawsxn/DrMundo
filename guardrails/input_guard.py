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
Follow-up fragments like "and at Chong Hua?" or "how about an MRI?" are "cost".
- "medical_advice": asking for clinical/medical guidance - symptoms, diagnosis, whether to \
undergo a procedure, medications, what treatment to get, is it safe, etc.
- "out_of_scope": anything else, including HMO/private insurance, PhilHealth eligibility/\
policy/membership questions, and unrelated topics.

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


def check_input(text: str) -> InputVerdict:
    clean_text, pii_found = redact(text or "")

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
