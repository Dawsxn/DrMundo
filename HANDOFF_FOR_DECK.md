# Handoff: everything you need for the deck

**For:** whoever is building the Final Capstone slides
**From:** the Scope v2 implementation work, 2026-08-15
**Status of the code:** phases 0 to 12 done except the deck itself

You own the deck. This document gives you the numbers, the story behind them, and the
things you should not claim. Everything here is measured unless it says otherwise, and
where a figure is an assumption it says so, because the specification grades that
distinction under value proposition and units.

---

## 1. First, the housekeeping

**The work is on a branch, not on main.** Everything below lives on `scope-v2-build`.
`main` still has only the dataset commits. Someone needs to open the pull request:

```
gh pr create --base main --head scope-v2-build --repo Dawsxn/DrMundo
```

I did not force-push over main and did not touch your two commits.

**The media is in git history and that is going to hurt.** `labrequests/media/` is about
380 MB of PNGs, now permanent unless the history is rewritten with filter-repo or BFG.
Every clone pays for it, and a fetch of that repo took over ten minutes on a normal
connection. The images regenerate from master seed `20260814`, so committing them bought
very little. Rewriting gets more painful the longer it waits, and everyone has to re-clone
when it happens. Worth deciding soon rather than after more commits land on top.

**Two servers, if you want to demo live.** `uvicorn api.main:app` on port 8000 and
`streamlit run ui/app.py` on 8501. Both were verified working end to end with the real
model, not just in tests.

---

## 2. The three headline numbers

The specification asks for at least three quantitative metrics with interpretation. These
are the ones to lead with.

| Metric | Result | What it means |
|---|---:|---|
| Reading F1 (GPT-4.1, n=40) | **77.2%** | Recall 67.2%, precision 90.8%. The system misses tests more often than it invents them |
| Top-1 match accuracy | **91.3%** | Of the labels read, this fraction reaches a real priced MMC catalogue row |
| Hallucinated-peso rate | **0.0%** | Across 40 generated reports, no figure appeared that could not be traced to structure |

The third one is the project's whole thesis, so give it a slide of its own rather than a
row in a table. It is the claim that separates this from a chatbot guessing prices.

Two supporting numbers worth having ready for questions:

- **Resolution, label to code: 100%** (1452 of 1452). With reading held perfect, nothing is
  lost turning a printed label into a catalogue code. This bounds the whole pipeline: no
  reader improvement can be undone by the resolver.
- **Latency: mean 3.6 s, max 7.2 s** against a 20 second budget that was fixed in writing
  before any benchmark ran. If someone asks how the budget was chosen, that ordering is the
  answer.

---

## 3. The RRL story, which is the part with the most marks in it

Component 14 requires a CV or DS model, and section 6.3 requires you to present the review
that led to choosing it. There are two findings and they are both real.

### Finding one: OCR structurally cannot do this task

We ran docTR against a clean form. It read 186 words correctly, which is every printed
label on the page, including the roughly forty tests the doctor did not order. The ground
truth for that form is seven tests.

The point to make on the slide: OCR answers "what text is on this page". We need "which
rows are marked", and a mark is not text. Making the OCR family competitive needs a second
stage that detects checkboxes and measures ink density. That is buildable and it is a
different project.

This is a better RRL slide than a table of accuracy numbers, because it explains *why* one
family was rejected rather than just reporting that it scored lower.

### Finding two: model capability is a threshold, not a gradient

Same image, same prompt, three models:

| Model | Tests reported | Invented | Latency |
|---|---:|---:|---:|
| gpt-4o-mini | 24 | 18 | 17.5 s |
| gpt-4o | 6 | 0 | 7.0 s |
| gpt-4.1 | 6 | 0 | 1.9 s |

Ground truth was seven. GPT-4o-mini did not score slightly worse. It failed in exactly the
way OCR does, listing every label on the page. No prompt work moved it.

Worth saying out loud: gpt-4o-mini is the model the rest of the application uses for chat.
The vision reader deliberately does not inherit that setting. That is a design decision with
evidence behind it, which is the kind of thing the rubric rewards.

### The degradation curve

The evaluation set renders each form in five conditions. This is the graph to put on the
slide.

| Media | Recall | Invented |
|---|---:|---:|
| clean | 81.7% | 3 |
| scan | 74.1% | 3 |
| photocopy, 1st generation | 62.5% | 3 |
| photocopy, 3rd generation | 61.4% | 6 |
| fax | 50.0% | 2 |

Half the tests on a faxed form are missed. Do not hide this. It is the clearest statement of
where the system's limit is, and stating it yourself is much stronger than being asked.

---

## 4. Things you should NOT claim

These will get caught in questions if you overstate them.

**Do not say it works on real doctor's requests.** Every image in the evaluation set is
synthetic. There is no real-slip arm at all. The numbers describe generated forms, not a
phone photograph of a real request in bad light.

**Do not say the full waterfall runs from an image.** Every form in the dataset is a
laboratory request and none names a procedure, so the PhilHealth leg never fires from the
image path. It fires from the conversation. The thesis is honestly stated as "images plus one
question", not "images alone".

**Do not present the HMO figures as anyone's actual policy.** They come from Maxicare's
published individual and family tiers. Most Philippine coverage is employer-negotiated and
will match no public tier. The app labels this on screen and the deck should too.

