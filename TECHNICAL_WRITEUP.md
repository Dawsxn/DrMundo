# Dr. Mundo: Technical Write-up

**Course:** Introduction to Agentic AI (STAI100), Final Capstone
**Team:** [Member 1], [Member 2], [Member 3]
**Repository:** https://github.com/Dawsxn/DrMundo
**Date:** August 2026

---

## Abstract

Dr. Mundo estimates what a Filipino patient should prepare for a hospital visit. The user
photographs a doctor's laboratory request; a vision model reads which tests were ordered, a
resolver turns those labels into catalogue codes, and a deterministic pricing layer produces a
peso range after PhilHealth and HMO coverage. The defining property is that no number is
invented. Every peso traces to a row in a local database built from Makati Medical Center's own
published price list, and an output guardrail rejects any figure in the prose that cannot be
tied back to that structure.

This version narrows the midterm's five-hospital scope to one hospital with real published
prices, and adds a computer vision stage as the primary input path. Measured on 260 labelled
request forms: resolution from label to code is lossless, 91.3% of read labels reach a priced
catalogue row, and the hallucinated-peso rate is zero across 40 generated reports. The reading
stage is the weak link, and Section 6 reports exactly where it fails and why.

A second document type was added late and changed the largest number in the system. Philippine
HMO plans publish a headline benefit limit, but a real schedule of benefits caps individual
procedures well below it, and on the expensive ones that smaller cap is the one that binds.
Modelling the headline limit as the only ceiling credited a ₱150,000 plan with ₱107,685 towards
a gallbladder operation its own schedule caps at ₱35,000. The system now reads the patient's
own benefits document, applies the ceilings in the order they actually bind, and where no
schedule is available says plainly that the figure is the most the plan could pay rather than
what it will.

---

## 1. Business case

### 1.1 The problem

Philippine hospital prices are not published in any form a patient can act on. Most private
hospitals publish nothing at all. A patient handed a request slip for six tests has no way to
find out what those six tests cost without phoning the hospital, being transferred between
departments, and writing figures on the back of the slip. PhilHealth's case rates add a second
layer of opacity: the subsidy is real and often substantial, but which procedures attract one,
and how it interacts with an itemised bill, is not something a patient can reasonably work out.

The result is that people arrive at admitting with no idea whether they can afford the day.

### 1.2 Users

The direct user is a patient or a family member holding a request slip and trying to budget.
The same engine has a business audience: HMO member services, hospital patient relations, and
health-tech products that need a pricing assistant they can defend. That is where willingness
to pay sits, and it is also where a wrong number is expensive, which is the property this
system is built around.

### 1.3 Value proposition and units

We claim two things, and we separate what we measured from what we assumed.

**Measured.** For every laboratory panel MMC publishes, buying the panel costs less than buying
its component tests separately. The saving runs from ₱60 to ₱1,400 depending on the panel and
which end of the price range applies. This comes straight from the committed dataset and is
checked by a test. A patient who does not know this pays the difference.

**Assumed, and flagged as an assumption.** Pricing six tests by telephone takes roughly 30
minutes of a patient's time, allowing for hold time and transfers between departments. We did
not measure this and it should be read as a working estimate rather than a finding. Dr. Mundo
answers in a mean of 3.6 seconds. On that assumption the time saved is about 0.5 hours per
episode. For a household, an episode is a handful of times a year, so the annual time saving is
small in absolute terms and the value is concentrated elsewhere: in knowing the number before
you are standing at the counter.

**Intangible, and labelled as such.** The larger benefit is avoided surprise, and we cannot put
a defensible peso figure on it. Being told at admitting that a bill is twice what you brought
is a different kind of harm from losing half an hour. We are not going to invent a number for
it.

### 1.4 Why this needs an agent

The specification asks whether a well-crafted prompt would suffice. It would not, and we can
show why rather than assert it.

