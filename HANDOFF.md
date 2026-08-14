# Dr. Mundo — Handoff (Phases 9–10 remaining)

> **Read this first.** It gives a new contributor (and their Claude) enough context to
> finish the project without re-deriving anything. The app is **built and working through
> Phase 8**. Two phases remain: **Phase 9 (MLflow monitoring + eval harness)** and
> **Phase 10 (Docker + final README)**.

---

## 1. What Dr. Mundo is

A graded university capstone: an **agentic AI cost estimator** for Philippine healthcare.
A user asks, in plain English or Taglish, what a medical procedure or outpatient service
costs. The agent routes the question down one of two paths, looks up **real numbers from a
local SQLite database**, and returns a grounded estimate. It never invents figures and
never gives medical advice.

- **Path A — Covered procedures** (PhilHealth case rate applies): report hospital price
  **range**, the PhilHealth **case rate**, and estimated **out-of-pocket (OOP)**.
- **Path B — Outpatient services** (not PhilHealth-covered): report the price **range only**,
  and state clearly it is **not covered** (never compute OOP).

---

## 2. ⛔ The six hard constraints (NEVER violate — the grade depends on these)

1. **NO text-to-SQL.** The LLM must **never** generate SQL. Every DB access is a
   pre-written, parameterized query in Python using the raw `sqlite3` module (see
   [`db/queries.py`](db/queries.py)). The model only picks *which tool* to call and *with
   what arguments*.
2. **NO invented numbers.** Every figure in an answer must come from a DB row. This is
   enforced twice: structured `Answer` fields are filled from tool observations (not model
   prose), and the output guard replaces any ungrounded peso amount in the prose.
3. **NO HMO / private insurance.** Out of scope → refuse.
4. **NO policy/eligibility Q&A and NO document vector store.** (Embeddings are used only to
   match the *procedure/service catalog*, not documents.)
5. **NO external tools/APIs, scraping, or live lookups at answer time.** All data is local
   CSVs / SQLite. (The one PDF scraper was a one-time build step, already done.)
6. **NO medical advice.** Clinical/diagnostic/treatment questions → polite refusal +
   disclaimer.

If you add anything in Phase 9–10, make sure it does not quietly break one of these.

---

## 3. Quick start (Windows / PowerShell; Python 3.13)

```bash
# from the repo root: DrMundo/
python -m pip install -r requirements.txt

# 1. Build the SQLite DB from the committed CSVs (no API key needed).
python data/load_db.py                 # writes dr_mundo.db (gitignored)

# 2. Embeddings are ALREADY committed (data/embeddings.npz). Only rebuild if the
#    catalog changes — this one DOES need an API key:
# python data/build_embeddings.py

# 3. Configure the key for runtime (chat + input classifier + query embedding):
cp .env.example .env                   # then edit .env and set OPENAI_API_KEY

# 4. Run it (two terminals):
uvicorn api.main:app --reload          # → http://localhost:8000/docs
streamlit run ui/app.py                # → http://localhost:8501

# 5. Tests (28 unit tests, no API calls; conftest auto-builds the DB):
python -m pytest -q
```

`.env` keys (see [`.env.example`](.env.example)):
`OPENAI_API_KEY` (required), `OPENAI_CHAT_MODEL` (default `gpt-4o-mini`),
`OPENAI_EMBEDDING_MODEL` (default `text-embedding-3-small`).
The Streamlit UI reads `DR_MUNDO_API_URL` (default `http://localhost:8000`).

---

## 4. Environment gotchas (these have already bitten us — don't rediscover them)

- **Non-Latin repo path.** The project lives under a path containing Japanese characters
  (`…\ドキュメント\…`). This crashes the default Windows console codec on `print`. Every
  entry-point script starts with `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`.
  Keep that pattern in any new script that prints.
- **LF→CRLF warnings on commit are expected** and harmless.
- **OneDrive file locks.** If an editor/Excel has a CSV open, atomic-rename edits fail with
  `EPERM`. Close the file and retry.
- **`pip` isn't on PATH** in this shell — use `python -m pip …`.
- **Git:** local repo, remote is `https://github.com/Dawsxn/DrMundo.git`. **Nothing has
  been pushed** — local `main` is ~12 commits ahead of `origin/main`. Do **not** push
  unless the owner asks. Commit style is **Conventional Commits**, one logical change per
  commit (see `git log`).
