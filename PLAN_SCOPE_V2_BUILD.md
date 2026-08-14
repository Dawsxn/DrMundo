# Dr. Mundo — Scope v2 build plan

> Companion to [`HANDOFF_SCOPE_V2_DATA.md`](HANDOFF_SCOPE_V2_DATA.md) (the dataset) and the
> Final Capstone spec. That handoff describes data that is *already built*. **This document
> describes code that does not exist yet.** It is written to be handed to an implementation
> agent in slices — each phase in §6 is a self-contained prompt.

---

## 0. Precedence

**The 2026-08-09 commits are authoritative.** Where anything below disagrees with them, they win
unless the disagreement is a genuine contradiction — those are enumerated in §2 and are the only
places a human decision is required.

| Authoritative | Commit |
|---|---|
| [`HANDOFF_SCOPE_V2_DATA.md`](HANDOFF_SCOPE_V2_DATA.md) | `771aa5d` |
| The dataset CSVs (`facility_rates`, `lab_panels`, `professional_fees`, prices, crosswalk) | `293ed5e` |
| [`GUARDRAIL_PIPELINE.md`](GUARDRAIL_PIPELINE.md), scraper, crosswalk builders | `9db6ab4` |

Subordinate where it conflicts: **everything from 2026-07-08** — the v1 app (`agent/`, `api/`,
`ui/`, `guardrails/`, `eval/`, `monitoring/`), [`HANDOFF.md`](HANDOFF.md), and
[`KICKOFF_PROMPT.md`](KICKOFF_PROMPT.md). That code stays and carries grade weight; it just
doesn't get to override a Scope v2 decision.

The adviser notes and the Final Capstone spec are *newer inputs*, not commits. They win only
where §2 says so explicitly.

### 0.1 Decisions locked 2026-08-14

| Decision | Ruling | Consequence |
|---|---|---|
| HMO document type | **Benefits letter / certificate**, not the membership card | Carries MBL and remaining balance ⇒ **W3 is numeric** and the thesis is fully answerable. `HMOPlan` (§4) stands as written. Harder to source — patients request these from the HMO, so budget effort for obtaining samples |
| HMO source | **Patient upload only.** No HMO table in `data/` | Handoff §7 wins outright (§2.3). `eval/fixtures/hmo_reference_plan.yaml` exists solely for reproducible evals and the demo fallback |
| Handwriting | **In scope**, printed and handwritten, **metrics reported separately** | Synthetic gives volume, real gives the honest denominator. A blended F1 is indefensible in Q&A |
| Slip corpus | **Mix of real (redacted) and synthetic** | See the stratification rule in §9 — this is the main threat to metric validity |
| Procedure on slip | **Mixed** — some slips name it, some are work-up only | The pipeline **must branch**: no procedure ⇒ PhilHealth leg never fires ⇒ report says so explicitly rather than showing ₱0 coverage |
| OCR runtime | **Local model**, no API vision in the primary path | No per-call cost and **no patient image leaves the box** — pairs with raster redaction into a real privacy story for the deck. Costs image size and CPU latency (§8) |

---

## 1. The thesis

> **Can an agent estimate the budget a patient needs to prepare, given only images of a
> doctor's request, accounting for both PhilHealth and HMO coverage?**

Everything below serves answering that with a number, not an opinion. §9 defines the metrics
that constitute the answer.