MMC's price list is only reachable by POST to a search endpoint that returns an empty page if
you fetch it plainly. A general chatbot cannot see it. The mapping from MMC's catalogue names
to PhilHealth's RVS codes does not exist anywhere in public; ours is 51 mappings made by hand,
and getting one wrong changes an estimate by tens of thousands of pesos. Reading a request slip
requires deciding which rows carry a tick and which are struck through, then resolving
abbreviations that are ambiguous without their section heading. Any of those steps done from
memory produces a confident, wrong, unverifiable figure.

The model orchestrates and explains. The numbers come from the database.

---

## 2. What changed since the midterm

The midterm covered five hospitals with indicative price ranges. This version covers one, with
figures scraped from Makati Medical Center's own published list, every row carrying MMC's
catalogue item code so any number on screen can be checked by hand. The dataset grew from about
134 priced rows to roughly 2,400.

Two midterm constraints were reversed. HMO is now in scope, and outpatient items can carry
coverage arithmetic where a case rate applies.

HMO began as a conversational input: the patient names their plan and we look up what Maxicare
publishes for that tier. That is still the fallback, and it is weaker than it looks, because a
published tier gives two numbers where a real policy has forty. The system now also accepts the
patient's own Summary of Benefits, Certificate of Coverage or benefit booklet as an upload, and
reads the limits out of it. Section 4 covers what that changes in the arithmetic.

The rule that governed the rebuild, and that still governs the code: if a number was never
published, we say so. That is why appendectomy has no package price in this system, why 19
procedures have no PhilHealth case rate, and why nine taxonomy codes report as unpriced. Those
gaps are exposed rather than filled.

---

## 3. Review of related literature and model selection

The vision stage is the component the course requires, so the choice of model is the part of
this project with the most literature behind it and the most measurement in front of it.

### 3.1 The candidates

We considered two families.

**Optical character recognition.** Tesseract as a baseline, PaddleOCR and docTR as modern
detector-plus-recogniser pipelines, and TrOCR as a transformer approach aimed at handwriting.
These are mature, run locally, cost nothing per page, and keep the image on the machine. docTR
in particular pairs a text detector with a CRNN recogniser and is well suited to structured
documents.

**Vision language models.** GPT-4o-mini, GPT-4o and GPT-4.1. These read an image and emit text
directly, understand layout without an explicit detector, and can be asked questions about what
they see rather than only what characters are present.

### 3.2 The finding that decided it

We ran docTR against a clean form from our evaluation set. It read 186 words correctly. That is
every printed label on the page, including the roughly forty tests the doctor did not order.
The ground truth for that form is seven tests.

This is not a tuning problem. OCR answers the question "what text is on this page". The question
we need answered is "which rows are marked", and a mark is not text. Making the OCR family
competitive would require a second stage: detect each checkbox, measure ink density inside it,
associate it with the nearest label. That is a real and buildable system, and it is a different
project from the one the course window allows.

We report this as the central trade-off rather than hiding it, because it is the most useful
thing we learned. OCR is the right tool when the information is the text. It is the wrong tool
when the information is a pencil stroke.

### 3.3 Model capability is a threshold, not a gradient

Having chosen the vision-language family, we compared three models on the same image with the
same prompt.

| Model | Tests reported | Invented | Latency |
|---|---:|---:|---:|
| gpt-4o-mini | 24 | 18 | 17.5 s |
| gpt-4o | 6 | 0 | 7.0 s |
| gpt-4.1 | 6 | 0 | 1.9 s |

Ground truth was seven. GPT-4o-mini did not merely score worse; it failed in the same way OCR
does, listing every label on the page. Mark detection appears to be a capability the smaller
model does not have, and no amount of prompt work moved it. GPT-4o and GPT-4.1 both handled it,
and GPT-4.1 was roughly four times faster.

This mattered practically because gpt-4o-mini is the model the rest of the application uses for
chat. The vision reader deliberately does not inherit that setting.

### 3.4 The latency budget

We fixed a budget of 20 seconds from upload to rendered report before running any benchmark,
and wrote it into the plan. The reasoning was that the demo runs live in front of a class, and
attention goes after about twenty seconds of silence; a patient in a hospital lobby is no more
patient than an audience.

