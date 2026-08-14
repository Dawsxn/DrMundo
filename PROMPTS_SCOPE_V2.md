# Dr. Mundo — Scope v2 phase prompts

Every phase below is a **self-contained prompt**. Paste the fenced block into a fresh session and
it will run cold — no memory of previous conversations required. Phases are in
[`PLAN_SCOPE_V2_BUILD.md`](PLAN_SCOPE_V2_BUILD.md) §6 with owners and dependencies.

**Before pasting any of them,** check §6 for what that phase depends on. Running Phase 3 before
Phase 1 will not work; running Phase 5 before track P has slips will not work.

Each prompt ends by asking the agent to report what it did and what it deliberately left alone.
That report is the handover to whoever runs the next phase.

---

## Shared preamble

Every prompt below already contains this. It is repeated here so you can see what is being
asserted each time, and fix it in one place if the repo moves.

> You are working in the Dr. Mundo repository at `D:\Libraries\Documents\STAI100\DrMundo`.
>
> Read these first, in order: `PLAN_SCOPE_V2_BUILD.md` §0 (precedence) and §0.1 (locked
> decisions), then `HANDOFF_SCOPE_V2_DATA.md`. **The 2026-08-09 commits are authoritative** — the
> handoff, the dataset CSVs, and `GUARDRAIL_PIPELINE.md`. Where anything disagrees with them, they
> win, except at the four contradictions enumerated in plan §2, which are already resolved there.
>
> Do not re-scrape MMC. Do not invent prices. Where a number was never published, the correct
> behaviour is to say so — that rule is the spine of this dataset and it is not negotiable.

---

## Phase 0 — Foundation

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0 and §0.1, then HANDOFF_SCOPE_V2_DATA.md §4. The 2026-08-09
commits are authoritative.

Do these four things:

1. Add `data/samples/` and `data/samples_raw/` to .gitignore, with a comment explaining that
   they hold un-redactable patient documents and must never be committed. Do this FIRST, before
   anything else in this phase — no patient document may exist in the working tree before the
   ignore rule does.

2. Rebuild the database from the committed Scope v2 CSVs:
       python data/load_db.py
   The current dr_mundo.db is the stale v1 build (34 procedures, no price_basis column). It is
   already gitignored as a build artifact, so overwriting it is safe. PRAGMA foreign_keys = ON is
   set before load, so an inconsistent rebuild must fail loudly — if it raises IntegrityError,
   STOP and report it rather than working around it.

3. Rebuild embeddings:
       python -m data.build_embeddings
   This needs OPENAI_API_KEY in the environment. If it is not set, skip this step and say so
   clearly in your report — do not fabricate an embeddings file.

4. Verify:
       python -m pytest tests/ -q
   The handoff records 43 passed, 1 skipped as the expected state. Report the actual numbers. If
   tests fail, diagnose but do NOT fix them in this phase — report them.

Then confirm the new tables exist and are populated: professional_fees (756), facility_rates (34),
lab_panels (9), hospital_prices (1605), hospital_procedure_prices (51). Report the real counts you
observe, not the expected ones.

Do not write application code in this phase. Do not modify data/ CSVs or the build scripts.

Report: what ran, actual row counts, actual test results, and anything that did not match the
handoff's stated expectations.
```

---

## Phase 1 — Contracts

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0, §0.1 and §4 (Data contracts). The 2026-08-09 commits are
authoritative.

Create ONLY the shared data contracts. This phase is deliberately small: three people build
against these in parallel, so they must land before anything else and must not churn afterwards.

1. vision/schemas.py — ExtractedItem, RequestSlip, HMOPlan exactly as specified in plan §4.
   - RequestSlip.redacted must have a validator that REJECTS False. An unredacted slip must not
     be constructible.
   - HMOPlan is assembled CONVERSATIONALLY, never from an image (plan §2.3). Its mbl_source field
     is Literal["published_tier", "patient_stated"] | None, and remaining_balance is always
     patient-stated — it appears on no document.

2. pricing/schemas.py — PricedItem, BudgetEstimate, SeparateLine per plan §4.
   - MONEY REPRESENTATION. The existing codebase uses int pesos throughout: data/load_db.py has
     to_int(), db/queries.py returns price_low/price_high as int, and
     guardrails/output_guard.py::_grounded_values returns set[int]. Do NOT change that convention.
     Instead: pricing/ converts to Decimal at its own boundary, does all arithmetic in Decimal
     (the senior/PWD multiplier 0.714286 produces fractions, and float would make the numbers
     unauditable), and rounds back to whole pesos at the presentation boundary.
   - Put that rounding in ONE exported function, e.g. pricing/schemas.py::to_display_pesos(), and
     state the rule explicitly (recommended: ROUND_HALF_UP to whole pesos). Phases 7 and 10 both
     depend on it being the same function — see the note in Phase 7.
   - BudgetEstimate must enforce the invariant from plan §4 as a Pydantic model validator that
     RAISES:
         len(priced) + len(unpriced) + len(needs_confirmation) == len(extracted items)
     A silently dropped item understates a real bill and is invisible in the output. This must be
     a hard failure, not a warning or a log line.

3. Write tests/test_schemas.py covering: the redaction validator rejects False; the count
   invariant raises when violated and passes when satisfied; Decimal is preserved through
   construction (no float coercion).

Follow the existing repo style — look at agent/schemas.py first and match it (Pydantic version,
docstring voice, import ordering).

Do NOT implement pricing logic, queries, OCR, or anything that uses these models. Contracts only.

Report: the models created, the validators enforcing the two hard rules, and any field in plan §4
you found underspecified — flag it rather than guessing, since three people are about to build on
whatever you decide.
```