- **`dr_mundo.db` is gitignored** (build artifact). `data/embeddings.npz` **is committed**.

---

## 5. Architecture & module ownership

```
User (Taglish/English)
   │
   ▼
Streamlit UI  (ui/app.py)  ──HTTP──►  FastAPI  (api/main.py)
                                          │  POST /ask {question, session_id}
                                          ▼
                              DrMundoService.handle()  (agent/service.py)
                                          │
     ┌────────────────────────────────────┼───────────────────────────────────┐
     ▼                                     ▼                                    ▼
 INPUT GUARD                         ReAct LOOP                          OUTPUT GUARD
 (guardrails/input_guard.py)         (agent/loop.py)                     (guardrails/output_guard.py)
 - PII redact (pii.py)               - gpt-4o-mini tool-calling          - every ₱ in prose must
 - topic classify:                   - tools: search_catalog,             tie to a retrieved value;
   cost / medical_advice /             get_covered_cost,                  else prose is rebuilt from
   out_of_scope                        get_outpatient_cost,               grounded fields (format.py)
                                       list_hospitals, ask_user          - outpatient "not covered" note
        session memory (agent/memory.py, FIFO 8 turns)                   - disclaimer enforced
                                          │
                                          ▼
                            db/ layer (RAW parameterized SQL only)
             search.py (embeddings + alias boost) · queries.py · aliases.py · connection.py
                                          │
                                          ▼
                                   dr_mundo.db (SQLite)
```

| Module | Responsibility |
|---|---|
| [`config.py`](config.py) | Paths, model names, cached OpenAI client, UTF-8 stdout fix |
| [`scraper/scrape_case_rates.py`](scraper/scrape_case_rates.py) | One-time PDF→CSV (done) |
| [`data/load_db.py`](data/load_db.py) | Build `dr_mundo.db` from 4 CSVs (explicit schema, FKs, indexes) |
| [`data/build_embeddings.py`](data/build_embeddings.py) | Embed catalog → `embeddings.npz` (L2-normalized) |
| [`db/connection.py`](db/connection.py) | `sqlite3` connection (Row factory, FK on) |
| [`db/queries.py`](db/queries.py) | **All** parameterized queries: `get_covered_cost`, `get_outpatient_cost`, `list_hospitals`, `_resolve_hospital`, `_compute_oop` |
| [`db/search.py`](db/search.py) | Hybrid catalog search: cosine similarity + curated **alias boost** (floor 0.35, boost +1.0) |
| [`db/aliases.py`](db/aliases.py) | Taglish aliases + `SERVICE_EQUIVALENTS` for cross-hospital outpatient grouping |
| [`agent/schemas.py`](agent/schemas.py) | Pydantic v2: tool-arg models + the structured `Answer` |
| [`agent/tools.py`](agent/tools.py) | 5 OpenAI function schemas + validated dispatch registry |
| [`agent/loop.py`](agent/loop.py) | ReAct loop (max 5 iters), richest-grounding tracking, `Answer` assembly |
| [`agent/memory.py`](agent/memory.py) | FIFO `SessionMemory` (max 8 turns, text only) |
| [`agent/format.py`](agent/format.py) | Deterministic grounded renderer (guard fallback) + `DISCLAIMER` |
| [`agent/service.py`](agent/service.py) | Orchestrator: input guard → memory → loop → output guard; returns `ServiceResult` |
| [`agent/prompts/system_v1.md`](agent/prompts/system_v1.md) | Versioned system prompt (routing rules) |
| [`guardrails/pii.py`](guardrails/pii.py) | Regex redaction (email, PH phone, PhilHealth ID, card) |
| [`guardrails/input_guard.py`](guardrails/input_guard.py) | Topic classifier (fails open to `cost`) |
| [`guardrails/output_guard.py`](guardrails/output_guard.py) | Grounding check, not-covered note, disclaimer |
| [`api/main.py`](api/main.py) | FastAPI: `POST /ask`, `GET /health`, `POST /reset`, `/docs` |
| [`ui/app.py`](ui/app.py) | Streamlit chat client (breakdown panel + collapsible trace) |
| [`tests/`](tests/) | 28 unit tests (aliases, queries, guardrails); `conftest.py` auto-builds DB |

---

## 6. Data model (already built & loaded)