**Scope frame (adviser's, with one reframe — see §2.1):**

| | |
|---|---|
| Hospital | Makati Medical Center only |
| Input A | Photo/scan of a doctor's request — procedures, radiologic studies, blood tests |
| Input B | Photo/scan of an HMO card or certificate (optional) |
| Output | One-page budget report: *prepare ₱X – ₱Y* |
| Excluded from the total | Professional fees, room & board |

---

## 2. Genuine contradictions — resolve these before writing code

Under §0 the handoff wins by default. These are the four places where it *can't* just win,
because something outside it says otherwise. Everything not listed here follows the handoff
without further discussion.

### 2.1 "Limited to in-patient" contradicts the dataset — handoff wins

A PhilHealth case rate is **all-in for the admission** (handoff §5.4). If a patient is admitted
for a cholecystectomy, the labs drawn during that admission are already inside the ₱60,450. So
"in-patient only" + itemised lab pricing double-counts, and subtracting the case rate on top of
itemised labs understates the bill — the harmful direction.

But that isn't what a request slip is. A pre-operative request slip is **outpatient work-up
done before admission** — that's why the patient is holding it in the lobby rather than lying in
a ward. The scope is coherent once stated as:

> **Pre-admission outpatient work-up (the slip) + the in-patient procedure it prepares for.**

This is the reframe, and it costs nothing: the 1,586 lab/imaging/diagnostic rows price the slip,
the 51 case-rated procedures price the admission, and no row is used twice.

**Recommendation:** adopt the reframe; say it in one line on the report ("work-up billed
outpatient; the procedure is billed as an admission"). **Never** apply a case rate to a lab item.

### 2.2 "Exclude professional fees" — not actually a contradiction

Handoff §9 already decided this: *"Professional fees: keep them a separate line (owner's
decision)."* A separate line **is** exclusion from the total, so the adviser's instruction and the
handoff agree. The existing `DISCLAIMER` in `agent/format.py` already says the estimate *"may
exclude professional fees, medicines, and room charges"* — reuse it rather than inventing new
wording. No decision needed.

What *is* needed is an arithmetic guard. A PhilHealth case rate bundles a **facility share and a
professional-fee share**. If the gross excludes PF but you subtract the *whole* case rate, you
credit the patient with a PF benefit against a bill that never contained PF — same failure class
as the `price_basis='component'` bug the handoff guards in §5.4: the number looks fine and is
thousands out, in the direction that hurts. Cap the PhilHealth deduction at the facility gross;
never let a line go negative (§5, rule W4).

Consequence to accept: appendectomy has *neither* a package price (handoff §6.1) *nor* a PF line
in the total. It becomes an almost-empty answer. Drop it as a demo — use **laparoscopic
cholecystectomy** and **lipid profile**, exactly as handoff §6.1 recommends.

### 2.3 The HMO reference plan vs. "no number exists unless it was published" ← **the real one**

This is the only head-on contradiction. The adviser wants one standard public plan (e.g.
Medicard). Handoff §7 dropped exactly this, on the owner's call, because invented tiers can only
ever be wrong — and it is the sole reason the project can claim *every committed number traces to
a published source*.

Under §0, the handoff wins: **the upload is the feature, and there is no HMO table in `data/`.**
Patient's certificate → CV → extracted fields → waterfall. That is also where CV surface #2 lives,
so it earns its keep twice.

The adviser's ask still gets satisfied, but as a **test fixture, not a dataset**:

- Put it in **`eval/fixtures/hmo_reference_plan.yaml`**, not `data/`. The directory is the
  guarantee — nothing in `eval/fixtures/` can be mistaken for scraped MMC data.
- It serves as the deterministic seed for §9 (the eval numbers move between runs without a fixed
  plan) and as the demo fallback when nothing is uploaded.
- Carry `source:` and `is_illustrative: true`; the renderer **must** surface the flag as a
  footnote on any figure derived from it.
- No upload and no fixture ⇒ label the figure *"before any HMO"* (handoff §7), never imply HMO
  doesn't exist.

Never commit an extracted patient plan — it carries their name and policy number (handoff §7).

### 2.4 Senior/PWD ordering vs. PhilHealth does not commute

The handoff (§9) notes VAT-exemption and the 20% discount commute with each other
(`×1/1.12 ×0.80 = ×0.714286`). **They do not commute with the PhilHealth deduction:**

```
(G × 0.714286) − P     =  0.714286G − P            ← discount first
(G − P) × 0.714286     =  0.714286G − 0.714286P    ← PhilHealth first
```

On a ₱46,800 case rate the two differ by ~₱13,400. Practice is discount-first (the discount is
applied to the hospital's charges; PhilHealth is deducted from the discounted bill).

**Recommendation:** implement **discount → PhilHealth → HMO**, make it one named constant, unit-test
both forms, and print the assumption on the report. The bug that actually costs money is omitting
the VAT exemption and applying only the 20% — assert `0.714286`, not `0.80`, in a test.

### 2.5 The existing grounding guard will destroy the budget report

[`GUARDRAIL_PIPELINE.md`](GUARDRAIL_PIPELINE.md) is in the priority window, so its pipeline is
authoritative — and as built it is incompatible with a multi-item report. Three concrete breaks:

**a) Grounding check, flat vs. nested.** `_grounded_values(answer)` collects numbers from a *flat*
`Answer` (`price_low`, `price_high`, `oop_low`, `oop_high`, `case_rate`, `as_of`). A budget report
quotes a price range **per item** — `CBC ₱630–1,200 · Urinalysis ₱495–1,000 · …` — none of which
live in those scalar fields. Every one reads as ungrounded, and the guard's remedy is to *rebuild
the prose from structured fields only*, which silently deletes the itemisation and leaves a report
that looks fine and says almost nothing. **Fix:** extend `_grounded_values` to walk
`BudgetEstimate.priced[*]` (and `separate_lines`) in Phase 7, before the renderer exists.

**b) `path` is binary.** Output Guardrail 2 fires on `answer.path == "outpatient"` to append the
not-covered note. A budget report is *mixed* — outpatient work-up plus one case-rated procedure —
so a single `path` can't express it. **Fix:** make the not-covered note per-item, driven by
`PricedItem.case_rate is None`, and add `path="budget_report"`.

**c) PII redaction is text-only.** `guardrails/pii.py` regexes EMAIL / PHONE / PHILHEALTH_ID /
CARD out of *text*. The CV path introduces PII in **rasters** — patient name and policy number on
an HMO card, name and address on a request slip — which no text regex will ever see. Handoff §12's
raster redaction is therefore a **second, independent mechanism**, not a reuse of this one. Wire
its output into the same `pii_found` list so redactions stay visible in MLflow.

Also: topic classification runs on text and refuses non-cost input. An image upload with no
caption gives it an empty string. Decide what `check_input("")` does *with an attachment present*
before it refuses your own demo.

---

## 3. Module map

Everything under `agent/`, `db/`, `api/`, `ui/`, `guardrails/`, `monitoring/` stays. New work is
additive; the ReAct loop, memory, guardrails and MLflow wiring are the Phase 9–10 assets that
carry grade weight (handoff §11).