---

## Phase 2 — Query layer

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0, §0.1, §5 (the waterfall — for what these queries must feed), and
HANDOFF_SCOPE_V2_DATA.md §4 and §5.4. The 2026-08-09 commits are authoritative.

Extend db/queries.py with new lookups. Read the existing file first and match its style exactly:
pre-written parameterised SQL, typed returns. The model NEVER writes SQL — that is a project
invariant, not a preference.

Add:
1. get_panel_comparison(panel_service) — returns the panel's own price and the summed price range
   of its members, from lab_panels joined to hospital_prices. Must handle a panel whose members
   are not all priced: return which members are missing rather than silently summing fewer.
2. get_professional_fees(service_query) — from professional_fees (756 rows).
3. get_facility_rates() — from facility_rates. IMPORTANT: this table is NOT purely room & board
   despite the handoff's label. It contains CARDIOVERSION, ECMO ICU, HEMODIALYSIS CRITCARE, AIR
   MATTRESS. Filter to actual room types with an explicit allow-list, or the UI will offer
   "cardioversion" as a room choice. Put the allow-list in one named constant.
4. Surface price_basis and confidence on the existing get_covered_cost path. price_basis is the
   flag that stops the app claiming "fully covered" on a partial price (handoff §5.4) — it must
   reach the caller, not be dropped in the mapping layer.

Data caveat: prices in these CSVs are comma-formatted strings ("1,810"). data/load_db.py already
has to_int() for exactly this — reuse the existing convention rather than writing a second parser.
Keep returning int pesos from db/queries.py; the Decimal conversion happens inside pricing/, not
here. Do not introduce a second money representation at this layer.

Write unit tests against known values from the handoff: laparoscopic cholecystectomy RVS 47562 at
case rate 60450; the four price_basis='component' rows (57452, 57460, 58300, 58260); ward rate
1810 and presidential suite 37200.

Do NOT implement the waterfall, panels comparison logic beyond the raw lookup, or any LLM call.