4 tables in `dr_mundo.db` (schema in [`data/load_db.py`](data/load_db.py)):

- **`hospitals`** (5 rows): `id, hospital, city` — St. Luke's, Makati Med, The Medical City
  (Ortigas), Chong Hua, Cardinal Santos.
- **`philhealth_procedure_rates`** (4,312 rows): `rvs_code (PK, TEXT), procedure, case_rate (REAL)`
  — the full PhilHealth Annex B catalog.
- **`hospital_procedure_prices`** (34 rows, **Path A**): `rvs_code, hospital_id, price_low,
  price_high, as_of`. Only **10** covered procedures actually have hospital prices (rvs
  codes: `19180, 27130, 27447, 38220, 44950, 47600, 58150, 59409, 59514, 60240` — e.g.
  appendectomy 44950, cholecystectomy 47600, NSD 59409, CS 59514). The other 4,302 covered
  procedures return case-rate-only with a graceful "no hospital price on file" message.
- **`hospital_prices`** (100 rows, **Path B**): `id, hospital_id, category, service,
  price_low, price_high, as_of` — **47 distinct outpatient services** (CT, MRI, X-ray,
  ultrasound, labs, checkups, etc.).

Prices are stored as INTEGER (thousands separators stripped at load). `case_rate` is REAL.

**OOP rules** (`_compute_oop` in [`db/queries.py`](db/queries.py)):
`case_rate ≥ price_high` → fully covered (OOP 0). `case_rate ≥ price_low` → OOP `0 …
price_high − case_rate`. Else → OOP `price_low − case_rate … price_high − case_rate`.

---

## 7. Key design decisions (so you don't "fix" them by accident)

- **Two-layer number safety.** Structured `Answer` fields come straight from tool
  observations in [`agent/loop.py`](agent/loop.py); the LLM only writes prose. The output
  guard then cross-checks every ₱ amount in the prose against the grounded set and, if any
  is unmatched, throws the prose away and re-renders from grounded fields. Result: numbers
  cannot be hallucinated.
