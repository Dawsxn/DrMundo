# Synthetic laboratory request slips — vision eval dataset

**Handoff. Read this before using anything in this directory.**

260 labelled Philippine outpatient laboratory request forms, fully synthetic,
for evaluating the document-extraction stage (`vision/`). Every image is
procedurally generated; there is no real patient, physician, clinic, licence
number or address anywhere in it, so this can be committed, shared and
photographed freely — unlike `data/samples/`, which is gitignored for exactly
the opposite reason.

Generated 2026-08-15 from master seed `20260814`.

---

## 1. Four things a fresh reader gets wrong by default

**1. Nothing is trained on this.** It is an eval set. 260 samples, not 10,000 —
diversity and difficulty coverage were the goal, and every sample tests
something specific.

**2. A struck-through row means the test was CANCELLED, not ordered.** It is
deliberately *absent* from `checked_codes` and listed under `cancelled_codes`.
45 rows across 40 forms are like this. Score a cancelled row as ordered and you
have not just lost a point — you have **over-billed the patient for a test the
doctor crossed out.** Every other mark style (tick, tick overflowing the box,
cross, filled box, slash through the box, circle round the box, circle round the
label) means ordered.

**3. There are no prices in here.** This dataset emits test *codes*. Turning
codes into money is `pricing/`'s job, against `data/hospital_prices.csv`. That
separation was deliberate and enforced upstream, so that no facility's price
table got baked into the dataset contract.

**4. No model has ever been run against this.** See §6. There is no accuracy
number for Opus 5, Sonnet 5 or Haiku 4.5 on this set. Nothing has been measured
and found wanting.

---

## 2. What is here

```
media/            260 PNGs — the images a model actually sees
groundtruth/      260 JSONs — per-sample ground truth, one per image
answer_key.csv    one row per sample, for filtering and diffing
answer_key.md     the same content grouped per sample, readable by eye
samples.json      manifest: sample_id, image, expected codes, printed labels
contact_sheet.png all 260 at thumbnail size, for spotting anything broken
taxonomy/         the code table the answer key's codes refer to
```

`taxonomy/taxonomy.yaml` is the contract: 87 codes, 36 concepts, every code
mapped to a canonical name, its surface forms (strings the generator may print)
and its aliases (strings a resolver must accept). **`checked_codes` is
meaningless without it.**

Images are named `<sample_id>_<media_class>.png`. Every PNG carries
`SYNTHETIC-DATA` in its metadata, so a file separated from this directory still
says what it is.

---

## 3. The 260

| Block | n | What it is |
|---|---:|---|
| coverage | 200 | 4 templates × 5 media classes × 10 — a full factorial |
| stress | 40 | 8 profiles × 5, forcing co-occurrences the taxonomy flagged as dangerous |
| blank | 10 | a real form with **zero** marks |
| non-lab | 10 | not a laboratory request at all |

Blanks and non-lab documents sit *on top* of the 240, not inside it: a blank
inside the coverage grid would leave a factorial cell short, and it forces no
co-occurrence so it cannot be a stress case.

1,407 checked tests overall — median 5 per form, max 24, 64 distinct codes
exercised. 52 samples per media class. Difficulty: 104 easy, 52 medium, 104 hard.

### Templates — each is a different bundle configuration

This is the axis that matters most for `pricing/panels.py`, which has to decide
panel-versus-component:

| | Layout | Bundle policy |
|---|---|---|
| `tpl_01_onecol_sans` | 1 column of sections, Letter | **bundles only** — Lipid Profile, never its analytes |
| `tpl_02_twocol_serif` | 2 column, serif, A4 | **bundle AND components on one page** — Lipid Profile *beside* all five analytes |
| `tpl_03_threecol_dense` | 3 column, 7.2pt, A5 | **components only** — the five analytes, no Lipid Profile. This is the most common real PH layout |
| `tpl_04_halfsheet_compact` | half-sheet, patient block at the **bottom** | **mixed** — Lipid Profile as a bundle *and* exploded electrolytes on the same sheet |

If the extraction stage collapses these four cases, the panel advisory
downstream is working from bad input.

### Media classes — increasing difficulty

`clean` → `scan` → `photocopy_gen1` → `photocopy_gen3` → `fax`.
`photocopy_gen3` compounds three degradation passes so faint marks progressively
drop out; `fax` is binarised and dithered. **These two are where a VLM is
expected to start failing**, and that is the point of having them. Look at the
right-hand columns of the contact sheet.

---

## 4. The traps, and what correct behaviour looks like

| Case | n | Expected output |
|---|---:|---|
| **Blank form** | 10 | Empty set. A model handed a blank form will confabulate; this measures that directly |
| **Not a lab request** | 10 | Empty set **plus** a "not a laboratory request" signal |
| **Cancelled rows** | 45 | In `cancelled_codes`, absent from `checked_codes` |
| **Faint / ambiguous marks** | 58 forms | Ground truth still says what was drawn; the model may reasonably be unsure |

The non-lab set is graded. `lab_result_report` (2 of the 10) is the one that
matters: it is covered in test names, values and reference ranges under a
laboratory letterhead, **and it is still not a request.** A model keying on
"does this page mention CBC and creatinine" fails it — and Dr. Mundo would then
bill a patient for tests they have already had. The others (prescription,
clinical abstract, medical certificate, referral letter, consent form, clinic
notice) are easier.