```
vision/                    ★ NEW — CV component (capstone #14)
  redact.py                raster redaction; runs before anything touches disk
  ocr.py                   the CV model, wrapped as a callable tool
  extract_request.py       OCR spans + LLM normalisation → RequestSlip
  extract_hmo.py           OCR spans + LLM normalisation → HMOPlan
  models/                  RRL candidates behind one interface (§8)

pricing/                   ★ NEW — pure Python, zero LLM, fully unit-testable
  waterfall.py             gross → discount → PhilHealth → HMO → prepare
  panels.py                panel vs. individual-components comparison
  rules.py                 price_basis guards, caps, the count invariant

report/                    ★ NEW
  render.py                one-page PDF
  templates/

db/queries.py              EXTEND — panels, professional fees, facility rates;
                           surface price_basis + confidence
agent/tools.py             EXTEND — new tools (§7)
guardrails/output_guard.py EXTEND — nested grounding, per-item not-covered note (§2.5a/b)
guardrails/pii.py          EXTEND — accept raster redaction results into pii_found (§2.5c)
eval/fixtures/             ★ NEW — hmo_reference_plan.yaml (§2.3), gold-set annotations
eval/                      EXTEND — gold set, metrics, LLM-as-judge (§9)
data/samples/              ★ gitignored BEFORE the first sample lands
```

---

## 4. Data contracts

These are the spine — write them first, and the rest of the phases become independent.

```python
# vision/schemas.py
class ExtractedItem(BaseModel):
    raw_text: str                  # verbatim, exactly as read from the slip
    normalized: str | None         # canonical guess; None if unreadable
    kind: Literal["procedure", "imaging", "lab", "unknown"]
    ocr_confidence: float          # from the CV model
    bbox: tuple[int, int, int, int] | None

class RequestSlip(BaseModel):
    items: list[ExtractedItem]
    image_sha256: str
    redacted: bool                 # validator: must be True

class HMOPlan(BaseModel):
    provider: str | None
    plan_name: str | None
    mbl_annual: Decimal | None     # maximum benefit limit
    remaining_balance: Decimal | None
    coverage_pct: float = 1.0
    room_entitlement: str | None
    covers_outpatient_diagnostics: bool | None
    accredited_at_mmc: bool | None
    is_illustrative: bool = False  # True for the reference fixture (§2.3)
    exclusions: list[str] = []
```

```python
# pricing/schemas.py
class PricedItem(BaseModel):
    item: ExtractedItem
    mmc_code: str
    catalog_name: str
    price_low: Decimal
    price_high: Decimal
    price_basis: Literal["package", "component"] | None
    rvs_code: str | None
    case_rate: Decimal | None
    match_confidence: float

class BudgetEstimate(BaseModel):
    priced: list[PricedItem]
    unpriced: list[ExtractedItem]           # MMC publishes no price
    needs_confirmation: list[ExtractedItem] # ambiguous / low confidence
    gross_low: Decimal;      gross_high: Decimal
    discount_applied: Decimal
    philhealth_applied: Decimal
    hmo_applied: Decimal
    prepare_low: Decimal;    prepare_high: Decimal
    separate_lines: list[SeparateLine]      # PF, room & board — never in the total
    caveats: list[str]
```

**The hard invariant** (handoff §10.5) — enforce as an exception, not a warning:

```python
assert len(priced) + len(unpriced) + len(needs_confirmation) == len(slip.items)
```

A silently dropped item understates someone's bill and is invisible in the output.

---

## 5. The waterfall, precisely

Pure function. No LLM anywhere in this path.

```
W0  gross        = Σ (price_low, price_high) over priced items, facility/service only
W1  discount     = gross × 0.714286  if senior or PWD    (VAT exemption × 0.80)
W2  philhealth   = Σ case_rate  over items where price_basis == 'package'
                                and rvs_code is not None
                                and kind == 'procedure'
W3  hmo          = min(remaining_balance, mbl_remaining, coverage_pct × balance_after_W2)
W4  prepare      = max(0, balance_after_W3)
```

Rules that are not optional:

- **W2 never fires on a lab or imaging item.** Outpatient diagnostics are not case-rated (§2.1).
- **`price_basis == 'component'` is a hard block on ever printing "fully covered."** The case
  rate exceeds MMC's ceiling, so MMC is billing a fragment (handoff §5.4). 4 rows today.
- **No line goes negative.** Clamp at each step; a case rate larger than the item's price means
  covered-in-full for that item, not a credit against other items.
- **Room & board never enters the total** (handoff §8). Length of stay is unknowable from a slip,
  and assuming one invents the largest number on the page. Separate line, per-day, always.
- **Ambiguity resolves toward the higher out-of-pocket** (handoff §5.2). Over-preparing is
  survivable; under-quoting is not.
- Range arithmetic: carry `low` and `high` independently end-to-end. Never average to a point
  estimate — the range *is* the honest answer.

### Data caveats the implementer will hit

- Prices in the CSVs are **comma-formatted strings** (`"1,810"`). Parse to `Decimal`, not float.
- `facility_rates` is **not purely room & board** despite the handoff's label — it is MMC's whole
  per-day facility department, and includes `CARDIOVERSION`, `ECMO ICU`, `HEMODIALYSIS CRITCARE`,
  `AIR MATTRESS`. Filter to actual room types by an explicit allow-list, or the UI will offer
  "cardioversion" as a room choice.
