# Dr. Mundo — Scope v2 data handoff

> **You are implementing the app on top of this data.** The dataset is finished, verified and
> committed. This document explains what is in it, *why* each decision went the way it did,
> and what the answers might look like. Nothing here is a mandate — where you disagree with a
> call, the rationale is written down precisely so you can overrule it knowingly.

---

## 1. What changed, in one paragraph

The midterm shipped with a **curated 5-hospital dataset** — indicative ranges, not official
quotes. Scope v2 narrows to **one hospital, Makati Medical Center**, and replaces every price
with a **real, officially published figure** scraped from MMC's own price list. The dataset
grew from ~134 priced rows to ~2,400, and every single one carries MMC's catalogue item code
so any number on screen can be traced back and re-checked by hand.

Two v1 constraints are deliberately reversed: **HMO is now in scope** (as a patient upload,
not a dataset), and **outpatient items can now carry coverage math** where a case rate exists.

---

## 2. The rule that governed every decision

> **No number exists unless it was published. If we don't have it, we say so.**

This is the spine of the whole dataset, and it is why several things are missing that you
might expect to find. It came directly from the project owner: *"don't force synthetic data if
there is none."*

Consequences you will meet:
- Appendectomy has **no** hospital package price (§6.1).
- 19 real procedures have **no** PhilHealth case rate (§5.3).
- There is **no** HMO table at all (§7).
- Room & board exists but is **deliberately excluded from totals** (§8).

Each of these is a gap we chose to expose rather than paper over. When the app meets one, the
right behaviour is to report it, not to substitute a plausible-looking figure.

---

## 3. Where the data comes from

`https://www.makatimed.net.ph/price-list/` — MMC's official price list.