- **Hybrid retrieval, not pure embeddings.** Pure cosine mis-ranked Taglish (e.g. "normal
  delivery" matched C-section). Curated aliases add a `+1.0` boost so the right catalog
  entry wins. Don't remove the alias layer.
- **`SERVICE_EQUIVALENTS`** hand-curated grouping lets cross-hospital outpatient comparison
  work when hospitals name the same service differently (e.g. "CT Scan (plain)" vs "CT Scan
  (plain, single region)"). Naive parenthetical-stripping over-merged (plain vs contrast),
  so it's a hand list on purpose.
- **Grounding richness.** The loop keeps the *richest* pricing observation (`_grounding_rank`
  = has-prices, then #hospitals) when the model explores variants — not just the last call.
- **Prompt is versioned** (`agent/prompts/system_v*.md`) specifically to enable Phase 9
  ablation. `DrMundoService(prompt_name=…)` and `run_agent(prompt_name=…)` already thread
  it through end-to-end.

---

## 8. Status — done & verified (Phases 1–8)

✅ Phase 1 PDF scrape → CSV · ✅ Phase 2 DB load · ✅ Phase 3 embeddings + search ·
✅ Phase 4 tools + queries · ✅ Phase 5 ReAct loop (thin slice) · ✅ Phase 6 memory +
orchestration · ✅ Phase 7 guardrails · ✅ **Phase 8 FastAPI + Streamlit**.

Verified live over HTTP (both TestClient and a real `uvicorn` socket):
`GET /health` → 200 with data-readiness; empty/missing question → **422**; appendectomy →
covered, case ₱46,800, ₱75k–220k, 5 hospitals; "how about an MRI?" (same session) → switched
to **outpatient** via memory; "should I get surgery? is it dangerous?" → refused
(`medical_advice`); disclaimer always present. **28/28 unit tests pass.**

---

## 9. ▶️ What's left — build these

### Phase 9 — MLflow monitoring + eval harness

**9a. `monitoring/` — MLflow per-request logging.**
Log one MLflow run per `/ask`: **latency**, **token usage + estimated cost**, **tool-call
trace** (from `ServiceResult.trace`), **errors**, and **prompt version**. Confirm runs show
up in the MLflow UI (`mlflow ui`).
- `ServiceResult` (in [`agent/service.py`](agent/service.py)) already exposes `latency_ms`,
  `trace`, `category`, `pii_found`, `prompt_version`, `output_report`.
- ⚠️ **Token usage is NOT captured yet.** Each OpenAI call in
  [`agent/loop.py`](agent/loop.py) has `resp.usage` (prompt/completion tokens), and the two
  guard calls do too. To log tokens/cost you must **accumulate `resp.usage` and thread it
  out** — e.g. add a `usage` accumulator to `AgentResult`/`ServiceResult`, or wrap
  `get_openai_client()` with a tiny counting proxy. Pick one and be consistent. Estimate
  cost from published gpt-4o-mini / text-embedding-3-small rates (put the rate constants in
  `config.py` or `monitoring/`).
- Cleanest integration point: wrap the call inside `DrMundoService.handle` (or a thin
  decorator around it) so both the API and the eval harness get logging for free. Keep the
  hard constraints intact — logging must not change answers.

**9b. `eval/` — offline eval harness.**
25–30 test prompts across **covered**, **outpatient**, **ambiguous** (should trigger
`ask_user` → `needs_clarification`), and **out-of-scope** (medical_advice / HMO). For each,
assert: catalog **match accuracy**, **path routing** (A vs B), **coverage/OOP correctness**,
**refusal correctness**, and record **latency**. Print a summary table + pass rate.
- Drive it through `DrMundoService.handle` (not the HTTP layer) so it's a plain script.
- **Ablation mode:** run the same suite against 2–3 prompt variants and compare. The plumbing
  exists — just create `agent/prompts/system_v2.md` (and `v3`) and call
  `DrMundoService(prompt_name="system_v2")`. Report per-prompt-version scores side by side.
- Store expected answers as a small dataset (JSON/CSV under `eval/`). Ground-truth numbers
  come from the DB — the 10 priced covered procedures and the 47 outpatient services are the
  reliable set to build cases around (see §6).

### Phase 10 — Docker + final README

**10a. `Dockerfile`** (multi-stage, `python:*-slim`) that runs **both** FastAPI and
Streamlit. Notes:
- `data/embeddings.npz` is committed → **no** embedding rebuild needed in the image (good,
  since that would need an API key at build time).
- `dr_mundo.db` is gitignored → run `python data/load_db.py` **during build** (CSVs are
  committed; no key needed).
- `OPENAI_API_KEY` is needed **at runtime** → pass as an env var, never bake it in.
- Running two processes in one container: use a small launcher (uvicorn in background +
  streamlit foreground) or a process manager. Streamlit's `DR_MUNDO_API_URL` should point at
  the in-container API (`http://localhost:8000`).

**10b. `docker-compose.yml`** — ideally two services (api, ui) sharing a network, with
`OPENAI_API_KEY` from the host `.env`. One-command run: `docker compose up`.

**10c. Final `README.md`** (replace the current scraper-only one — but keep the scraper
section): overview, architecture diagram (mermaid or reuse the ASCII in §5), setup + `.env`
instructions, one-command Docker run, the **MODULE-OWNERSHIP table** (reuse §5), and a
**grader note on RAG**: explain that retrieval here = semantic search over the
*procedure/service catalog* (embeddings) feeding *parameterized SQL* retrieval of grounded
rows — deliberately **not** a document vector store (which the spec forbids), yet still
retrieval-augmented generation in the assignment's sense.

---

## 10. Conventions & verification checklist

- **Conventional Commits**, one logical change per commit. Match the existing granularity.
- New print-scripts get the `sys.stdout.reconfigure(...)` UTF-8 line.
- Don't push to `origin` unless asked.
- Before declaring a phase done, re-run:
  ```bash
  python -m pytest -q          # expect 28+ passing (add tests for new code)
  uvicorn api.main:app --reload   # GET /health → 200; POST /ask a covered + outpatient q
  ```
- Sanity Q&A to eyeball: "magkano ang appendectomy sa Chong Hua?" (Path A),
  "CT scan with contrast price" (Path B), "does my Maxicare HMO cover this?" (refuse),
  "is this surgery safe?" (refuse).

---

*Handoff written at the completion of Phase 8. The next contributor should start with
Phase 9a (MLflow), because the token-usage plumbing it forces will also make the eval
harness's cost reporting (9b) trivial.*