- `as_of` varies per item (2021 → 2025 in this table alone). Show the oldest `as_of` across the
  items in a report so staleness is visible.

---

## 6. Build order

Each phase ends in something runnable and testable. Phases 1–3 have no CV dependency, so they can
proceed in parallel with the RRL.

Ready-to-paste prompts for every phase below live in
[`PROMPTS_SCOPE_V2.md`](PROMPTS_SCOPE_V2.md) — each one is self-contained so a different person
(or a fresh agent session) can pick up any phase cold.

| # | Phase | Owner | Depends on | Definition of done |
|---|---|---|---|---|
| **0** | **Foundation.** Rebuild the DB (`python data/load_db.py`, then `python -m data.build_embeddings`). Today's `dr_mundo.db` is still the v1 build — 34 procedures, no `price_basis`. Add `data/samples/` to `.gitignore` **before any patient document exists**. Kick off track **P**. | team | — | `load_db.py` runs with no `IntegrityError`; `professional_fees`, `facility_rates`, `lab_panels` present |
| **1** | **Contracts.** `vision/schemas.py` + `pricing/schemas.py` per §4, and nothing else. Small, but it is what lets A/B/C work in parallel. | team | 0 | Models import; the §4 count invariant has a test |
| **2** | **Query layer.** Extend [`db/queries.py`](db/queries.py): `get_panel_comparison`, `get_professional_fees`, `get_facility_rates`; surface `price_basis` + `confidence`. Pre-written parameterised SQL — the model never writes SQL. | B | 1 | Typed rows; unit tests on known values |
| **3** | **Waterfall.** `pricing/waterfall.py` per §5. No LLM, no I/O. | B | 1, 2 | Golden-number tests incl. all four `component` rows and both discount orderings |
| **4** | **Panels.** `pricing/panels.py` — panel vs. sum of members. | B | 2, 3 | Correct on all 9 `lab_panels` mappings |
| **5** | **CV: request slip.** `vision/redact.py` → `vision/ocr.py` → `vision/extract_request.py`. Redaction runs **first**. Includes the RRL benchmark (§8). | A | 1, P (partial) | Runs on the gold set; per-source item-level P/R reported (§9.1) |
| **6** | **CV: HMO letter.** `vision/extract_hmo.py` → `HMOPlan`. | A | 1, 5 | Extracted plan drives W3; nothing patient-identifying written under the repo |
| **7** | **Guardrail retrofit (§2.5).** Nested `_grounded_values`, per-item not-covered note, `path="budget_report"`, raster redactions into `pii_found`, `check_input` with an attachment. **Must land before Phase 10.** | C | 1, 3 | A multi-item report survives the pipeline intact; a hallucinated peso in it is still caught |
| **8** | **Tools, routing, memory.** New tools (§7); `SessionMemory` carries the `BudgetEstimate` between turns so the §14 refine loop re-prices without re-upload. | C | 3, 4, 5, 6 | Agent completes an image → Pass 1 → refine → Pass 2 trajectory |
| **9** | **API + UI upload.** Multipart image on the FastAPI endpoint; Streamlit file upload + Pass 1/Pass 2 rendering. | C | 8 | A slip can be uploaded and priced through the real UI |
| **10** | **Report renderer.** `report/render.py` → the one-pager (§11), inline + PDF. | A | 7, 9 | PDF renders; every peso traces to a `BudgetEstimate` field |
| **11** | **Eval suite.** §9, §9.1, §9.2. | C | P, 10 | 3+ quantitative metrics, reported per source, with interpretation |
| **12** | **Deck + write-up.** Spec §6.2/§6.3 format. | team | 11 | Spec §11 checklist fully ticked |
| **P** | **Gold set** — collect, redact, annotate (§9.2). **Runs in parallel from Phase 0.** | team | 0 | 40 slips (floor 24), four cells non-empty, ~20% double-annotated |

**Track P is the critical path, not Phase 12.** It starts at Phase 0 and gates Phases 5 and 11.
Everything else can slip a week; this can't.

**Docker note:** WeasyPrint needs `libpango`/`libcairo`, which `python:3.11-slim` does not ship
(handoff §11). Add them in Phase 10, alongside the OCR weights (§8) — the two together are the
whole image-size problem, so solve them once, not twice.

---

## 7. New agent tools

Keep descriptions carrying the routing logic, matching the existing style in `agent/tools.py`.

| Tool | Purpose |
|---|---|
| `extract_doctor_request(image)` | CV + normalisation → `RequestSlip`. Entry point for the image path. |
| `extract_hmo_plan(image)` | CV + normalisation → `HMOPlan`. Optional; absent ⇒ label *"before any HMO."* |
| `price_item_list(items, hmo, senior_pwd)` | Deterministic. Runs the whole waterfall → `BudgetEstimate`. |
| `compare_panel(service)` | Panel vs. components. |
| `get_room_rates()` | Separate line only. Must not be summable into the total. |

The two-layer grounding from v1 stays: structured fields come from tool results, and the output
guard checks **every peso figure in the prose** against them. With a report this numeric, that
guard is the main defence against a confident wrong total.