Fixing it in advance matters. Choosing the threshold after seeing the results would have made
the rejection of any candidate unfalsifiable, and a grader asking how we picked the number
would have deserved a better answer than "it is where the winner happened to land".

GPT-4.1 measures a mean of 3.6 seconds and a maximum of 7.2 across 40 forms, comfortably
inside. TrOCR was not benchmarked; on CPU, per-line transformer inference over a dense form
would very likely exceed the budget, but we did not measure it and we are not going to claim a
result we do not have.

---

## 4. Architecture

### 4.1 The pipeline

```
 slip ────► redact ──► read ──► resolve ──► triage ──► price ──► waterfall ──► report
 image      raster     VLM      taxonomy    4 buckets   MMC        ▲            HTML/PDF
                                                                   │                │
 benefits ► text or vision ──► plan limits ────────────────────────┘                │
 PDF                           sub-limits, MBL, pre-existing                        │
                                                                                    │
 text ───► input guard ──► ReAct loop ──► tools ──► output guard ────────────────────┘
```

The text path is the midterm system and is unchanged. The two document paths are separate and
meet at different places: a slip decides what is being bought, and joins the pipeline at the
front; a benefits document decides what the plan pays for it, and joins at the waterfall. All
three converge at the output guardrail.

The separation matters beyond the diagram. A slip is a turn in a conversation and stops being
true when the next one arrives. A benefits document describes the patient, governs every figure
afterwards, and survives a new slip. Early on both were uploaded into the chat box, and the
result was that uploading a slip discarded the benefits document that had been read a minute
earlier, then asked the patient which HMO plan they had.

### 4.2 The stages

**Redaction** runs first and destroys pixels rather than drawing an annotation over them. A
redacted PDF that still carries the original text underneath is worse than no redaction because
it looks safe.

**Reading** turns an image into marks: a label, its section heading, and whether the row is
struck through. The reader is an interface with several implementations, so a vision model and
an OCR pipeline can be scored on identical terms. An oracle reader that returns ground truth is
used to measure everything downstream with reading held perfect.

**Resolution** maps a printed label to a taxonomy code. The rules come from the taxonomy's own
matching block rather than from us: no substring matching, fuzzy matching to an edit distance
of one, and an explicit list of code families that must never fuzzy-match each other. LDL and
LDH are one character apart and are unrelated tests.

**Triage** puts every item in exactly one of four buckets: priceable, unpriced,
needs-confirmation, or cancelled. An ambiguous label and an unresolved label both go to
needs-confirmation. We read something; the patient is owed a question about it rather than a
silent omission.

**Pricing** joins a taxonomy code to an MMC catalogue row. MMC publishes emergency-room,
point-of-care, specimen and extent variants of nearly every test, so the join ranks candidates
instead of demanding a unique match: avoid ER pricing because a request slip is not an
emergency, respect specimen because a serum creatinine is not a urine creatinine, and prefer
the least qualified name so an unqualified order does not silently buy a richer study.

**Benefits reading** turns a schedule of benefits into a set of limits. It is a different
problem from reading a slip and uses a different strategy. A slip asks which rows carry a mark,
which is a perception question that no text extractor can answer. A booklet asks what the
figures mean, and the text is usually machine readable; the difficulty is that "up to
PhP15,000.00" appears eleven times on one page and each occurrence governs something else. So
the reader tries text first and falls back to the vision model only when a document turns out
to be a scan.

**The waterfall** is pure Python with no model involvement. Gross, then the senior and PWD
reduction, then PhilHealth, then HMO, then what to prepare. Every leg is a range rather than a
scalar, because a deduction is the smaller of an entitlement and what is left to pay, and what
is left differs between the ends of a price range.