Report: functions added, the room-type allow-list you chose and why, and any row you found that
does not fit the schema the handoff describes.
```

---

## Phase 3 — Waterfall

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0, §0.1, §2.2, §2.4 and §5 (the waterfall, in full), plus
HANDOFF_SCOPE_V2_DATA.md §5.4, §8 and §9. The 2026-08-09 commits are authoritative.

Implement pricing/waterfall.py. This is PURE PYTHON: no LLM, no I/O, no database access. It takes
PricedItems (from pricing/schemas.py, Phase 1) and returns a BudgetEstimate. Being pure is the
point — every number in this project becomes auditable and unit-testable here.

Implement exactly the order in plan §5:
  W0 gross      = sum of item ranges, facility/service charges only
  W1 discount   = gross x 0.714286 if senior or PWD   (VAT exemption THEN 20%)
  W2 philhealth = sum of case rates where price_basis == 'package' AND rvs_code is not None
                  AND kind == 'procedure'
  W3 hmo        = min(remaining_balance, mbl_remaining, coverage_pct x balance)
  W4 prepare    = max(0, remaining balance)

Non-negotiable rules, each of which exists because violating it produces a plausible wrong number:

- W2 NEVER fires on a lab or imaging item. Outpatient diagnostics are not case-rated. A case rate
  is all-in for an admission; applying one to a lab double-counts.
- price_basis == 'component' is a HARD BLOCK on ever emitting "fully covered". Those four rows are
  partial prices — MMC is billing a fragment of the episode.
- No line ever goes negative. Clamp at every step. A case rate larger than an item's price means
  that item is covered in full, NOT a credit against other items.
- Cap the PhilHealth deduction at the facility gross. The gross excludes professional fees but the
  case rate includes a PF share; netting the full case rate against a facility-only gross credits
  the patient with a benefit the bill never contained. See plan §2.2.
- Room & board NEVER enters the total. Separate line, per-day, always. Length of stay is unknowable
  from a request slip and assuming one invents the largest number on the page.
- Carry low and high independently end to end. Never average to a point estimate — the range IS
  the honest answer.
- Where two readings are defensible, resolve toward the HIGHER out-of-pocket. Over-preparing is
  survivable; under-quoting is not.

Money: db/queries.py hands you int pesos (existing convention). Convert to Decimal on the way in,
do every step in Decimal, and round to whole pesos ONLY at the presentation boundary using the
single to_display_pesos() from Phase 1. Never round mid-waterfall — rounding at each step
accumulates drift across five operations and the totals stop reconciling with the line items.

Discount ordering (plan §2.4): implement discount BEFORE PhilHealth. These do not commute —
(G x 0.714286) - P differs from (G - P) x 0.714286 by about P13,400 on a P46,800 case rate. Put
0.714286 in ONE named constant. Unit-test both orderings so the choice is visible and defended,
and assert the constant is 0.714286 and not 0.80 — omitting the VAT exemption is the bug that
actually costs money.

Write tests/test_waterfall.py with hand-computed golden numbers. Cover at minimum: a package
procedure with a case rate; all four component rows; senior+PhilHealth (ordering); PWD on an
outpatient panel; HMO exhausting its MBL mid-total; a case rate exceeding the item price (clamp);
an all-unpriced slip.

Do NOT touch OCR, tools, guardrails, or the renderer.

Report: the module, the constant, the clamping behaviour, and every golden number you computed by
hand with its working — those numbers are the audit trail for the whole project.
```

---

## Phase 4 — Panels

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0 and §0.1, and HANDOFF_SCOPE_V2_DATA.md §10.2. The 2026-08-09
commits are authoritative.

Implement pricing/panels.py: given items on a slip, identify lab panels and compare the panel
price against the summed price of its individual member tests, then report which is cheaper and
by how much.

Use get_panel_comparison from db/queries.py (Phase 2). There are 9 mappings in lab_panels covering
3 panels. Per the handoff, all three panels beat their components by P60-P1,400 depending on panel
and price end — verify this against the rebuilt database rather than trusting the figure, and
report what you actually measure.

Handle these honestly:
- A panel whose members are not all priced: report the comparison as incomplete rather than
  summing the subset. A partial sum understates the component side and makes the panel look better
  than it is.
- Both a panel AND its individual members appearing on the same slip. Decide what that means,
  implement it, and say what you decided in your report.
- Range arithmetic: compare low-to-low and high-to-high. The saving is itself a range.

Write tests covering all 9 mappings and the incomplete-members case.

Do NOT change the waterfall. Panels produce an advisory comparison shown alongside the estimate;
they do not silently rewrite what the patient is charged.