---

## 8. CV component + RRL (capstone #14, and 30% of the rubric)

The spec requires a CV/DS model as a **first-class, non-decorative** component, and §6.3 requires
you to **present an RRL justifying the choice**. A bare multimodal-LLM call is weak here on both
counts: it is arguably just another LLM tool call, and "we used the vision endpoint of the model
we already had" is not a model selection with trade-offs.

**This extends handoff §12; it does not overrule it.** §12 specifies *vision LLM → strict
Pydantic*, and was written on 2026-08-09 — before the Final Capstone spec existed. Putting an OCR
model in front changes nothing §12 asked for: redaction still runs first, the stage still ends in
strict Pydantic, low-confidence reads still route to `needs_confirmation`. The spec's requirement
is additive, so both are satisfiable at once and no §2-style decision is needed.

**Recommended shape:** a real OCR model as the callable tool, with the LLM doing *normalisation*
downstream (`"CBC c PC"` → `CBC (COMPLETE BLOOD COUNT)`). That gives a genuine RRL, keeps the CV
component load-bearing — no OCR, no input at all — and makes the vision-LLM the fallback arm
rather than the whole component.

**RRL candidates**, all behind one interface in `vision/models/` so they are swappable and
benchmarkable on the same gold set:

| Candidate | Why it's in the comparison |
|---|---|
| Tesseract | Baseline. Cheap, weak on handwriting — establishes the floor |
| PaddleOCR | Strong printed-text detection+recognition, runs local |
| docTR | Document-structure aware; good on form layouts |
| TrOCR | Transformer, handwriting-oriented — the interesting arm |
| Vision LLM | Upper bound on semantics, no bbox/confidence, per-call cost — **comparison arm only**, not the shipped path (§0.1) |

Report per candidate on the gold set: **item-level recall, precision, latency, cost, local vs API**.
That table *is* the RRL slide. The trade-off to articulate: printed lab slips and handwritten
admitting orders are different problems, and the pipeline may route between two models.

**Local-only, CPU-only (§0.1).** No GPU on the LXC — confirmed. Benchmark latency **on the
container, not a dev laptop**; a laptop with an integrated GPU or simply more cores will mislead
you about all four candidates.

**Set a latency budget before you benchmark, not after.** Something like *"a slip must go from
upload to report in under N seconds."* Decide N up front, in writing. TrOCR is per-line
transformer inference and on CPU will be the slowest arm by a wide margin — quite possibly beyond
any budget you'd accept for a live demo. Rejecting it against a pre-committed threshold is a
finding. Rejecting it after seeing the numbers is a rationalisation, and the difference is visible
to anyone who asks how the threshold was chosen. Expect the practical shortlist to be
**PaddleOCR and docTR**, with Tesseract as the floor and TrOCR reported as evaluated-and-infeasible
— that is a perfectly good RRL outcome and directly answers the spec's "when to use one over
another."

Watch the image size: adding
PaddleOCR or docTR plus model weights to `python:3.11-slim` is a large jump, and it stacks with the
`libpango`/`libcairo` that WeasyPrint needs (§6, Phase 10). Pin model weights into the image at
build time rather than downloading on first run — a container that fetches weights at startup will
fail the live demo on conference wifi.

Keeping images local is also a **presentable design decision**, not just a constraint: patient
documents never leave the box, which is the strongest possible pairing with the raster-redaction
requirement. Put it on the architecture slide.

**Redaction is not optional and runs first** (handoff §12): redact in the **raster**, not via PDF
annotations, which can be peeled off. No unredacted intermediate may be written anywhere under
the repo.

---

## 9. Eval plan (capstone #13, 20% of the rubric)

The spec is explicit that the Midterm was graded on your own sample outputs and the Final wants a
rigorous suite. This is the largest gap between the repo today and the rubric.

**Gold set:** 30–50 request slips — printed and handwritten, redacted — each annotated with a
ground-truth item list. Include slips containing items MMC does not price (fecalysis, sodium):
`unpriced[]` being busy is the honest outcome, not a bug. This set does double duty as the RRL
benchmark (§8).

### 9.1 Stratification — the main threat to metric validity

Per §0.1 the corpus varies on **two axes at once**: real vs synthetic, and procedure-named vs
work-up-only. If those axes correlate — e.g. every synthetic slip names a procedure and every real
one doesn't — then any difference you measure is uninterpretable, and you will not be able to say
whether the model struggled with handwriting or with procedure lines.

Two rules:

1. **Cross the axes deliberately.** Populate all four cells: real/named, real/work-up-only,
   synthetic/named, synthetic/work-up-only. They need not be equal, but none may be empty.
2. **Never report a blended headline.** Every metric in §9 is reported **per source** (real vs
   synthetic) at minimum. Synthetic slips are clean in exactly the ways real ones aren't; a
   combined F1 flatters the model and collapses under one question in Q&A.

Tag each gold item with `source: real|synthetic` and `names_procedure: bool` at annotation time.
Retrofitting these tags after the fact is far more painful than adding two fields now.

**Branch to test explicitly:** a work-up-only slip must produce a report that *says* no procedure
was identified and PhilHealth therefore does not apply — not one showing ₱0 of coverage, which
reads as "PhilHealth covers nothing" and is a different, wrong claim.