The HMO leg is the part that changed most. It applies three ceilings, and the order is the
reverse of the intuitive one. The procedure's own sub-limit binds first, per item, because it
does not depend on what the rest of the bill costs. Outpatient laboratory and imaging then draw
against a separate pool of their own. The overall benefit limit binds last, across everything.
Run in the intuitive order, a ₱35,000 cholecystectomy cap against a ₱150,000 limit yields
₱150,000, which is four times what the plan will pay.

### 4.3 Grounding

Two layers, both inherited from the midterm and both extended.

Structured fields come only from tool results. The model never produces a number; it selects
which typed query to call.

The output guardrail then extracts every peso figure from the prose and checks it against the
structured estimate. Anything it cannot find causes the prose to be discarded and rebuilt
deterministically. Extending this to multi-item reports was necessary and easy to get wrong:
the original check looked only at a flat set of scalar fields, so a report quoting a range per
item would have had every one of those figures declared ungrounded, and the guardrail would
have deleted the itemisation while leaving something that still looked like a report.

---

## 5. Methodology and design decisions

**The model never writes SQL.** It chooses among typed, parameterised queries and supplies
arguments that Pydantic validates. All SQL lives in one module.

**Ambiguity resolves toward the higher out-of-pocket figure.** Where two readings are
defensible, we take the one that leaves the patient expecting to pay more. Over-preparing is
recoverable. Being short at the counter is not.

**Discount before PhilHealth.** The senior and PWD reduction is VAT exemption followed by 20%,
a single multiplier of 0.714286. It is applied before the case rate is deducted, because the
two orderings do not commute: on a ₱100,000 procedure with a ₱46,800 case rate they differ by
about ₱13,371. The multiplier is one named constant with a test asserting it is not 0.80, since
dropping the VAT exemption is the version of this bug that costs money.

**Deductions clamp per item.** A ₱60,450 case rate against a ₱40,000 procedure covers ₱40,000.
The excess is not a credit against the patient's blood tests.

**A partial price can never be reported as full coverage.** Four MMC rows carry a case rate
larger than MMC's own ceiling price, which means MMC is billing part of an episode rather than
all of it. Those rows are flagged, out-of-pocket is reported as uncomputable rather than zero,
and the phrase "fully covered" is blocked.

**Cancelled rows are shown and never charged.** A struck-through row is a test the doctor
withdrew. Rendering it visibly, rather than dropping it, lets the patient catch a misread: if
the reader wrongly cancels something they actually need, they can see it and say so.

**Room and board never enters a total.** Length of stay cannot be known from a request slip,
and assuming one would invent the largest number on the page. It appears as a per-day line
outside the total.

**The first answer asks nothing.** Somebody who has just uploaded a slip wants a figure, not an
intake form. The report appears immediately, labelled as being before any HMO, and every
question after that is an offer to improve a number they already have. Abandoning halfway still
leaves them with something true.

**An HMO figure without a schedule behind it is labelled a ceiling.** Where we know only the
plan's headline limit, the most we can honestly say is that the plan will pay no more than a
certain amount. The report says exactly that, and the coverage panel says it continuously. This
was the cheapest correction we made and probably the most valuable, because it makes the figure
honest for every patient who never uploads anything.

**A field the document does not state stays empty.** The reader returns null rather than
supplying what a plan of that tier usually carries. An invented outpatient ceiling is
indistinguishable from a real one by the time it reaches a patient as a peso figure, and the
patient has no way to audit it. One of the three test documents is a one page human resources
advisory that states a plan, a limit and nothing else, and it exists specifically to catch a
reader that fills in the rest.

**An unmatched limit is discarded, not attached to the nearest row.** A schedule says
"Laparoscopic cholecystectomy" where the hospital says "LAPAROSCOPIC CHOLECYSTECTOMY PACKAGE",
so the two vocabularies never match exactly and something has to bridge them. The bridge
requires a match at a word boundary, and where nothing matches, the cap is dropped. This rule is
shared with the catalogue join, because the same carelessness there once matched the surface
form "Crea" inside "panCREAs" and priced a ₱740 blood test as a ₱16,800 study.