Report: measured savings per panel at both price ends, and your decision on the panel-plus-members
case.
```

---

## Phase 5 — CV: request slip extraction

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0, §0.1, §8 (CV component and RRL) and §9.1/§9.2 (how the gold set is
stratified and annotated), plus HANDOFF_SCOPE_V2_DATA.md §12. The 2026-08-09 commits are
authoritative.

Build the request-slip extraction pipeline. This is the mandatory CV component for the capstone
(spec component #14) and it is graded on being first-class, not decorative.

Order matters:

1. vision/redact.py — runs FIRST, before anything else touches an image. Redact in the RASTER, not
   via PDF annotations (annotations can be peeled off). No unredacted intermediate may be written
   anywhere under the repo. These are real patient documents.

2. vision/ocr.py — the CV model, wrapped as a callable tool behind ONE interface so candidates are
   swappable: image -> list of text spans with per-span confidence and bounding boxes.

3. vision/extract_request.py — OCR spans + LLM normalisation -> RequestSlip (vision/schemas.py,
   Phase 1). The LLM's job is normalisation only ("CBC c PC" -> "CBC (COMPLETE BLOOD COUNT)"), not
   reading pixels. Low OCR confidence routes to needs_confirmation and NEVER to a price.

Constraints from §0.1, already decided — do not relitigate them:
- LOCAL model only in the shipped path. No API vision as primary. Patient images do not leave the
  box.
- CPU only. There is no GPU on the deployment target (a Proxmox LXC).
- Printed AND handwritten are both in scope.

RRL benchmark — this is a deliverable of this phase, not an afterthought. Implement candidates
behind the vision/models/ interface and benchmark them on the gold set: Tesseract (floor),
PaddleOCR, docTR, TrOCR, and a vision LLM as a comparison arm only. Report item-level recall,
precision, latency and cost for each.

CRITICAL METHOD POINT: agree and write down the latency budget BEFORE you benchmark. Rejecting
TrOCR against a pre-committed threshold is a finding; rejecting it after seeing the numbers is a
rationalisation, and the difference is visible to anyone who asks how the threshold was chosen. If
no budget has been given to you, ask for one before running the benchmark.

Report metrics SEPARATELY for real vs synthetic slips (plan §9.1). Never publish a blended F1 —
synthetic slips are clean in exactly the ways real ones are not, and a combined number flatters the
model and collapses under one question in Q&A.

Also benchmark on the container, not a dev laptop. More cores or an integrated GPU will mislead you
about all four candidates.

Request slips are the ONLY document type in this project. HMO intake is conversational (plan §2.3),
so there is no second document pipeline to design for. Do NOT build the tools or the renderer.

Report: the pipeline, the RRL table, the latency budget and when it was fixed, and per-source
metrics. If a candidate was infeasible, say so and give the number that made it infeasible.
```

---

## Phase 6 — HMO intake (conversational)

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0, §0.1, §2.3 (in full — it was revised on 2026-08-14 and earlier
versions of this plan said the opposite) and §5 (W3), plus HANDOFF_SCOPE_V2_DATA.md §7.

HMO intake is CONVERSATIONAL. There is no upload, no card OCR, and no vision/extract_hmo.py. If
you find instructions anywhere describing an HMO document-extraction pipeline, they are superseded
by §2.3.

Two facts drive this design:
- Remaining balance appears on NO document. A certificate shows the ANNUAL MBL; the balance changes
  with every claim and lives in the member portal. It must be typed by the patient.
- Handoff §7 rejected INVENTED tiers, not published ones. A table of published figures with source
  URLs satisfies the project rule that no number exists unless it was published.

Build three things:

1. data/hmo_published_tiers.csv — published tier figures with columns: provider, plan_name,
   mbl_annual, room_entitlement, source (URL), as_of, is_published. Seed it from published
   individual/family tiers, e.g. Maxicare Platinum Plus 200000 (large private), Platinum 150000
   (regular private), Gold 100000, Silver 60000; MediCard Standard ~50000-60000 (ward/semi-private)
   with higher tiers 100000-120000. VERIFY each figure against the provider's own page before
   committing it and put the URL in the source column — do not carry over a number from this prompt
   without checking it. If a figure cannot be verified, omit the row rather than guessing.
   Room entitlement values should map onto the room types in facility_rates.

2. A lookup: plan name -> HMOPlan (vision/schemas.py, Phase 1) pre-filled with mbl_annual,
   room_entitlement, and mbl_source="published_tier". Matching should be forgiving of casing and
   partial names. A plan that matches nothing is the EXPECTED case, not an error — most PH coverage
   is employer-provided and negotiated, and corporate plans match no public tier.

3. The three refine questions for the §14 flow, in order:
     "Do you have an HMO? Which provider and plan?"
     "Roughly how much of your benefit is left?"      <- always typed, never looked up
     (ask for MBL directly only if the plan matched no tier)

Rules:
- The table PRE-FILLS, it never decides. Any patient-stated figure overrides it, and mbl_source
  flips to "patient_stated".
- Any figure taken from the table must be labelled in the output as published figures for that
  plan tier, with a nudge to check their own certificate. Handoff §7's objection that a static
  table "could only ever be wrong" for a given patient is real; the answer is labelling, not
  omission.
- No plan given => "before any HMO", never a quiet zero.
- Plan given but balance unknown => show the MBL-capped figure, labelled as an upper bound on HMO
  help rather than a computed balance.