### 9.2 Annotation protocol

The team annotates its own gold set, which makes the protocol a design artefact rather than an
afterthought. Write it down *before* the first slip is labelled — retrofitting a rule means
re-labelling everything done under the old one.

**How many.** Item-level metrics care about item count, not slip count. At roughly 8 items per
slip, **40 slips ≈ 320 items**, which is enough for an F1 you can quote with a straight face and
gives ~10 per stratification cell (§9.1). Treat **24 slips (6/cell) as the floor** — below that the
per-cell numbers are anecdotes. If time is short, cut *synthetic* slips, never real ones.

**Rules to fix in advance** — each of these will otherwise be decided inconsistently three times:

- **What is one item?** `CBC with platelet count` — one item or two? Pick a rule and apply it
  everywhere, because it silently changes every precision and recall figure you report.
- **Record `raw_text` verbatim *and* the intended catalogue item**, separately. The first scores
  OCR, the second scores matching. Collapsing them makes it impossible to tell which stage failed —
  and those are owned by two different people (§12).
- **Illegible items get flagged, never guessed.** They are the ground truth for
  `needs_confirmation`, and an annotator quietly resolving one destroys the only signal you have
  for the branch that protects patients from confident wrong prices.
- **Order doesn't count.** Score as a set; a slip read bottom-to-top is not an error.
- **Redact first, annotate second.** Nobody should be looking at an unredacted slip in a
  spreadsheet.

**Double-annotate ~20% and report inter-annotator agreement.** With three annotators this costs
about 8 slips of duplicated effort and buys two things the spec rewards directly: it is exactly the
"more rigorous eval suite" the Final asks for over the Midterm, and it establishes a **human
ceiling** — if two of you agree on only 92% of items, an OCR F1 of 0.90 is near-optimal rather than
mediocre, and you can say so with evidence. Disagreements are also the fastest way to find the
holes in the rules above.

| Layer | Metric | Why it answers the thesis |
|---|---|---|
| Unit | Waterfall exactness vs. hand-computed goldens | The arithmetic is deterministic; it should be *provably* right |
| Unit | Count invariant holds on 100% of runs | A dropped item is invisible and understates a bill |
| Component | OCR item-level **precision / recall / F1** | "given only images" — this is the load-bearing claim |
| Component | Item → catalogue **top-1 match accuracy** | Wrong match = confidently wrong price |
| Trajectory | Tool-sequence validity; `ask_user` fires when confidence is low | Does it clarify rather than guess? |
| End-to-end | **Hallucinated-peso rate** — every figure in prose present in the structured result | Target 0%; this is the trust metric |
| LLM-as-judge | Honesty rubric: does it name what's missing, avoid "fully covered" on `component` rows, flag illustrative HMO? | The gaps are the design (handoff §2) |

Pick **three headline numbers** for the deck: OCR F1, top-1 match accuracy, hallucinated-peso
rate. Report each with interpretation, not just the value.

---

## 10. Test questions (adviser task 3)

**5 × 3 by input type**

*Procedures:* `magkano ang tanggal apdo?` · `how much for a laparoscopic cholecystectomy?` ·
`total knee replacement po` · `hysterectomy cost` · `appendectomy — magkano?` (the honest-gap case)

*Radiologic:* `chest xray` · `ultrasound ng tiyan` · `CT scan of the head` · `mammogram magkano` ·
`MRI lower back with contrast`

*Blood tests:* `magkano ang cbc` · `lipid profile` (panel-vs-components) · `magkano ang creatinine`
(**must disambiguate** serum vs 24h urine) · `HbA1c` · `FBS and uric acid`

**5 coverage combinations**

1. PhilHealth ✓, HMO ✗ — case-rated procedure, no upload → label *"before any HMO"*
2. PhilHealth ✓, HMO ✓ — full waterfall, HMO applied to the post-PhilHealth balance
3. PhilHealth ✗, HMO ✓ — outpatient lab slip; **HMO is the entire coverage story** (§2.1)
4. PhilHealth ✗, HMO ✗ — pure gross; the report is an itemised total and says so
5. `price_basis == 'component'` (colposcopy / LEEP / IUD / vaginal hysterectomy) — must **never**
   print "fully covered"

**3 senior/PWD**

1. Senior + PhilHealth-covered procedure → verifies discount-before-PhilHealth ordering (§2.4)
2. PWD + outpatient lab panel → verifies `×0.714286`, not `×0.80`
3. Senior + HMO + case rate → all four legs; verifies clamping and no negative line

**Also worth a fixture:** an unreadable/blurred slip. The correct behaviour is
`needs_confirmation`, not a guess.

---

## 11. Report format (adviser task 4)

One page. Every number traceable.

