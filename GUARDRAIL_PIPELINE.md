# Dr. Mundo Guardrail Pipeline Flowchart & Example

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUT                              │
│              "How much is a CT scan at Chong Hua?"              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              INPUT GUARDRAIL: PII DETECTION                      │
│  • Regex scan: EMAIL, PHONE, PHILHEALTH_ID, CARD               │
│  • Redact found patterns                                         │
│  • Return (clean_text, pii_found_list)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           INPUT GUARDRAIL: TOPIC CLASSIFICATION                 │
│  • LLM checks: Is this a COST question?                         │
│  • Categories: "cost" ✓ | "medical_advice" ✗ | "out_of_scope" ✗│
│  • If not cost → Refuse & return                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  AGENT PROCESSING                               │
│  1. search_catalog() → Find procedure/service                   │
│  2. get_covered_cost() OR get_outpatient_cost() → Get data      │
│  3. Generate prose answer with numbers                          │
│  4. Build Answer object (structured fields + text)              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│          OUTPUT GUARDRAIL 1: GROUNDING CHECK                     │
│  • Extract numbers from structured Answer fields                │
│  • Extract numbers from prose text                              │
│  • Verify: prose_numbers ⊆ structured_numbers                   │
│  • If violation → Rebuild prose from structured fields only     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│        OUTPUT GUARDRAIL 2: NOT-COVERED NOTE (Outpatient)         │
│  • If answer.path == "outpatient"                               │
│  • Check prose for "not covered" or "philhealth"                │
│  • If missing → Append safety note                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         OUTPUT GUARDRAIL 3: DISCLAIMER                           │
│  • Check if DISCLAIMER text is in answer                        │
│  • If missing → Append mandatory disclaimer                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│        MEMORY GUARDRAIL: STORE REDACTED TEXT                     │
│  • Take clean_text (from PII redaction)                         │
│  • Store in session memory (ephemeral, in-memory only)          │
│  • Never persist raw PII                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RETURN TO USER                               │
│          (Full answer with all guardrails enforced)             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Full End-to-End Example

### Step 1: User Input
```
User Input: "Hi, my email is john.doe@gmail.com. How much is a CT scan at Chong Hua?"
```

### Step 2: PII Redaction (Input Guardrail #1)

**File:** `guardrails/pii.py`

```python
from guardrails.pii import redact

raw_input = "Hi, my email is john.doe@gmail.com. How much is a CT scan at Chong Hua?"
clean_text, pii_found = redact(raw_input)

# clean_text = "Hi, my email is [REDACTED]. How much is a CT scan at Chong Hua?"
# pii_found = ["EMAIL"]
```

### Step 3: Topic Classification (Input Guardrail #2)

**File:** `guardrails/input_guard.py`

```python
from guardrails.input_guard import check_input

verdict = check_input(clean_text)
# verdict = InputVerdict(
#     allowed=True,
#     category="cost",
#     clean_text="Hi, my email is [REDACTED]. How much is a CT scan at Chong Hua?",
#     pii_found=["EMAIL"]
# )

if not verdict.allowed:
    # Short-circuit: refuse to answer
    return Answer(status="refused", answer_text=f"I can only help with cost questions. {DISCLAIMER}")
```

### Step 4: Agent Processing

**File:** `agent/loop.py`

```python
# Agent receives clean_text, calls tools:

# Tool 1: Search catalog
candidates = search_catalog("CT scan")
# Result: [
#   {"name": "CT Scan - Head", "rvs_code": "70450", "kind": "outpatient"},
#   {"name": "CT Scan - Abdomen", "rvs_code": "74150", "kind": "outpatient"}
# ]

# Agent picks top match (Head) and asks for hospital
hospital = "Chong Hua"

# Tool 2: Get outpatient cost
result = get_outpatient_cost(service="CT Scan - Head", hospital="Chong Hua")
# Result: {
#   "price_low": 8500,
#   "price_high": 12000,
#   "as_of": 2025
# }

# Agent writes prose
prose = "A CT scan of the head at Chong Hua costs ₱8,500 to ₱12,000."

# Build Answer object
answer = Answer(
    status="answered",
    path="outpatient",
    price_low=8500,
    price_high=12000,
    oop_low=None,
    oop_high=None,
    case_rate=None,
    hospitals=None,
    as_of=2025,
    answer_text=prose
)
```

### Step 5: Grounding Check (Output Guardrail #1)

**File:** `guardrails/output_guard.py`