- Never persist a patient's stated plan details alongside anything identifying.

Do NOT build any image handling here. Do NOT modify the waterfall — W3 is already specified in §5
and takes an HMOPlan regardless of how it was assembled.

Report: the table with every source URL you verified, which seed figures you could NOT verify and
therefore omitted, the matching behaviour, and how an unmatched plan is handled.
```

---

## Phase 7 — Guardrail retrofit

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0, §0.1 and §2.5 (in full), then GUARDRAIL_PIPELINE.md end to end.
GUARDRAIL_PIPELINE.md is in the 2026-08-09 priority window and is authoritative for how the
pipeline behaves today.

The existing guardrail pipeline is incompatible with a multi-item budget report. Fix it BEFORE the
renderer exists (Phase 10), because the failure is silent and you will not notice it afterwards.

Four fixes:

1. NESTED GROUNDING. guardrails/output_guard.py::_grounded_values collects numbers from a FLAT
   Answer (price_low, price_high, oop_low, oop_high, case_rate, as_of). A budget report quotes a
   range PER ITEM — none of which live in those scalar fields. Today every one reads as ungrounded,
   and the guard's remedy is to rebuild the prose from structured fields only, which silently
   deletes the itemisation and leaves a report that looks fine and says almost nothing.
   Extend _grounded_values to walk BudgetEstimate.priced[*] and separate_lines.
   Write a test that a correct multi-item report passes untouched, AND a test that a hallucinated
   peso inside a multi-item report is still caught. The second test is the one that matters —
   it is easy to "fix" this by making the guard permissive.

   ROUNDING PARITY — this will bite you and the symptom looks like a hallucination. _grounded_values
   returns set[int] and _money_amounts parses integers out of prose, but BudgetEstimate holds
   Decimals. If the guard rounds differently from the renderer, a report printing P12,401 gets
   compared against a grounded 12,400 and is flagged as ungrounded — so the guard deletes a
   perfectly correct figure. Use the SAME to_display_pesos() from Phase 1 in both places. Write a
   test with a value that rounds ambiguously (something ending .5) to prove they agree.

2. PER-ITEM NOT-COVERED NOTE. Output Guardrail 2 fires on answer.path == "outpatient". A budget
   report is MIXED: outpatient work-up plus possibly one case-rated procedure. A single path field
   cannot express that. Drive the note per-item from PricedItem.case_rate is None, and add
   path="budget_report".

3. RASTER PII. guardrails/pii.py regexes EMAIL / PHONE / PHILHEALTH_ID / CARD out of TEXT. The CV
   path introduces PII in rasters — patient name and policy number burned into pixels — which no
   text regex will ever see. The raster redaction from Phase 5 is a SECOND, INDEPENDENT mechanism.
   Wire its results into the same pii_found list so redactions stay visible in MLflow.

4. check_input WITH AN ATTACHMENT. Topic classification runs on text and refuses non-cost input. An
   image upload with no caption hands it an empty string. Decide and implement what happens when an
   attachment is present and text is empty — before it refuses your own live demo.

Preserve everything that currently works: PII redaction before the agent sees input, the disclaimer,
redacted-only memory storage. The DISCLAIMER in agent/format.py already says the estimate "may
exclude professional fees, medicines, and room charges", which is exactly right for Scope v2 —
reuse it, do not rewrite it.

Report: each fix, the tests proving the guard still catches hallucinations in nested reports, and
your decision on empty-text-with-attachment.
```

---

## Phase 8 — Tools, routing, memory

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0, §0.1, §7 (new tools) and §14 (the user flow, in full). The
2026-08-09 commits are authoritative.

Wire the pieces into the agent.

1. New tools in agent/tools.py — read the existing file first; the tool DESCRIPTIONS carry the
   routing logic the model depends on, so write them in the same voice and with the same
   directiveness:
     extract_doctor_request(image)   -> RequestSlip
     resolve_hmo_plan(provider, plan_name) -> HMOPlan   (Phase 6 lookup; NOT an image tool)
     price_item_list(items, hmo, senior_pwd) -> BudgetEstimate   (deterministic, runs the waterfall)
     compare_panel(service)
     get_room_rates()                -> separate line ONLY; must not be summable into the total
   The existing two-path split (get_covered_cost / get_outpatient_cost) still holds and must keep
   working — the v1 text path is unchanged.

