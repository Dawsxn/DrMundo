# Kickoff prompt (paste this into a fresh Claude Code session)

> Give this whole block to your Claude as the first message, from inside the `DrMundo/`
> repo. It tells Claude exactly how to orient and what to build. Everything it needs is in
> [`HANDOFF.md`](HANDOFF.md).

---

You're taking over an in-progress university capstone called **Dr. Mundo** — an agentic AI
cost estimator for Philippine healthcare (answers plain-language / Taglish questions about
what medical procedures and outpatient services cost, using only a local SQLite database).
The project is **complete and verified through Phase 8**. Your job is to finish **Phase 9**
and **Phase 10**.

**Step 1 — Orient before touching anything.**
Read [`HANDOFF.md`](HANDOFF.md) in this repo end to end — it's the source of truth
(architecture, module-ownership map, data model, design decisions, environment gotchas, and
the detailed specs for the remaining phases). Then read these files so you understand the
seams you'll extend: `agent/service.py`, `agent/loop.py`, `agent/schemas.py`,
`agent/tools.py`, and `db/queries.py`. Give me a 5-line summary of the current state and
your plan, and ask me any clarifying questions **before** writing code.

**Step 2 — Verify the environment is healthy** (so you know your baseline works):
```bash
python -m pip install -r requirements.txt
python data/load_db.py          # builds dr_mundo.db (gitignored); no API key needed
python -m pytest -q             # expect 28 passing
```
For anything that hits the model you'll need `OPENAI_API_KEY` in `.env` (copy `.env.example`).
Note: this repo lives under a path with Japanese characters, so any new print-script must
start with `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` (see existing scripts).

**⛔ Non-negotiable constraints — the grade depends on these. Do not break them:**
1. The LLM must **never** generate SQL. All DB access stays as pre-written parameterized
   `sqlite3` queries in `db/queries.py`.
2. **No invented numbers** — every figure must come from a DB row. The two-layer grounding
   (structured `Answer` fields + output guard) must stay intact.
3. No HMO/private insurance, no policy/eligibility Q&A, **no document vector store**, no
   live external lookups at answer time, and **no medical advice**.
Your monitoring/eval/Docker work must be *additive* — it must not change answers.

**Step 3 — Build Phase 9, then Phase 10** (full specs are in `HANDOFF.md` §9; summary here):

- **Phase 9a — MLflow monitoring (`monitoring/`):** one MLflow run per `/ask`, logging
  latency, token usage + estimated cost, tool-call trace, errors, and prompt version.
  ⚠️ **Do this first:** token usage isn't captured yet — each OpenAI call in `agent/loop.py`
  (and the two guard calls) has `resp.usage`; thread it out (accumulate into
  `AgentResult`/`ServiceResult`, or wrap the client). This same plumbing makes 9b's cost
  reporting free. Confirm runs appear in `mlflow ui`.
- **Phase 9b — eval harness (`eval/`):** 25–30 prompts across **covered / outpatient /
  ambiguous (→ needs_clarification) / out-of-scope**. Drive it through
  `DrMundoService.handle` (not HTTP). Report match accuracy, path routing (A vs B),
  coverage/OOP correctness, refusal correctness, and latency. Add an **ablation mode**: run
  the suite against 2–3 prompt variants (`agent/prompts/system_v2.md`, `v3`) via
  `DrMundoService(prompt_name=...)` and compare. Ground-truth numbers come from the DB — the
  10 priced covered procedures and 47 outpatient services (see `HANDOFF.md` §6).
- **Phase 10 — Docker + final README:** multi-stage `Dockerfile` (python slim) running
  **both** FastAPI + Streamlit; run `python data/load_db.py` at build time (DB is
  gitignored, CSVs are committed); `embeddings.npz` is already committed so don't rebuild it;
  pass `OPENAI_API_KEY` at runtime only. Add `docker-compose.yml` (one-command
  `docker compose up`). Rewrite `README.md` with overview, architecture diagram, setup +
  `.env`, one-command Docker run, the module-ownership table, and a grader note explaining
  why the catalog-embedding + parameterized-SQL retrieval counts as RAG *without* a document
  vector store.

**Working style:**
- **Conventional Commits**, one logical change per commit, matching the existing granular
  history (`git log`). Add tests for new code and keep `pytest` green.
- **Do not `git push`** — the repo is intentionally local-only (~13 commits ahead of origin);
  leave pushing to the owner.
- **Checkpoint with me** after Phase 9 and again after Phase 10 — show what you built, how
  you verified it, and the test results — before moving on.
- Before declaring a phase done, re-run `pytest` and smoke-test the API (`GET /health`, plus
  a covered and an outpatient `/ask`).

Start with Step 1: read `HANDOFF.md`, summarize the state, and ask your questions.