```python
from guardrails.output_guard import _grounded_values, _money_amounts

# Extract grounded numbers (from Answer structured fields)
grounded = _grounded_values(answer)
# grounded = {8500, 12000, 2025}

# Extract numbers mentioned in prose
mentioned = _money_amounts(answer.answer_text)
# mentioned = {8500, 12000}

# Check for violations
ungrounded = mentioned - grounded
# ungrounded = {} (empty → all numbers are grounded ✓)

if ungrounded:
    # Would rebuild prose, but not needed here
    report.grounded = False
    report.violations = list(ungrounded)
```

### Step 6: Not-Covered Note (Output Guardrail #2)

**File:** `guardrails/output_guard.py`

```python
# Check if outpatient
if answer.path == "outpatient":
    low = answer.answer_text.lower()
    if "not covered" not in low and "philhealth" not in low:
        # Add not-covered note
        answer.answer_text += "\n\nNote: this outpatient service is not covered by PhilHealth."
        report.notes.append("Added not-covered note.")

# Updated answer_text:
# "A CT scan of the head at Chong Hua costs ₱8,500 to ₱12,000.
#
# Note: this outpatient service is not covered by PhilHealth."
```

### Step 7: Disclaimer (Output Guardrail #3)

**File:** `guardrails/output_guard.py` + `agent/format.py`

```python
from agent.format import DISCLAIMER

DISCLAIMER = "Estimates only — not medical or financial advice. Price ranges are indicative and may exclude professional fees, medicines, and room charges."

# Check if disclaimer present
if DISCLAIMER not in answer.answer_text:
    answer.answer_text = f"{answer.answer_text.rstrip()}\n\n{DISCLAIMER}"
    report.notes.append("Appended disclaimer.")

# Final answer_text:
# "A CT scan of the head at Chong Hua costs ₱8,500 to ₱12,000.
#
# Note: this outpatient service is not covered by PhilHealth.
#
# Estimates only — not medical or financial advice. Price ranges are indicative and may
# exclude professional fees, medicines, and room charges."
```

### Step 8: Memory Storage (Memory Guardrail)

**File:** `agent/service.py` + `agent/memory.py`

```python
from agent.memory import SessionMemory

session_memory = SessionMemory(session_id="user_123")

# Store cleaned input (PII redacted)
session_memory.add_user(clean_text)  # ← NOT raw_input
# Stored: "Hi, my email is [REDACTED]. How much is a CT scan at Chong Hua?"

# Store final answer
session_memory.add_assistant(answer.answer_text)

# Memory never persists to disk; ephemeral only
print(session_memory.history())
# [
#   ("user", "Hi, my email is [REDACTED]. How much is a CT scan at Chong Hua?"),
#   ("assistant", "A CT scan... [full answer with all guardrails]")
# ]
```

### Step 9: Return to User

```json
{
  "status": "answered",
  "path": "outpatient",
  "answer_text": "A CT scan of the head at Chong Hua costs ₱8,500 to ₱12,000.\n\nNote: this outpatient service is not covered by PhilHealth.\n\nEstimates only — not medical or financial advice. Price ranges are indicative and may exclude professional fees, medicines, and room charges."
}
```

---

## Violation Example: Grounding Check Catches Hallucination

Suppose the agent had hallucinated:

```python
# Agent prose (with hallucination):
prose = "A CT scan at Chong Hua costs ₱8,500 to ₱12,000. Typically takes 2 hours and costs ₱15,000 total."

answer = Answer(
    status="answered",
    path="outpatient",
    price_low=8500,
    price_high=12000,
    answer_text=prose
)
```

**Grounding check catches it:**

```python
grounded = _grounded_values(answer)
# grounded = {8500, 12000, 2025}

mentioned = _money_amounts(answer.answer_text)
# mentioned = {8500, 12000, 15000}  ← ₱15,000 NOT in grounded!

ungrounded = mentioned - grounded
# ungrounded = {15000}

if ungrounded:
    report.grounded = False
    report.violations = [15000.0]
    # Rebuild prose from structured fields ONLY
    answer.answer_text = format_answer(answer)
    # Result: "A CT scan of the head at Chong Hua costs ₱8,500 to ₱12,000."
    # ↑ ₱15,000 is stripped out (hallucination removed)
```

---

## Summary Table

| Guardrail | Type | When | Location | Visible? |
|-----------|------|------|----------|----------|
| PII Redaction | Input | Before agent sees input | `guardrails/pii.py` | No (silent) |
| Topic Classification | Input | Before agent processes | `guardrails/input_guard.py` | Yes (refusal) |
| Grounding Check | Output | After agent writes prose | `guardrails/output_guard.py` | No (silent) |
| Not-Covered Note | Output | After agent answers outpatient | `guardrails/output_guard.py` | Yes (appended) |
| Disclaimer | Output | Final answer assembly | `guardrails/output_guard.py` | Yes (always) |
| Redacted Memory Storage | Memory | After user/assistant exchange | `agent/memory.py` | No (internal) |