2. SessionMemory must carry structured state. agent/memory.py currently holds text turns only
   (max_turns=20). The §14 refine loop re-prices without re-uploading, so the BudgetEstimate has to
   survive between turns. Keep memory ephemeral and redacted — never persist raw PII, never write
   a patient's extracted plan to disk.

3. Implement the §14 flow:
   - PASS 1 asks NOTHING and always produces a report: gross, plus PhilHealth only if a procedure
     was identified, labelled "before any HMO or discounts".
   - Then refine, ONE question per turn via the existing ask_user contract, in this order:
     (a) disambiguation, (b) "is this work-up for a planned operation?", (c) HMO provider/plan then
     remaining balance (conversational — see Phase 6), (d) senior/PWD. Order is by what each
     changes, not what it is worth — a wrong item invalidates everything downstream, so
     disambiguation goes first even though it moves the number least.
   - unpriced[] and needs_confirmation[] appear on EVERY render including Pass 1. They never
     collapse away.
   - No HMO answer => "before any HMO", never a quiet zero. No procedure identified => "no procedure
     named, so PhilHealth does not apply here", never P0 of coverage. Those read as different claims
     and only one is true.

4. Failure branches from §14.2, built deliberately: unreadable slip (ask for a retake, do not price
   low-confidence guesses); not a medical document; zero items extracted (distinct from all-unpriced);
   every item unpriced (a real outcome — P0 KNOWN, not P0 owed); a plan name matching no published
   tier (expected, not an error); a plan given with no known balance.

Do NOT build the renderer (Phase 10) or the UI (Phase 9).

Report: tools added, how memory carries the estimate, and a full worked trajectory of
upload -> Pass 1 -> one refine question -> Pass 2.
```

---

## Phase 9 — API + UI upload

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0, §0.1 and §14. The 2026-08-09 commits are authoritative.

Expose the image path through the existing API and UI. Read api/main.py and ui/app.py first and
match their structure — this extends the v1 app, it does not replace it.

1. api/main.py — accept a multipart image upload alongside the existing text endpoint. Keep the
   text /ask endpoint working unchanged. Uploaded images must be redacted before they are written
   anywhere, including any temp directory; if a temp file is unavoidable, it goes outside the repo
   and is deleted in a finally block.

2. ui/app.py — file upload control, plus rendering for the §14 two-pass flow: Pass 1 appears
   immediately with no questions, then the refine questions arrive one per turn. Preserve the
   existing liquid-glass theme and sample prompts.

3. The existing per-request token and cost accounting must keep working on the new path, and MLflow
   must log image-path requests the same way it logs text ones. OCR latency should be visible as
   its own number, not buried inside total request time — it is a headline metric for the RRL.

Do NOT change the waterfall, the tools, or the guardrails. If you find a bug in them, report it
rather than fixing it here.

Report: endpoints changed, how the two-pass flow renders, what MLflow now logs for an image request,
and confirmation that the v1 text path still works end to end.
```

---

## Phase 10 — Report renderer

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0, §0.1, §11 (the report layout) and §5 (what may and may not appear
in a total), plus HANDOFF_SCOPE_V2_DATA.md §8. The 2026-08-09 commits are authoritative.

PRECONDITION: Phase 7 (guardrail retrofit) must be done. Without nested grounding, the guard
silently strips the itemisation out of every report you generate and you will not notice.

Build report/render.py — a one-page report, rendered inline in chat and downloadable as PDF. Use
the layout in plan §11 as the spec.

Design rules, in priority order:
- The headline "what you'll pay" range is the largest thing on the page. It is what the patient
  came for.
- Excluded lines (professional fees, room & board) sit visually OUTSIDE the total, not in a
  footnote. A reader skimming must not be able to mistake them for included.
- NOT PRICED and PLEASE CONFIRM are always present when non-empty. They never collapse.
- Room & board is per-day and never multiplied. Do not print an all-in figure. If someone later
  wants one, the assumed length of stay must be printed on the report in plain sight.
- Any MBL taken from data/hmo_published_tiers.csv (mbl_source == "published_tier") carries a
  visible marker reading as "published figures for this plan tier — check your own certificate".
  Patient-stated figures do not.
- Show the OLDEST as_of across the items in the report so staleness is visible — as_of varies per
  item, from 2021 to 2025 in facility_rates alone.
- Every peso on the page must trace to a BudgetEstimate field. Write a test asserting this.
- Round with the SAME to_display_pesos() the grounding guard uses (Phase 1, Phase 7). If the
  renderer and the guard round differently, the guard will strip correct figures out of every
  report and the failure looks like a hallucination rather than a rounding bug.