**Facts about the paperwork are cleared; facts about the person are kept.** A new slip means new
tests, a new room and possibly a new operation. It does not mean a new HMO, a new age, or newly
lapsed PhilHealth contributions. Getting this split wrong is what discarded an uploaded benefits
document the moment the patient uploaded their slip. Whether a condition is pre-existing is
cleared with the slip, because it belongs to the condition rather than to the person.

**Where the professional fee comes out of the same limit, we say so and decline to size it.**
Several schedules draw the surgeon's and anaesthesiologist's fees from the same benefit limit we
are crediting against the hospital bill. Professional fees are out of scope and the hospital's
published data covers clinic consultations rather than surgeons' fees by procedure, so we have
no defensible figure. The report states that part of the limit is already spoken for rather than
inventing an amount for it.

---

## 6. Experiments and evaluation

The suite is organised in five layers so that a failure identifies its own stage: unit
arithmetic, resolution, matching, reading, and end-to-end grounding, plus a model-scored
honesty rubric. It runs offline against an oracle reader for the deterministic layers and
against the real model for the reading layer.

### 6.1 Headline results

| Metric | Result | Reading |
|---|---:|---|
| Resolution, label to code | **100%** (1452/1452) | With reading held perfect, resolution loses nothing |
| Top-1 match, code to priced row | **91.3%** (1284/1407) | The remaining 8.7% are tests MMC publishes no price for |
| Hallucinated-peso rate | **0.0%** (0/40 reports) | No figure appeared that could not be traced to structure |
| Reading F1, GPT-4.1 | **77.2%** (n=40) | Recall 67.2%, precision 90.8% |
| Cancelled rows billed | 1 of 11 | The failure that costs money, and it is not yet zero |
| Benefits fields read | **100%** (14/14) | Across three documents of different shapes |
| Benefits sub-limits read | **100%** (20/20) | The figures that bind before the overall limit |
| Benefits fields fabricated | **0** (of 3 unstated) | The score that matters more than the other two |
| Latency | mean 3.6 s, max 7.2 s | Against a 20 s budget fixed in advance |

### 6.2 Reading degrades with media quality, as designed

The evaluation set renders each form in five conditions of increasing difficulty. Recall tracks
them closely.

| Media | Recall | Invented |
|---|---:|---:|
| clean | 81.7% | 3 |
| scan | 74.1% | 3 |
| photocopy, first generation | 62.5% | 3 |
| photocopy, third generation | 61.4% | 6 |
| fax | 50.0% | 2 |

Half the tests on a faxed form are missed. This is the honest ceiling of the current system and
the clearest target for future work. Precision holds up much better than recall, which means
the failure mode is omission rather than fabrication. For a cost estimator that is the better
direction to fail in, though it is still a failure: a missed test is a bill the patient did not
budget for.

Note that clean-form recall here (81.7%, n=8) is lower than the 100% we saw in an earlier
three-image spot check. Eight forms per condition is a small sample and these figures carry wide
error bars. We report the larger run rather than the flattering one.

### 6.3 Section headings are worth measuring

The taxonomy warns that a bare "KUB" appears under both Ultrasound and X-Ray on the same sheet.
We tested how much the heading is actually worth by withholding it.

Resolution falls from 100% to 96.8%. Forty-six labels become ambiguous: Thyroid eighteen times,
Liver Profile fourteen, KUB ten, Breast four. Critically, none become wrong. The system asks
instead of guessing, which is the behaviour we wanted and now have evidence for rather than
hope about.

### 6.4 Safety behaviours

On the taxonomy's five explicitly ambiguous abbreviations, the system asked five times out of
five and priced nothing. Across the full set, no cancelled row reached the pricing layer when
reading was held perfect; the one billed cancellation in the headline table came from the vision
model misreading a strike-through, not from the pricing logic.

### 6.5 The honesty judge

Numbers being right is not the same as a report being honest. A model scores each generated
report against five criteria: does it name unpriced items and say they are excluded, does it
avoid claiming full coverage against a partial price, does it label HMO figures that came from a
published tier rather than the patient's own certificate, does it show cancelled rows, and does
it avoid reading as a quotation. The judge sees the report and the structured estimate but never
the ground truth, so it grades prose against structure.

