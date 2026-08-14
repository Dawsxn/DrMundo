# `hmo_published_tiers.csv` — where these figures came from

**Source:** <https://www.maxicare.com.ph/maxicare-plans/mymaxicare/> — Maxicare's own site.
Read 2026-08-15. Maxicare only, by decision; other providers can be appended in the same shape.

| Plan | MBL | Room & board, as Maxicare words it |
|---|---:|---|
| Platinum Plus | ₱250,000 | Large Private |
| Platinum | ₱200,000 | Regular Private |
| Gold | ₱150,000 | Regular Private |
| Silver | ₱100,000 | Semi - Private |

## Read this before trusting a figure elsewhere

**A web search summary got all four of these wrong.** An earlier search returned Platinum Plus
₱200,000 / Platinum ₱150,000 / Gold ₱100,000 / Silver ₱60,000 — every tier shifted down one step,
which is exactly the kind of error that looks plausible and is off by ₱50,000. The figures above
were read from Maxicare's own plan page. If you update this file, read the page; do not take a
number from a search result, a blog, or a reseller site.

Only the MyMaxicare plan page carries MBL. `maxicare.com.ph/maxicare-plans/` (the landing page)
publishes prices but no benefit limits, so it cannot corroborate.

## What is deliberately NOT in here

- **No coverage percentage.** Maxicare does not publish one on that page. `HMOPlan.coverage_pct`
  defaults to 1.0 in code; that default is an assumption, not a published figure, and must not be
  presented as one.
- **No MMC room mapping for "Regular Private".** MMC's `facility_rates` has `SMALL PRIVATE`,
  `LARGE PRIVATE` and `PREMIUM LARGE PRIVATE` — there is no "regular private". `SMALL PRIVATE` is
  the plausible match and is *not* recorded, because a wrong room mapping silently changes what a
  patient is told they are entitled to. `mmc_room_type` is filled only where the two vocabularies
  agree unambiguously (Large Private, Semi - Private).
- **No corporate or SME tiers.** These are the individual/family plans. Most PH coverage is
  employer-provided and negotiated, so a corporate member's plan will very likely match nothing
  here. That is expected, not a failure — see plan §2.3.

## Accreditation: checked, and deliberately NOT recorded

An HMO pays nothing at a hospital it has not accredited, so whether Makati Medical Center
is accredited by Maxicare matters as much as any figure here. It is not in this file
because it could not be verified to the same standard.

What exists: third-party copies of Maxicare accredited-hospital lists from 2015 and 2018
that name Makati Medical Center, and the general expectation that a hospital that size is
accredited by a major HMO. What does not exist: any current, citable, first-party list.
Maxicare's own directory at `/get-care/find-doctors-clinics-and-hospitals/` is a live
search tool, and accreditation can lapse or change.

So `HMOPlan.accredited_at_mmc` stays None, and the estimate carries a caveat telling the
patient to confirm it in the directory or by phone. Asserting `true` from a decade-old
third-party PDF would be exactly the kind of plausible-looking unsourced fact this project
is built to avoid.

## How it is used

Pre-fill only. Naming a plan fills MBL and room entitlement; anything the patient states overrides
it, and `HMOPlan.mbl_source` flips from `published_tier` to `patient_stated`. Any figure still
sourced from this table renders with a visible marker telling the patient to check their own
certificate.

**Remaining balance is never in here.** It changes with every claim, lives in the member portal,
and is always typed by the patient (plan §0.1).