Library: WeasyPrint is the default (the layout is design-heavy and HTML->PDF iterates fastest), but
it needs libpango and libcairo, which python:3.11-slim does not ship. Update the Dockerfile in this
phase. The OCR model weights from Phase 5 land in the same image, so solve the image-size problem
once for both. If the image becomes unmanageable, ReportLab is the sanctioned fallback — say so in
your report rather than silently switching.

Report: the renderer, a sample PDF for each of a covered procedure, a lab-only slip, and an
all-unpriced slip, plus the Dockerfile change and the resulting image size.
```

---

## Phase 11 — Eval suite

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0, §0.1, §1 (the thesis), §9, §9.1 and §9.2. The 2026-08-09 commits
are authoritative.

Build the evaluation suite. This is 20% of the capstone grade and the largest gap between this repo
and the rubric: the Midterm was graded on hand-picked sample outputs, and the Final wants rigour.

The suite exists to answer ONE question with a number:
  "Can an agent estimate the budget a patient needs to prepare, given only images of a doctor's
   request, accounting for both PhilHealth and HMO coverage?"

Extend eval/ (read run_eval.py and scoring.py first; match their structure). Layers:

  Unit         — waterfall exactness against hand-computed goldens
  Unit         — the count invariant holds on 100% of runs
  Component    — OCR item-level precision / recall / F1
  Component    — item -> catalogue top-1 match accuracy
  Trajectory   — tool-sequence validity; ask_user fires when confidence is low
  End-to-end   — hallucinated-peso rate (every figure in prose present in the structured result)
  LLM-as-judge — honesty rubric: does it name what is missing? does it avoid "fully covered" on
                 price_basis='component'? does it label published-tier MBLs as needing
                 verification against the patient's own certificate?

Three headline numbers for the deck: OCR F1, top-1 match accuracy, hallucinated-peso rate. Report
each WITH INTERPRETATION, not just a value.

STRATIFICATION — this is the main threat to validity, do not skip it. The gold set varies on two
axes at once: real vs synthetic, and procedure-named vs work-up-only. Report every metric PER
SOURCE at minimum. Never publish a blended headline: synthetic slips are clean in exactly the ways
real ones are not. If the four cells (real/named, real/work-up, synthetic/named, synthetic/work-up)
are not all populated, say so — a metric from an empty cell does not exist.

Report inter-annotator agreement from the ~20% double-annotated subset (§9.2). It establishes a
HUMAN CEILING: if two annotators agree on 92% of items, an OCR F1 of 0.90 is near-optimal rather
than mediocre, and you can defend that with evidence instead of adjectives.

Also test the branch where a work-up-only slip produces a report that SAYS no procedure was
identified — not one showing P0 of coverage, which is a different and wrong claim.

Report: every metric per source, the human ceiling, which cells were thin or empty, and a direct
answer to the thesis question with the number that supports it.
```

---

## Phase 12 — Deck and write-up

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md in full, HANDOFF_SCOPE_V2_DATA.md, and the Final Capstone
specification at "D:\Libraries\Documents\[Stratpoint x DLSU] Final Capstone - Project
Specification.docx". The 2026-08-09 commits are authoritative for what the system does.

Produce the slide deck and technical write-up. Existing decks are in the repo root — read
"Dr Mundo - Capstone Slides.pptx" and TECHNICAL_WRITEUP.md first; this is a restructure, not a
rewrite from zero.

Format requirements, all new for the Final and all graded:
- Title slide names the LLM used, with parameter size if open-source
- Agent name and tagline as a footer on EVERY slide
- Navigation tabs or breadcrumbs so the audience can track position
- The live demo moves to the END of the deck (the Midterm placed it mid-deck)
- 12-15 minutes plus 3 minutes Q&A, for a team of 3

Content that must be present:
- Team member contributions — who owned which module (plan §12)
- Value proposition with disciplined Units of Measurement. Qualify every time period: if a human
  doing this costs X pesos, say per what. Present the measure you estimated and be ready to defend
  it. Flag intangibles explicitly as intangible.
- RRL: the OCR model comparison, the trade-offs, and why the chosen model won (plan §8). Include
  the latency budget and when it was fixed.
- Architecture diagram showing where the CV model plugs into the agent pipeline (plan §14 has the
  flow)