Eight reports scored 100% on all five criteria. The sample is small and the judge shares a
family with the model being judged, which is a real limitation of this method and not one we
can design away at this scale.

### 6.6 The benefits reader, and the score we care about

Real benefit booklets cannot go in a public repository. They are somebody's actual policy, they
name a member, and the copies circulating on document sharing sites are re-uploads of employer
contracts that were never meant to be public. We generated three synthetic ones instead, from a
committed script so they can be rebuilt.

What is real in them is sourced and what is invented is labelled. The plan names, benefit limits
and room entitlements come from Maxicare's own published tiers. The shape of the documents, the
section order, the recurring "subject to MBL" phrasing, the table of per-procedure caps, and
pre-existing cover scaled by the number of enrolled members, was read off the Bureau of Customs'
published HMO procurement contract. Government agencies have to publish a full schedule of
benefits so bidders can price against it, which makes procurement documents the one reliable
public source for this material. Every peso figure other than a benefit limit is invented, and
every page of every specimen carries a banner and a watermark saying so.

The three cover deliberately different shapes. A two page certificate of coverage is mostly
prose with one table. A three page corporate summary states three sets of figures for three
employee categories in a grid, and the reader is asked for one of them. A one page human
resources advisory states four facts and omits everything else.

| Document | Fields | Sub-limits | Fabricated | Mode | Time |
|---|---:|---:|---:|---|---:|
| Certificate of coverage, 2pp | 6/6 | 8/8 | 0 of 0 unstated | text | 6.2 s |
| Corporate summary, 3pp | 6/6 | 12/12 | 0 of 0 unstated | text | 3.0 s |
| Human resources advisory, 1pp | 2/2 | 0/0 | **0 of 3 unstated** | text | 1.1 s |

The last cell is the one we would defend first. A reader scoring perfect recall while inventing
one outpatient ceiling is worse than a reader scoring 80% and inventing nothing, because the
invented figure looks exactly like a real one on the report. The benchmark therefore scores
fabrication separately rather than folding it into an accuracy number, and the sparse document
exists to give it something to count.

Two things this evaluation does not establish. All three documents are synthetic, so none of
these figures describe a photograph of a real booklet, and the corporate specimen was written by
us from a real contract's structure rather than being a real contract. And the corporate
document states a co-insurance of 20% on charges above ₱80,000 for one employee category, which
the reader correctly declined to record, because our plan model holds a flat percentage and
cannot express a threshold. Flattening it would have quietly cut coverage on small bills.

---

## 7. What we would tell the next team

**The gate on the evaluation dataset paid for itself.** Its documentation says to run about ten
images past a real model and look at the output before drawing conclusions from a full sweep.
We did, and the first model we tried returned 24 tests where seven were ordered. Running the
full benchmark first would have produced a plausible-looking F1 for a configuration that was
structurally broken.

**Write the failing case down before you fix it.** The most valuable single test we have asserts
that a chest x-ray code reaches the right MMC row. It failed, and the failure revealed that our
own hand-written mapping quietly dropped a lateral view and would have understated every chest
x-ray on an AP-and-lateral order. The test was wrong about what it expected and right about
looking.

**The dangerous bugs are the ones that return a number.** A read failure originally produced an
empty slip, which priced cleanly to ₱0. "Prepare ₱0" reads like an answer. It now raises. The
same shape of bug appeared three times: an empty result, a partial price, and a truncated
x-ray order all produced confident output that happened to be wrong, and none of them looked
like errors.

**The guardrail will bite the hand that feeds it.** When the system first read a benefits
document and reported the limits it found, the output guardrail deleted the sentence and
replaced it with an empty report. It was right to: those figures came from the patient's plan,
and the grounded set only contained figures from the priced estimate. The fix was to ground the
plan as well, and to carry it alongside the estimate rather than inside it, because the estimate
is deliberately withheld while questions are still being asked. A guardrail strict enough to be
worth having will occasionally block something true, and the fix is to widen what counts as
grounded rather than to loosen the check.