```
DR. MUNDO — BUDGET ESTIMATE            Makati Medical Center
Read from your request: 6 items                    prices as of <oldest as_of>

WHAT YOU'LL PAY               ₱ 12,400 – ₱ 21,700     ← the number they came for

  Itemised (4 priced)                    ₱ 4,400 – ₱ 9,700
    CBC ₱630–1,200 · Urinalysis ₱495–1,000 · Chest PA ₱1,105–3,400 · HbA1c ₱2,170–4,100
  Senior/PWD discount (−28.6%)                    − ₱ 2,772
  PhilHealth case rate (RVS 47562)               − ₱ 60,450
  HMO — Medicard ‡ (remaining ₱ 40,000)          − ₱ 40,000

NOT INCLUDED — ask about these separately
  Surgeon's / anaesthesiologist's fee     ₱ 75,000 – ₱ 105,000
  Room & board, if admitted               ₱ 1,810/day (ward) – ₱ 21,800/day (suite)

NOT PRICED (2) — MMC publishes no price; NOT in the total above
  Fecalysis · Sodium

PLEASE CONFIRM (1)
  Your slip says "CREA" — Creatinine serum, or 24-hour urine?

‡ illustrative reference plan, not your actual policy
Estimates only, not a quotation. Every price traces to an MMC catalogue item code.
```

Design rules: the headline range is the largest thing on the page; excluded lines are visually
*outside* the total, not a footnote; unpriced and needs-confirmation are never collapsed away.

---

## 12. Component ownership (capstone spec §4)

**Team of 3 ⇒ floor of 6 components**, each member owning ≥2 and able to explain them; #14 is
mandatory for the team. The split below assigns **9**, comfortably clear of the floor, with the
extra giving slack if someone's component turns out thin.

| Member | Components | Owns in code |
|---|---|---|
| A — CV lead | **#14 CV/DS ★**, #2 Disambiguation, #5 Guardrails | `vision/`, RRL + benchmark, raster redaction, `needs_confirmation` routing, `guardrails/pii.py` |
| B — data lead | #3 RAG, #12 Advanced RAG, #10 SQL/Planning-Critique | `db/search.py`, `db/aliases.py`, `db/queries.py`, `pricing/` |
| C — agent lead | #9 ReAct/Tool Use, #13 Evals, #8 LLMOps | `agent/loop.py`, `agent/tools.py`, `eval/`, MLflow, `guardrails/output_guard.py` |
| (team) | #1 Prompting, #4 Memory, #6 UI, #7 API | carried from v1 |

Two workstreams aren't numbered components but still need an owner: **`report/`** (goes with A —
same document-rendering muscle as `vision/`) and the **§2.5 guardrail retrofit**, which straddles A
and C — the raster/PII half is A's, the grounding half is C's. Agree that boundary before Phase 6b
or it will be the thing nobody does.

With three people, everyone presents and everyone fields Q&A on their own components. There is no
bench.

Everyone must be able to defend the **value proposition and its UoM** (spec §6.3) — that is graded
under Presentation now. Frame it in defensible units: *hours per month* of calling hospitals, or
*pesos of avoided surprise* per admission, plus the panel-vs-components saving (₱60–₱1,400 per
panel, real numbers). Flag intangibles explicitly as intangible.

**Sanity check the spec demands** (§5 — *could ChatGPT or a Google search suffice?*): no, and
provably. MMC's prices only render behind a POST search, and the MMC→RVS crosswalk does not exist
anywhere published — it is 51 hand-made mappings. Say exactly that on a slide.

**One thing to pre-empt in Q&A:** the rubric lists "safety-critical workflows without a
human-in-the-loop" as a poor fit. Dr. Mundo estimates *prices*, not triage or diagnosis. State
that explicitly rather than letting a grader raise it.

---

## 13. Open questions

The four CV-blocking decisions are settled in §0.1. What remains does **not** block Phases 0–3,
which depend only on the committed dataset and can start immediately.

**Still needed:**

1. **The OCR latency budget (§8)** — one number, agreed before benchmarking. It is the only
   remaining decision that changes an outcome rather than a schedule.
2. **Gold-set size, confirmed against the calendar.** §9.2 recommends 40 slips and floors it at 24.
   Collection + annotation is track **P** in §6 and the **critical path of the whole project** — it
   gates Phase 5 and Phase 11, and §0.1 made it harder on both axes (handwriting in scope, benefits
   letters rather than cards). It starts at Phase 0 and runs alongside everything else.

**Settled:** team of 3 (§12) · team annotates its own gold set (§9.2) · no GPU, CPU-only (§8).

**Defaults if nobody decides — override knowingly:**

| Question | Default |
|---|---|
| How does senior/PWD status get set? | Agent asks once, conversationally, and stores it in session memory. Not a UI checkbox — it's a conversational fact like any other, and the toggle would sit unused |
| Length of stay for room & board | **None assumed.** Per-day separate line only (handoff §8). Only revisit if someone asks for an all-in figure, and then print the assumed LOS on the report |
| PDF library | WeasyPrint — the one-pager is design-heavy and HTML→PDF is far easier to iterate. Accept the `libpango`/`libcairo` Docker cost; ReportLab is the fallback if the image gets unmanageable alongside OCR weights |
| Multi-turn on an uploaded slip | Yes — `needs_confirmation` → user answers → re-price without re-uploading. **Note this changes `agent/memory.py`:** `SessionMemory` currently holds text turns only, and will need to carry the structured `BudgetEstimate` between turns |
| Report delivery | Rendered inline in chat **and** downloadable as PDF. The PDF is the deliverable; the inline view is what gets demoed live |

---

## 14. User flow