- At least 3 quantitative eval metrics WITH INTERPRETATION (Phase 11)
- A full reasoning-trace walkthrough of one agent decision chain
- Design decisions and trade-offs — plan §2 is written as exactly this, use it
- Lessons learned and known limitations (handoff §14 and plan §13)

Two things to state explicitly rather than let a grader raise them:
- The sanity check from spec §5: no, ChatGPT or a Google search could NOT do this. MMC's prices
  only render behind a POST search, and the MMC->RVS crosswalk does not exist anywhere published —
  it is 51 hand-made mappings.
- Dr. Mundo estimates PRICES, not triage or diagnosis. The rubric lists "safety-critical workflows
  without a human in the loop" as a poor fit for agentic AI; say why this is not that.

Honesty requirements: HMO MBL figures come from PUBLISHED INDIVIDUAL/FAMILY tiers, but most PH
coverage is employer-provided and negotiated — so a corporate plan may match no public tier, and
remaining balance is always patient-stated rather than verified. Disclose both. Report OCR metrics
per source, never blended. Name the gaps: no appendectomy package, 19 procedures without RVS codes,
no fecalysis.

Demo: use laparoscopic cholecystectomy (full package plus case rate) or lipid profile (the
panel-vs-components story). Do NOT use appendectomy — MMC publishes no operating-room package for
it, so the demo the Midterm was built on no longer works.

Report: deck outline slide by slide, and which spec §11 checklist items are ticked versus
outstanding.
```

---

## Track P — Gold set (runs in parallel from Phase 0)

```
You are working in the Dr. Mundo repository at D:\Libraries\Documents\STAI100\DrMundo.

Read PLAN_SCOPE_V2_BUILD.md §0.1, §9.1 and §9.2, plus HANDOFF_SCOPE_V2_DATA.md §12.

This is the CRITICAL PATH of the whole project. It starts at Phase 0 and gates Phase 5 and Phase
11. Everything else can slip a week; this cannot.

PRECONDITION: data/samples/ must already be gitignored (Phase 0, step 1). Verify this before a
single document enters the working tree. If it is not ignored, stop and do that first.

Build the annotated gold set:

TARGET: 40 slips (~320 items at ~8 items per slip). FLOOR: 24. If time runs short, cut SYNTHETIC
slips, never real ones — the real ones are the only honest denominator.

STRATIFY across four cells, none empty:
  real / names-a-procedure        real / work-up-only
  synthetic / names-a-procedure   synthetic / work-up-only
The two axes must not correlate. If every synthetic slip names a procedure and every real one does
not, no metric you produce afterwards is interpretable — you will not be able to tell whether the
model struggled with handwriting or with procedure lines.

Include slips containing items MMC does not price (fecalysis, sodium). unpriced[] being busy is the
honest outcome, not a bug.

ANNOTATION PROTOCOL — write it down BEFORE labelling the first slip. Retrofitting a rule means
re-labelling everything done under the old one:
- What counts as ONE item? "CBC with platelet count" — one or two? Pick a rule, apply it
  everywhere. It silently changes every precision and recall figure you report.
- Record raw_text VERBATIM and the intended catalogue item SEPARATELY. The first scores OCR, the
  second scores matching. Collapsing them makes it impossible to tell which stage failed — and
  those stages are owned by two different people.
- Illegible items are FLAGGED, never guessed. They are the ground truth for needs_confirmation, and
  an annotator quietly resolving one destroys the only signal protecting patients from confident
  wrong prices.
- Order does not count. Score as a set.
- Redact FIRST, annotate SECOND. Nobody looks at an unredacted slip in a spreadsheet.
- Tag every item with source: real|synthetic and names_procedure: bool at annotation time. Adding
  these later is far more painful than now.

DOUBLE-ANNOTATE ~20% (about 8 slips) across different annotators and report inter-annotator
agreement. With three people this costs little and buys two things: it is exactly the rigour the
Final asks for over the Midterm, and it establishes a human ceiling for interpreting OCR F1.
Disagreements are also the fastest way to find holes in the rules above.

Redaction: in the RASTER, never via PDF annotations, which can be peeled off. No unredacted
intermediate anywhere under the repo.

Request slips are the ONLY document type. Do NOT collect HMO cards, certificates or benefits
letters — HMO intake went conversational on 2026-08-14 (plan §2.3) and no HMO document is used
anywhere in this project.

Report: counts per cell, the annotation rules as written, inter-annotator agreement, and the
real/synthetic split.
```