### Two more deliberate difficulties

- **~12% of printed labels are aliases**, not the canonical surface form. The
  form may say "Stool Examination" where the code is `FECALYSIS`, or "Fasting
  Blood Glucose" for `FBS`. `checked_labels_as_printed` shows what is actually
  on the page.
- **Bare `KUB` appears twice on some sheets** — once under Ultrasound, once
  under X-Ray. It is only resolvable from its section heading. This is why the
  extraction prompt should ask for the section header alongside each label.

---

## 5. Reading the answer key

`answer_key.csv`, one row per sample:

```
sample_id, template_id, media_class, difficulty, n_checked,
checked_codes, checked_labels_as_printed, cancelled_codes,
variants, modifiers, is_blank, is_not_lab_request, stress_case,
n_ambiguous_marks, primary_mark_style, order_profile, image
```

Multi-value fields are `;`-joined. `checked_codes` and
`checked_labels_as_printed` are positionally aligned — column *n* of one
describes column *n* of the other. `variants` encodes `CODE=option`
(e.g. `CA_SERUM=ionized`, a circled sub-option); `modifiers` encodes
`CODE=a+b` (e.g. `CT_CHEST=iv_contrast`).

**Caveat: variants and modifiers are thin.** Only ~18 samples carry a circled
sub-option and ~5 a ticked modifier. Any accuracy figure on those two axes has
very wide error bars — do not read much into them.

`answer_key.md` is the same content grouped per sample, meant to be read beside
`contact_sheet.png` when spot-checking by eye. `groundtruth/<id>.json` carries
the full record per sample: every mark with its style and state, the media
degradation log, and the printed label for each code.

---

## 6. What has NOT happened — do not assume otherwise

**No model has ever been run against this dataset.** The generator's eval
harness exists and works, but it has only ever been exercised by *fake*
providers (a perfect oracle, a null provider, a deliberately corrupted oracle, a
perfect transcriber). Those validate the scorer, and nothing else.

Specifically, and none of this should be inferred as done:

- No API call has ever been made from the generator repo.
- There is no accuracy, miss-rate or hallucination-rate number for any model on these images.
- The model comparison (Opus 5 / Sonnet 5 / Haiku 4.5) and the resolution sweep have not started.
- Nothing was measured and found disappointing. There is no negative result being glossed over here.

This was **deferred, not cancelled and not failed.** The dataset was built first,
on purpose, so that generation and measurement stayed separate pieces of work.

The standing gate: run ~10 images against a real model and review the output
*before* concluding anything from a full run.

---

## 7. Integration gap with `vision/schemas.py` — read before wiring this up

This dataset was designed against a different contract than the one currently in
`vision/schemas.py`. Neither is wrong; they have not been reconciled. The
mismatches, in rough order of how much they matter:

1. **No cancellation concept in `ExtractedItem`.** There is no `state` /
   `cancelled` field, so a struck-through row currently flows into `pricing/` as
   an ordered test. That is the over-billing failure §1 warns about, and 45 rows
   in this dataset will hit it.
2. **`normalized: Optional[str]` is a name, not a code.** This dataset's whole
   contract is a `test_code` from `taxonomy/taxonomy.yaml`, resolved from free
   text through an alias table. There is no code field to carry it.
3. **`ocr_confidence: float` is required**, and the pipeline docstring describes
   `OCR spans -> LLM normalisation`. This dataset was built for a VLM that reads
   the image and emits text directly — there is no OCR stage and no per-item
   confidence to populate. Ground truth has a boolean `uncertain`, not a float.
4. **`bbox` is optional here and low-value.** Boxes are emitted by the generator
   but were explicitly taken off the critical path: a VLM emits text, not
   coordinates.
5. **`ItemKind` is `procedure|imaging|lab|unknown`**; this dataset's taxonomy uses
   14 sections (hematology, blood_chemistry, renal, metabolism, liver, thyroid,
   cardiac, bleeding, serology, hepatitis, xray, ultrasound, ct_advanced,
   cardiac_diagnostics). A mapping is needed.
6. **`RequestSlip.redacted` must be True.** These images are synthetic and have
   nothing to redact, so eval code has to set the flag as a formality — which
   slightly weakens an invariant that exists to protect real documents. Worth a
   separate construction path for synthetic input rather than lying to the
   validator.

**Decide (1) before running an eval.** The rest can be adapters; (1) is a
correctness bug with a direct cost to the patient.

---

## 8. Regenerating

The generator is a separate repository (`labrequests`) and is **not** vendored
here — it needs playwright + chromium, opencv and augraphy, none of which this
application needs at runtime. It consumes this dataset; it does not rebuild it.

The whole set is deterministic from master seed `20260814`: two independent runs
produced byte-identical ground truth. Rebuilding is
`python -m labgen.run dataset` in that repo, taking ~20 minutes.

That repo also carries `DECISIONS.md`, which records why each of the above is
the way it is — read it before changing any of these conventions, because most
of them were reversals of something that turned out to be wrong.