Two entry points. The v1 text path is **unchanged** — `magkano ang lipid profile?` still routes
through `search_catalog` → `get_covered_cost` / `get_outpatient_cost` exactly as it does today.
Everything new hangs off the image path.

```
PATIENT OPENS CHAT
      │
      ├──────────────────────────────┐
      ▼                              ▼
 uploads a request slip        types a question   ← v1 path, unchanged
      │                              │
      ▼                              └─→ search_catalog → covered / outpatient → answer
 RASTER REDACTION                    ← step zero. before anything touches disk
      │
      ▼
 document-type check ──not a request slip?──→ say so, ask for one
      │
      ▼
 OCR (local, CPU)                    → spans + per-span confidence
      │
      ▼
 LLM normalisation                   → ExtractedItem[]  (raw_text, normalized, kind)
      │
      ▼
 catalogue match (aliases + embeddings)
      │
      ▼
 TRIAGE ──┬──→ priced[]               matched, MMC publishes a price
          ├──→ unpriced[]             MMC publishes nothing (fecalysis, sodium)
          └──→ needs_confirmation[]   low OCR confidence, or ambiguous match
      │
      │   invariant: len(priced) + len(unpriced) + len(needs_confirmation) == len(extracted)
      ▼
 ╔══════════════════════════════════════════════════════════════╗
 ║ PASS 1 REPORT — shown before asking anything                 ║
 ║   gross range · PhilHealth only if a procedure was named     ║
 ║   labelled "before any HMO or discounts"                     ║
 ╚══════════════════════════════════════════════════════════════╝
      │
      ▼
 AGENT OFFERS TO REFINE — one question per turn, in this order
      │
      ├─ 1. "Your slip says CREA — serum, or 24-hour urine?"        → correctness
      ├─ 2. "Is this work-up for a planned operation?"              → unlocks PhilHealth
      ├─ 3. "Do you have an HMO? Upload your benefits letter."      → unlocks W3
      └─ 4. "Are you a senior citizen or PWD?"                      → unlocks −28.6%
      │       (each answer re-runs the waterfall; no re-upload)
      ▼
 ╔══════════════════════════════════════════════════════════════╗
 ║ PASS 2 REPORT — refined                                      ║
 ╚══════════════════════════════════════════════════════════════╝
      │
      ▼
 OUTPUT GUARDRAILS   grounding (nested) → per-item not-covered note → disclaimer
      │
      ▼
 render inline  +  PDF download
      │
      ▼
 follow-ups in the same session — memory holds the BudgetEstimate
```

### 14.1 The five rules that shape it

1. **Never block on a question.** A patient who uploaded a slip wants a number, not an intake
   form. Pass 1 asks nothing and always produces a report; every question after it is an *offer to
   improve* an estimate that already exists. Three questions before the first number is how you
   lose someone in a hospital lobby.
2. **One question per turn.** This is the existing `ask_user` contract (`agent/tools.py`) — it
   stops the loop and asks exactly one thing. Don't batch them into a form; a slip with two
   ambiguous items produces two turns.
3. **Refine in order of what it changes, not what it's worth.** Disambiguation goes first even
   though it moves the number least — a wrong item invalidates everything downstream of it.
   Procedure identification comes next because it unlocks the single largest deduction (a case rate
   can be ₱60,450), then HMO, then the senior/PWD percentage.
4. **The buckets never collapse.** `unpriced[]` and `needs_confirmation[]` are on every render,
   including Pass 1. An item silently dropped from the report understates a real bill and is
   invisible — the failure class the §4 invariant exists to make impossible.
5. **Nothing is assumed on the patient's behalf.** No HMO answer ⇒ *"before any HMO"*, never a
   quiet zero. No procedure identified ⇒ *"no procedure named, so PhilHealth doesn't apply here"*,
   never ₱0 of coverage — those read as different claims and only one of them is true.

### 14.2 Failure branches to build deliberately

| Situation | Correct behaviour |
|---|---|
| Blurred / unreadable slip | Say it's unreadable and ask for a retake. Do **not** price a handful of low-confidence guesses |
| Not a medical document | Decline and say what's needed. The existing topic guard covers text; the image path needs its own check |
| Zero items extracted | Distinct from "all unpriced" — say the slip couldn't be read, not that MMC prices nothing on it |
| Every item unpriced | A real, honest outcome. Report it as such; the total is ₱0 *known*, not ₱0 *owed* |
| HMO letter uploaded but unreadable | Fall back to *"before any HMO"* and say why. Never fall back to the `eval/fixtures/` reference plan in a patient-facing answer |

### 14.3 Two integration points this flow depends on

- **`check_input` with an attachment.** An image upload with no caption hands the topic classifier
  an empty string (§2.5). Decide what it does *before* it refuses your own demo.
- **`SessionMemory` carries structured state.** Steps 1–4 of the refine loop re-run the waterfall
  without re-uploading, which means the `BudgetEstimate` survives between turns. `agent/memory.py`
  currently holds text turns only — see the §13 defaults table.

---

*Written 2026-08-14 against the 2026-08-09 commits (`9db6ab4`, `293ed5e`, `771aa5d`), which take
precedence per §0, plus the Final Capstone specification and the adviser notes. Nothing here is
built yet.*