**Do not claim cancelled-row handling is perfect.** One cancelled row in eleven was billed,
because the vision model misread a strike-through. The pricing logic never bills a cancelled
row, and that is tested, but the reader can still mislabel one. This is the failure that
takes money from a patient, so name it as the top open issue.

**Do not quote clean-form recall as 100%.** An early three-image spot check gave that. The
larger 40-form run gave 81.7%. Use the larger number.

---

## 5. The sanity check the specification asks for

Section 5 asks whether ChatGPT or a Google search would suffice. The answer is no and it is
provable, which makes a good slide:

- MMC's price list only returns data to a POST search. Fetched plainly, the page is empty.
  A general chatbot cannot see these prices.
- The mapping from MMC's catalogue names to PhilHealth RVS codes does not exist in public.
  Ours is 51 mappings made by hand, and a wrong one moves an estimate by tens of thousands
  of pesos.
- Reading a slip requires deciding which rows carry a mark and which are struck through.
  That is not a retrieval problem.

Also pre-empt this one, because a grader may raise it: the rubric lists "safety-critical
workflows without a human in the loop" as a poor fit for agentic AI. Dr. Mundo estimates
prices. It does not triage, diagnose, or recommend treatment, and the input guardrail
refuses medical advice outright. Say that on a slide rather than in an answer.

---

## 6. Value proposition and units

The specification is specific about qualifying units, so keep the three categories separate.

**Measured.** Every laboratory panel MMC publishes costs less than buying its component
tests separately, by ₱60 to ₱1,400 depending on the panel and which end of the price range
applies. This comes from the committed dataset and has a test behind it.

**Assumed, and label it as an assumption on the slide.** Pricing six tests by telephone takes
roughly 30 minutes, allowing for transfers between departments. We did not measure this. Dr.
Mundo answers in a mean of 3.6 seconds.

**Intangible, and label it as intangible.** Avoided surprise at admitting. Being told your
bill is twice what you brought is a different kind of harm from losing half an hour, and we
declined to invent a peso figure for it. The specification explicitly allows intangibles if
you flag them, so flag it.

---

## 7. Architecture slide

The specification wants a diagram showing where the CV model plugs into the agent pipeline.
This is the shape:

```
 image ──► redact ──► read ──► resolve ──► triage ──► price ──► waterfall ──► report
           raster     VLM      taxonomy    4 buckets   MMC       pure Python
                                                                            │
 text ───► input guard ──► ReAct loop ──► tools ──► output guard ────────────┘
```

Three things worth calling out on that slide:

1. The text path is the midterm system, unchanged. This is an extension, not a rewrite.
2. The waterfall is pure Python with no model involvement, which is why every peso is
   auditable.
3. Both paths converge at the output guardrail, which is what produces the 0% hallucinated
   figure.

---

## 8. Component ownership

Team of three needs six components, each member owning at least two. The build assigns nine.

| Member | Components | Where in the code |
|---|---|---|
| A | **14 CV/DS**, 2 Disambiguation, 5 Guardrails | `vision/`, `guardrails/pii.py`, needs-confirmation routing |
| B | 3 RAG, 12 Advanced RAG, 10 SQL/Planning | `db/`, `pricing/` |
| C | 9 ReAct/Tool use, 13 Evals, 8 LLMOps | `agent/`, `eval/`, MLflow |
| team | 1 Prompting, 4 Memory, 6 UI, 7 API | carried from the midterm |

Adjust the names to who actually did what. Everyone has to be able to explain their own
components in questions, so pick the split that matches reality rather than the one that
looks tidiest.

---

## 9. Demo

**Use laparoscopic cholecystectomy or lipid profile.** Not appendectomy: MMC publishes
professional fees for it but no operating-room package, so it produces an almost empty
answer. The midterm demo was built on appendectomy and no longer works well.

**A good live sequence:**

1. Upload a request slip. The report appears immediately, labelled as being before any HMO.
   Point out that it asked nothing first.
2. Answer one refine question, for example the HMO plan and remaining balance. The number
   drops. Point out there was no second upload.
3. Show the buckets: priced, not priced, please confirm, crossed out. The "not priced" bucket
   is the honesty story, and "crossed out" is the one that saves the patient money.

**Have a fallback recording.** The specification says a failed live demo affects the
presentation score and that you should disclose a fallback upfront. The reading stage makes
a network call, so a bad connection is a real risk.

---

## 10. Where the numbers live

Everything above can be regenerated:

```
python -m eval.suite --offline          # deterministic layers, free
python -m eval.suite --limit 40         # includes the vision model, costs API calls
python -m eval.resolver_bench           # resolution and the section-heading ablation
python -m eval.reader_bench --limit 25  # the RRL table
```

Raw results are committed at `eval/results_v2.json` and `eval/rrl_gpt41.json`. The full
technical write-up is `TECHNICAL_WRITEUP.md` and `TECHNICAL_WRITEUP.pdf`, and it covers the
same ground in more depth if you need wording for a slide.

The design decisions and the reasoning behind them are in `PLAN_SCOPE_V2_BUILD.md`, section 2
in particular. If a grader asks why something was built a certain way, the answer is usually
written down there.