**A warning that cost us a wrong turn:** fetching that URL plainly returns an empty page, and
it is easy to conclude MMC publishes nothing (major PH private hospitals mostly don't —
St. Luke's and Asian Hospital genuinely publish no itemised prices). It is actually a
**searchable database that renders empty until you search**.

Mechanics, verified hands-on:
- Plain **HTTP POST** to `/price-list/`, one field: `search=<term>`. No auth, no AJAX token,
  no pagination.
- Prices are **already in the returned HTML**, embedded in a per-row inline `<script>` that
  builds the "See Price" modal. The "See Price" button reveals what is already there.
- Each row carries MMC's **item code**, name, department (`Type`), low price, high price and
  an `As of` date that **varies per item** (we saw Aug 2023 through Jul 2026).

**Parsing gotcha:** do not split rows on `<tr>…</tr>`. Each row's inline script embeds the
modal's own HTML table *as a string*, so a non-greedy `</tr>` terminates inside that string
and silently drops the prices. Anchor on the `name="submitPrice"` button instead.

**Enumeration gotcha (this one bit twice):** the search is unbounded — a single letter `A`
returns 5,195 rows — so the catalogue can be enumerated exhaustively rather than guessed at.
The first attempt swept vowels only, which **structurally cannot find `HDL` or `LDL`** (no
vowels). The scraper now sweeps the full alphabet plus digits. Any name contains at least one
letter, so coverage is complete: **6,167 items**.

Scraper: [`scraper/scrape_mmc_prices.py`](scraper/scrape_mmc_prices.py). This is a one-time
offline build step, exactly like the existing PDF scraper — **the app still does no live
lookups at answer time.**

---

## 4. The tables

Rebuild everything with:

```bash
python -m data.build_rvs_crosswalk   # curated MMC -> RVS mapping
python -m data.build_dataset         # the CSVs
python data/load_db.py               # dr_mundo.db
python -m data.build_embeddings      # needs OPENAI_API_KEY
```

| Table | Rows | What it is |
|---|---|---|
| `hospitals` | 1 | Makati Medical Center (id **2** — not renumbered) |
| `philhealth_procedure_rates` | 4,312 | National PhilHealth Annex B. **Unchanged and complete** |
| `hospital_procedure_prices` | 51 | Procedures with a verified RVS code → case rate applies |
| `hospital_prices` | 1,605 | 842 laboratory · 566 imaging · 178 diagnostic · 19 procedures with no case rate |
| `professional_fees` | 756 | Surgeon / anaesthesiologist, itemised by specialty |
| `facility_rates` | 34 | Room & board, **per day** |
| `lab_panels` | 9 | Panel → member test mapping |

Provenance columns on the price tables: `mmc_code` (the official item), `source`, `as_of`.

### 4.1 Case rates are current — don't re-scrape them
PhilHealth Circular 2024-0037 applied a 50% uplift to select case rates. Checked: **98.4% of
the 4,312 rates divide cleanly by 1.5 into whole pesos** (appendectomy = ₱31,200 × 1.5 =
₱46,800). The committed data already includes the adjustment.

---

## 5. The MMC → RVS crosswalk, and why it is hand-made

MMC uses its own item codes; PhilHealth pays by RVS code; **nobody publishes a mapping.**
Getting it wrong is the project's most dangerous failure — variants of one operation carry
very different rates (cholecystectomy is ₱60,450 / ₱90,675 / ₱104,130), so a bad pick yields
an out-of-pocket figure that *looks fine* and is tens of thousands out.

### 5.1 Automated matching was tried and rejected
A scorer keying on operative morphology (`-ECTOMY`, `-OSTOMY`, `-PLASTY`) works for
`LAPAROSCOPIC CHOLECYSTECTOMY` and collapses on acronyms — CABG, TAHBSO, FESS, ACL, VATS have
no root word. With nothing to grip it fell through to word overlap and returned confident
nonsense:

| MMC item | It proposed | Which actually is |
|---|---|---|
| CESAREAN SECTION MOTHER | 88331 | *Pathology consultation w/ frozen section* |
| CABG 3 VESSELS | 11403 | *Excision of benign lesion* |
| Endoscopic sinus surgery | 11770 | *Excision of pilonidal cyst* |
| USE OF WATERPROOF DOPPLER | 93556 | rated **"high" confidence** — not a procedure at all |

It is kept only as a shortlisting tool
([`data/propose_rvs_crosswalk.py`](data/propose_rvs_crosswalk.py)). **Don't promote it back to
deciding.** The lesson generalises: automation is fine for narrowing 4,312 candidates to five;
the choice among those five is clinical.

### 5.2 How the 51 mappings were actually made
Expand the acronym into the clinical operation → read candidate RVS descriptions → confirm the
operation, the **approach** (PhilHealth codes laparoscopic and open separately) and the extent
all agree. Every decision, its reasoning and the rejected alternatives are in
[`data/build_rvs_crosswalk.py`](data/build_rvs_crosswalk.py) and the generated
[`data/mmc_rvs_crosswalk.csv`](data/mmc_rvs_crosswalk.csv). Confidence: **41 high, 9 medium,
1 low**.

Worked example — `LAPAROSCOPIC CHOLECYSTECTOMY PACKAGE`:

| RVS | Case rate | Verdict |
|---|---|---|
| **47562** | **₱60,450** | plain laparoscopic cholecystectomy ✔ |
| 47563 | ₱60,450 | bundles cholangiography MMC never mentions |
| 47564 | ₱90,675 | bundles common-duct exploration — ₱30k richer, wrong |
| 47600 | ₱60,450 | the *open* operation |

**Ambiguity rule:** where two codes are both defensible, prefer the **lower** case rate. Less
assumed PhilHealth help ⇒ higher estimated out-of-pocket ⇒ the patient over-prepares rather
than being under-quoted. Over-preparing is survivable; under-quoting is not.

### 5.3 The 19 unmapped are a feature
`PRECISION CATARACT PHACOEMULSIFICATION` (the catalogue has no primary
cataract-extraction-with-IOL code), `VATS PACKAGE` (names the *approach*; 16 candidate codes
span ₱23,634–90,675 and nothing selects among them), IVC filter, PICC line, newborn packages.
Each has a written reason. They keep their real MMC price and live in `hospital_prices` under
`Procedure (no case rate)` — **PhilHealth coverage undetermined, not zero.**

### 5.4 `price_basis` — the flag that stops a silent lie
A PhilHealth case rate is **all-in** (facility + professional fee). If it exceeds MMC's
*ceiling* price, MMC cannot be billing the whole episode — it is a component charge. Four rows:

| RVS | MMC charges | Case rate | |
|---|---|---|---|
| 57452 Colposcopy | ₱4,100 | ₱15,639 | `component` |
| 57460 LEEP | ₱4,860 | ₱18,915 | `component` |
| 58300 IUD insertion | ₱2,060 | ₱3,900 | `component` |
| 58260 Vaginal hysterectomy | ₱40,590 | ₱59,085 | `component` |

Without this the app reports **"fully covered"** on a partial price and understates a real
bill. Note the comparison is against `price_high` deliberately: a case rate merely *inside* a
wide range is ordinary partial coverage (ESWL, ₱22,700–70,900 against ₱35,100), not a partial
price. An earlier version compared against `price_low` and produced exactly that false
positive.

**Suggestion:** treat `price_basis='component'` as a hard block on ever printing "fully
covered", and say something like *"MMC's published figure covers only part of this procedure,
so your actual bill will be higher."*

---

## 6. Things that will surprise you

### 6.1 Appendectomy has no package price
MMC publishes **no operating-room package** for it — only professional fees:

| | |
|---|---|
| LAP APPENDECTOMY – SURGERY | ₱100,000–140,000 |
| OPEN APPENDECTOMY – SURGERY (GENERAL) | ₱75,000–105,000 |
| OPEN APPENDECTOMY RUPTURED – SURGERY | ₱87,500–122,500 |

The midterm demo was built on appendectomy, so **the demo script needs revisiting.** The app
can still answer usefully (case rate ₱46,800 + real surgeon fees), but it must be explicit
that the hospital/facility portion is not included. Suggested substitute headline demos:
**laparoscopic cholecystectomy** (full package + case rate) or **lipid profile** (the
panel-vs-individual story).

### 6.2 The same RVS code can have several MMC packages
`27447` (total knee replacement) has two: ₱268,000–334,000 (unilateral) and ₱428,000–536,000
(bilateral) — one case rate, ₱78,624, and PhilHealth pays it once. `47562` likewise has plain
and "W/ ICG" packages. The existing aggregate min/max logic handles this, but a good answer
probably names the variants rather than presenting one merged range.

### 6.3 MMC's names are long and clinical
`LIPID PROFILE (HDL LDL CHOL TRIG) SERUM`, `LAPAROSCOPY, SURGICAL; CHOLECYSTECTOMY (ANY
METHOD)`. Nobody types those, so **the alias layer matters more than it did in v1**. All aliases
in [`db/aliases.py`](db/aliases.py) were rewritten against the real names; the old ones were
100% dead. Retrieval is verified working, including Taglish:

```
'magkano ang cbc'      → CBC (COMPLETE BLOOD COUNT)          1.49
'chest xray'           → CHEST PA                            1.55
'ultrasound ng tiyan'  → WHOLE ABDOMEN                       1.23
'tanggal apdo'         → LAPAROSCOPY, SURGICAL; CHOLECYST…   1.09
'magkano ang tuli'     → CIRCUMCISION, USING CLAMP…          1.07
```

### 6.4 Ambiguity is now real, not hypothetical
There are three LIPID PROFILE variants at three prices, `CREATININE SERUM` vs `CREATININE
URINE 24HRS`, `ER CBC` vs `CBC`. This is genuinely good material for the disambiguation story
— the agent *should* sometimes ask which one.

---

## 7. HMO — there is no table, and that's the design

The earlier plan was a synthetic `hmo_plans.csv` with invented Maxicare tiers. **Dropped**, on
the owner's call, in favour of the patient **uploading their own HMO certificate**, extracted
at runtime.

Why it is better: real per-patient plans differ enormously, so a static table of three tiers
could only ever be wrong; it reuses the extraction pipeline you're already building; and it
means **every committed number in this project traces to a published source** — nothing
synthetic anywhere.

What this implies for you:
- The HMO step is **conditional**. No upload ⇒ skip it and label the figure *"before any
  HMO"*, rather than implying HMO doesn't exist.
- You need a small schema for extracted fields (benefit limit, remaining balance, coverage %),
  not a dataset.
- **Never commit extracted HMO data** — it carries the patient's name and policy number. Same
  redaction discipline as the doctor's-request samples.

---

## 8. Facility costs — captured, but never multiplied in

`facility_rates` holds real per-day rates: WARD ₱1,810, ICU ₱9,900, ISOLATION PRIVATE ₱10,900,
REGULAR SUITE ₱21,800, PRESIDENTIAL SUITE ₱37,200.

**They are in their own table on purpose.** Length of stay is unknowable from a doctor's
request, and multiplying by an assumed LOS would invent the single largest number on the page —
a fabricated multiplier sitting on top of carefully sourced figures. A 3-day vs 7-day suite
stay is an ₱87,000 swing. Keeping them out of `hospital_prices` makes that a **structural**
guarantee rather than a convention someone forgets.

**Suggested handling** — show them as a separate labelled line:

> *If admitted, room & board is billed separately: ₱1,810/day (ward) to ₱21,800/day (suite).*

Two reasons the gap is narrower than it looks: MMC's `OPERATING ROOM` / `DELIVERY SURGERY`
prices are **all-in packages** (OR time and room already inside), and PhilHealth case rates
already bundle a facility fee — so adding room charges *and* subtracting the full case rate
carelessly double-counts in the patient's favour, the more harmful direction.

If you ever do want one all-in number, print the assumed length of stay on the report in plain
sight rather than burying it in the math.

---

## 9. The cost waterfall — suggested shape

Owner's decision: keep it **gross → PhilHealth → HMO**.

```
gross price range (from the tables)
        │
        ▼
PhilHealth case rate      only when an RVS code is mapped
        │                 and price_basis == 'package'
        ▼
HMO benefit               only when the patient uploaded a certificate
        │                 min(remaining balance, remaining MBL)
        ▼
"prepare ₱X – ₱Y"    + separate lines for professional fees and room & board
```

**Senior/PWD discount — offered, not prescribed.** RA 9994 gives seniors and PWDs 20% off plus
VAT exemption on medical services — effectively `× (1/1.12) × 0.80 = × 0.714286`, a ~28.6%
reduction, which is a large and genuinely verifiable saving. The owner chose to leave it out of
the core waterfall; **your call whether to add it.** If you do, one trap worth knowing: the
operations *commute* (`x/1.12×0.80 ≡ x×0.80/1.12`), so the order is a documentation question
under RR 7-2010, not an arithmetic one. The bug that actually costs money is **omitting the VAT
exemption entirely** and applying only the 20%.

**Professional fees: keep them a separate line** (owner's decision). MMC publishes them apart
from the package, and they vary hugely by surgeon — blending a fixed package price with a
highly variable fee makes the headline number less honest, not more useful.

---

## 10. What answers might look like

Illustrative only — every peso figure below is real, pulled from the built database, but the
wording and layout are yours to design.

### 10.1 A covered procedure with a full package

> **You:** magkano ang tanggal apdo?
>
> **Dr. Mundo:** That's a **cholecystectomy** — Makati Medical Center prices the laparoscopic
> operation in two packages:
>
> | Package | Price |
> |---|---|
> | Laparoscopic cholecystectomy | ₱150,000 – ₱184,000 |
> | …with ICG fluorescence | ₱174,500 – ₱208,500 |
>
> **PhilHealth case rate:** ₱60,450 (RVS 47562)
> **Estimated out-of-pocket:** ₱89,550 – ₱148,050
>
> Surgeon's and anaesthesiologist's fees are billed separately. If you're admitted, room &
> board is extra — ₱1,810/day (ward) to ₱21,800/day (suite).
>
> *Prices as of MMC's published list; estimates only, not a quotation.*

### 10.2 Blood tests, with the panel comparison

> **You:** how much for a lipid profile?
>
> **Dr. Mundo:** **LIPID PROFILE (HDL LDL CHOL TRIG) SERUM** — ₱4,450 – ₱8,700.
>
> Worth knowing: buying the four component tests separately (Total Cholesterol, HDL, LDL,
> Triglycerides) comes to **₱4,520 – ₱9,400** — so **the panel is cheaper by ₱70 to ₱700.**
>
> This isn't covered by PhilHealth as an outpatient test.

*(All three panels beat their components: ₱60–₱1,400 depending on panel and price end. This is
scope (c) working on real numbers — worth demoing.)*

### 10.3 Disambiguation, which is now genuinely necessary

> **You:** magkano ang creatinine?
>
> **Dr. Mundo:** Two different tests match — which did your doctor order?
>
> - **CREATININE SERUM** (blood) — ₱740 – ₱1,400
> - **CREATININE URINE 24HRS** (24-hour urine collection) — different test, different price
>
> **You:** yung dugo
>
> **Dr. Mundo:** **CREATININE SERUM** — ₱740 – ₱1,400. Not PhilHealth-covered as an outpatient
> test.

### 10.4 The honest gap — appendectomy

> **You:** how much is an appendectomy?
>
> **Dr. Mundo:** I have partial information for this one, and I want to be clear about what's
> missing.
>
> **PhilHealth case rate:** ₱46,800 (RVS 44950)
> **Surgeon's fee** (MMC published): ₱75,000 – ₱105,000 open · ₱100,000 – ₱140,000 laparoscopic
>
> **MMC does not publish an operating-room package price for appendectomy**, so I can't give
> you a full hospital bill — the figures above exclude facility charges, room, and
> anaesthesia. Treat them as a floor, not a total.

### 10.5 A doctor's request with mixed results

> **You:** *[uploads a request slip]*
>
> **Dr. Mundo:** I read **6 items** from your request.
>
> **Priced (4)** — ₱4,400 – ₱9,700 total
> · CBC ₱630–1,200 · Urinalysis ₱495–1,000 · Chest PA ₱1,105–3,400 · HbA1c ₱2,170–4,100
>
> **Not priced (2)** — MMC doesn't publish a price for these, so they're **not** in the total
> above: · Fecalysis · Sodium
>
> **Please confirm (1):** your slip says "CREA" — did you mean Creatinine (serum)?
>
> None of these are PhilHealth-covered as outpatient tests.

**The invariant that makes this trustworthy:**
`len(priced) + len(unpriced) + len(needs_confirmation) == len(extracted)`. Enforce it as a hard
failure. Silently dropping an item understates someone's bill, and it is invisible in the
output — exactly the class of error that survives review.

---

## 11. Suggested build order (refactor in place)

The owner's preference is to **keep the working v1 app** — ReAct loop, guardrails, memory,
FastAPI, Streamlit, MLflow, Docker — and change the tools underneath. That preserves the
Phase 9–10 work that carries grade weight.

1. **Query layer** (`db/queries.py`) — add lookups for panels, professional fees, facility
   rates; surface `price_basis` and `confidence`. Still pre-written parameterised SQL: the
   model never writes SQL.
2. **Waterfall** — pure Python, no LLM. Easy to unit-test and the numbers become auditable.
3. **Tools & routing** (`agent/tools.py`) — the two-path split still holds; add panel
   comparison and the unpriced/needs-confirmation buckets.
4. **Extraction stage** — vision LLM → strict Pydantic. See §12.
5. **Report renderer** — the 1-page PDF. Note WeasyPrint needs `libpango`/`libcairo`, which
   `python:3.11-slim` does not ship, so the Dockerfile needs changes.

The two-layer grounding from v1 still applies and is worth keeping: structured fields come
from tool results, and the output guard checks every peso figure in the prose against them.

---

## 12. Extraction stage — notes since you own it

- **Redact before anything else.** These are real patient documents. Redact in the **raster**,
  not via PDF annotations (annotations can be peeled off). No unredacted intermediate may be
  written anywhere under the repo, and `data/samples/` should be gitignored **before** the
  first sample lands.
- **Strict Pydantic output**, not free text — an item list with a confidence per item, so
  low-confidence reads route to `needs_confirmation` rather than being priced.
- Expect **handwriting**, abbreviations (`CBC`, `U/A`, `CXR`, `FBS`, `CREA`, `Na/K`), and items
  MMC simply doesn't price. `unpriced[]` will be busy; that's the honest outcome, not a bug.
- Same pipeline reads the optional **HMO certificate** (§7).

---

## 13. Verification

```bash
python data/load_db.py        # must complete with no IntegrityError
python -m pytest tests/ -q    # 43 passed, 1 skipped
python -m agent.thin_slice "magkano ang lipid profile?"
```

Current state: **43 pass, 1 skipped.** The skip is
`test_covered_ambiguous_hospital_needs_clarification` — the "multiple hospitals match" branch
is unreachable with one hospital. It is skipped with a reason rather than deleted, because the
code path in `db/queries.py` is untouched and still correct.

`PRAGMA foreign_keys = ON` is set before load, so an inconsistent rebuild fails loudly rather
than loading orphans — treat a clean `load_db.py` run as part of verification, not just a
build step.

---

## 14. Known gaps, stated plainly

| Gap | Why | Suggested handling |
|---|---|---|
| No appendectomy package | MMC doesn't publish one | Answer with case rate + professional fees, labelled incomplete |
| 19 procedures without RVS codes | No honest match exists | Show price, report coverage undetermined |
| No fecalysis | Not in MMC's catalogue under any name we found | Route to `unpriced[]` |
| Consultations/OPD not extracted | Out of the three scope categories | Add a sweep if you want them |
| 1 low-confidence mapping | `SHOULDER ARTHROSCOPY PACKAGE` is unqualified; 8 candidate codes ₱35,100–59,943, took the lowest | Fine as-is; revisit if it ever headlines a demo |
| Senior/PWD discount absent | Owner scoped it out | §9 has the math if you add it |

---

*Dataset built and verified 2026-08. Every price traces to a Makati Medical Center catalogue
item code; every case rate to PhilHealth Annex B. Where something wasn't published, there is
no row — and the app should say so.*