**Version control will corrupt your data if you let it.** The repository had line ending
conversion switched on and nothing marking PDFs as binary. Committing was fine and cloning was
not: the files opened on the machine that made them and failed on the machine that received
them, which is the exact path this dataset takes to a teammate. Two documents were already
damaged in the working tree before we noticed. Binary types are now declared, and the check is a
fresh clone that opens every file rather than a green test run.

**Limits we did not solve.** Every image in the evaluation set is synthetic, so none of these
numbers describe a phone photograph of a real slip in bad light. Every form is a laboratory
request, so no form names a procedure and the PhilHealth leg is never exercised from an image;
it fires from the conversation instead. Fax and third-generation photocopy recall sits near
half.

On the coverage side: accreditation could not be verified from any first-party source, since
Maxicare publishes a live directory rather than a citable list, so the report states the
assumption and tells the patient how to check it rather than asserting a status. A sub-limit
attaches to a priced procedure, so an operation named only in conversation gets no cap, which is
narrower than it appears. Threshold co-insurance is not representable. And the professional fee
drawn from the same benefit limit is acknowledged but not sized.

**What we would do next, in order.** Add a checkbox detector so the OCR family becomes a real
comparison arm rather than a documented rejection. Collect a small set of real, redacted slips
so there is a non-synthetic denominator, and the same for benefits documents, which are harder
to obtain because they identify a member. Push cancelled-row detection to zero, since that is
the one failure that takes money out of somebody's pocket rather than merely omitting a line.
Then represent threshold co-insurance and per-category limits properly, since a group contract
is the common case in the Philippines and we currently read it by taking the lowest figures
stated.

---

## 8. Deployment

The application runs as two processes: a FastAPI service exposing `/ask`, `/ask-slip`,
`/ask-benefits`, `/coverage`, `/choice`, `/refine`, `/reset` and `/health`, and a Streamlit
interface. Both are containerised, and the image needs no OCR weights because the reading stage
is an API call. Per-request token usage, cost and latency are logged to MLflow, and the reading
stage reports its own time separately so it can be compared against the latency budget rather
than hidden inside a total.

Uploads are validated on type and size, written to a temporary file outside the repository, and
deleted in a finally block. The temporary name is random by design, because a patient's own
filename can carry their name. This matters more for a benefits booklet than for a slip, since a
certificate of coverage names the member on its first page.

The interface has one conversation and no sidebar, with a single exception: coverage lives in a
persistent card above the conversation rather than in the message history. It holds the upload,
shows the plan and its limits, and states continuously whether the figures are built on the
patient's real limits or on a ceiling. It is backed by its own endpoint rather than by the last
reply, because a plan may have arrived from a document, from answering a question, or ten turns
earlier, and only the session knows which.

Nothing is persisted to disk. Health questions, an extracted slip, a stated benefit balance and
an uploaded booklet all live in memory for the session and are dropped with it.

---

## 9. Conclusion

Dr. Mundo answers a question a Filipino patient cannot currently answer for themselves, and it
answers it without inventing anything. The arithmetic is deterministic and auditable, the
grounding guardrail is measured at zero hallucinated figures across the reports we generated,
and the places where the data simply does not exist are reported as gaps rather than filled with
plausible numbers.

The last change we made was also the most instructive. For most of this project the HMO leg was
confidently wrong by a factor of four, and nothing in the test suite could have caught it,
because the arithmetic was correct and the model of the world was not. What found it was reading
a real published contract and noticing a section we had no field for. The corresponding fix that
helps the most patients is not the document reader at all; it is the sentence that now appears
when there is no document, admitting that the figure is a ceiling.

The reading stage is where the system is weakest, and we have said where and by how much. A
system that misses half the tests on a faxed form is not finished. But it is honest about being
unfinished, which is the property we would most want to keep if we carried this further.
