"""Build the curated MMC-procedure -> PhilHealth RVS crosswalk.

The CURATED dict below is the human decision record. Each entry was chosen by reading the
MMC item name, expanding any acronym into the clinical operation it denotes, then reading
the candidate RVS descriptions in `procedure_case_rates.csv` and confirming that the
operation, the approach (open vs laparoscopic -- PhilHealth codes these separately) and the
extent all agree.

Automated matching was tried first and rejected: scoring on word morphology (-ECTOMY,
-OSTOMY, -PLASTY) has nothing to grip on for acronyms like CABG, TAHBSO, FESS, ACL or VATS,
so it fell through to generic token overlap and produced confident nonsense (it mapped
CESAREAN SECTION to a pathology-consultation code and rated a doppler-rental line "high"
confidence). Automation is kept only for shortlisting -- see propose_rvs_crosswalk.py.

Where no honest match exists the item is listed in UNMAPPED with a reason. Those rows keep
their real MMC package price and simply carry no case rate, and the app must report
PhilHealth coverage as undetermined for them rather than implying zero or guessing a code.

Ambiguity rule: where two codes are both defensible, prefer the LOWER case rate. A lower
assumed PhilHealth benefit yields a HIGHER estimated out-of-pocket, so an uncertain mapping
over-prepares the patient rather than under-quoting the bill.

Usage:
    python -m data.build_rvs_crosswalk
"""

import csv
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "mmc_price_list_raw.csv"
RATES = ROOT / "data" / "procedure_case_rates.csv"
OUT = ROOT / "data" / "mmc_rvs_crosswalk.csv"

# MMC item name -> (rvs_code, confidence, rationale)
CURATED: dict[str, tuple[str, str, str]] = {
    # --- obstetrics -------------------------------------------------------------------
    "CESAREAN SECTION PROCEDURE": ("59514", "high", "Cesarean delivery, direct match."),
    "CESAREAN SECTION MOTHER PACKAGE": ("59514", "high",
        "Mother's cesarean delivery; the baby package is billed separately and is newborn care."),
    "SPONTANEOUS VAGINAL DELIVERY": ("59409", "high", "Normal spontaneous delivery."),
    "SPONTANEOUS VAGINAL MOTHER PACKAGE": ("59409", "medium",
        "Delivery-only code (59409, P18,915) chosen over the antepartum-through-postpartum "
        "package NSD01 (P9,750): MMC bills this as a tertiary-hospital delivery, not a "
        "primary-care maternity bundle."),
    "TAHBSO PACKAGE": ("58150", "high",
        "Total abdominal hysterectomy; 58150's text explicitly covers 'w/ or w/o removal of "
        "tube(s)/ovary(s)', which is the BSO in TAHBSO."),
    "DR OB GYNE MAJOR VAGINAL HYSTERECTOMY": ("58260", "medium",
        "Vaginal hysterectomy -- the operation match is clear. Flagged by the sanity check: "
        "the case rate (P59,085) EXCEEDS MMC's price (P40,590), which would make it fully "
        "covered. The mapping is right; the price is the oddity -- this is a 'DR' "
        "(delivery-room) line billed at P40,590 flat, so it is very likely a component "
        "charge rather than a whole-operation package. Treat the resulting 'fully covered' "
        "result as understating the true bill."),
    "HYSTERECTOMY PACKAGE (ROBOT-ASSISTED)": ("58150", "medium",
        "Catalog has no laparoscopic/robotic hysterectomy code (58570-58573 absent), so the "
        "abdominal total hysterectomy is the closest honest match."),
    "DILATATION AND CURETTAGE PACKAGE": ("58120", "high", "Dilation and curettage."),
    "DIAGNOSTIC HYSTEROSCOPY PACKAGE OUTPATIENT": ("58555", "high", "Diagnostic hysteroscopy."),
    "EXPLORATORY LAPARATOMY PACKAGE": ("49000", "high", "Exploratory laparotomy/celiotomy."),
    # --- general surgery --------------------------------------------------------------
    "LAPAROSCOPIC CHOLECYSTECTOMY PACKAGE": ("47562", "high",
        "Laparoscopic cholecystectomy. Chosen over 47564 (+common-duct exploration, P90,675) "
        "and 47563 (+cholangiography) because MMC's name states neither extra."),
    "LAPAROSCOPIC CHOLECYSTECTOMY W/ ICG PACKAGE": ("47562", "high",
        "ICG is a fluorescence imaging dye used during the same operation, not extra surgery."),
    "OPEN HEPATECTOMY SURGERY PACKAGE": ("47120", "high", "Partial hepatic lobectomy."),
    "OPEN INGUINAL HERNIA W/ MESH PACKAGE": ("49505", "high",
        "Initial inguinal hernia repair, age 5+, reducible; the paediatric codes (49495-49500) "
        "are age-restricted and do not apply to a general adult package."),
    "HEMORRHOIDECTOMY PACKAGE W/ CAUTERY": ("46255", "high",
        "Internal and external hemorrhoidectomy; cautery is the technique, not extra surgery."),
    "HEMORRHOIDECTOMY PACKAGE W/ LIGASURE": ("46255", "high",
        "As above; LigaSure is a vessel-sealing device, not a different procedure."),
    "FISTULLECTOMY PACKAGE": ("46270", "medium",
        "Anal fistulectomy, subcutaneous. Deeper variants (46275+) pay the same P23,634, so "
        "the choice among them cannot change the estimate."),
    # --- breast / endocrine -----------------------------------------------------------
    "MODIFIED RADICAL MASTECTOMY SURGERY PACKAGE": ("19240", "high",
        "Modified radical mastectomy including axillary nodes."),
    "SLNB MODIFIED RADICAL MASTECTOMY PACKAGE": ("19240", "medium",
        "Sentinel lymph node biopsy is performed within the same MRM; 19240 already includes "
        "axillary node work."),
    "THYROIDECTOMY SURGERY PACKAGE": ("60240", "high",
        "Total/complete thyroidectomy. Malignancy variants with neck dissection (60252/60254) "
        "are not indicated by MMC's name."),
    # --- ENT ---------------------------------------------------------------------------
    "TONSILLECTOMY SURGERY PACKAGE": ("42825", "high",
        "Tonsillectomy alone; 42820 bundles adenoidectomy, which MMC's name does not mention."),
    "FUNCTIONAL ENDOSCOPIC SINUS SURGERY PACKAGE": ("31255", "high",
        "FESS = nasal/sinus endoscopy with total ethmoidectomy. The plain intranasal "
        "ethmoidectomy codes (31200-31205) are the non-endoscopic operation."),
    "TYMPANOPLASTY - OP LOCAL OUP PACKAGE": ("69631", "high", "Tympanoplasty without mastoidectomy."),
    "TYMPANOPLASTY - WITH SEDATION OUP PACKAGE": ("69631", "high",
        "Same operation; sedation is the anaesthetic, not a different procedure."),
    "TYMPANOPLASTY MASTOIDECTOMY PACKAGE": ("69641", "high",
        "Tympanoplasty WITH mastoidectomy; 69604 is a revision mastoidectomy, a different case."),
    # --- urology -----------------------------------------------------------------------
    "LAP PROSTATECTOMY (ROBOT-ASSISTED)": ("55866", "high",
        "Laparoscopic radical retropubic prostatectomy; robot-assisted is a laparoscopic approach."),
    "PROSTATE BIOPSY PACKAGE": ("55700", "high", "Needle/punch prostate biopsy."),
    "VARICOCELECTOMY PACKAGE": ("55530", "high",
        "Excision of varicocele. Chosen over 55535/55540 (P29,172) which specify abdominal "
        "approach / hernia repair, neither stated by MMC."),
    "CYSTOSCOPY PACKAGE": ("52000", "high",
        "Cystourethroscopy. 52005 adds ureteral catheterization, which MMC's name does not."),
    "CIRCUMCISION PACKAGE - OR": ("54152", "high",
        "Circumcision by clamp/device, other than newborn (this is the OR package, not the "
        "newborn nursery item)."),
    # --- orthopaedics / spine ----------------------------------------------------------
    "TOTAL KNEE REPLACEMENT - BILATERAL PACKAGE": ("27447", "high",
        "Total knee arthroplasty (medial AND lateral compartments). Note PhilHealth pays one "
        "case rate; the bilateral MMC price covers two knees."),
    "LOWER EXTREMITY SURGERY TOTAL KNEE REPLACE BARRIER EXTREMITY PACKAGE": ("27447", "high",
        "Total knee arthroplasty."),
    "ARTHROSCOPIC MENISECTOMY PACKAGE": ("29881", "high",
        "Arthroscopic knee meniscectomy; 27332/27333 are the open arthrotomy operation."),
    "ARTHROSCOPIC MENISECTOMY PACKAGE W/ANES": ("29881", "high",
        "Same operation; the suffix denotes anaesthesia inclusion, not extra surgery."),
    "ACL ARTHROSCOPY/MENISECTOMY PACKAGE": ("29888", "high",
        "Arthroscopically aided anterior cruciate ligament repair."),
    "ANKLE ARTHROSCOPY PACKAGE": ("29897", "medium",
        "Ankle arthroscopy with limited debridement; 29898 (extensive) pays more and is not "
        "indicated by the name, so the lower rate is the conservative choice."),
    "SHOULDER ARTHROSCOPY PACKAGE": ("29815", "low",
        "MMC's name is unqualified. 29815 (diagnostic, P35,100) is both the literal reading and "
        "the lowest of eight shoulder-arthroscopy codes (up to P59,943) -- conservative. If the "
        "package is in fact a surgical repair the true benefit is higher."),
    "MICRODISCECTOMY PACKAGE": ("63030", "high",
        "Laminotomy/hemilaminectomy with nerve-root decompression, one lumbar interspace."),
    "TRANSFORAMINAL LUMBAR INTERBODY FUSION PACKAGE": ("22630", "high",
        "Arthrodesis, posterior interbody technique, single lumbar interspace. TLIF is a "
        "posterior approach; 22554/22556 are anterior."),
    # --- cardiac / vascular ------------------------------------------------------------
    "CABG OFF/ON PUMP 3 VESSELS PACKAGE": ("33533", "medium",
        "Coronary artery bypass using arterial graft(s). The catalog codes CABG by graft type "
        "and count; arterial grafting is standard for multi-vessel CABG. Vein-only equivalents "
        "(33510/33511) pay the same P104,130, so the choice does not change the estimate."),
    "CABG OFF/ON PUMP 5 VESSELS PACKAGE": ("33536", "medium",
        "CABG, arterial graft(s), four or more coronary grafts -- matches 5 vessels."),
    "ARTERIO VENOUS FISTULA CREATION PACKAGE": ("36821", "high",
        "Direct arteriovenous anastomosis (Cimino type) -- the standard dialysis-access fistula."),
    "ARTERIO VENOUS GRAFT PACKAGE": ("36830", "high",
        "AV fistula created by nonautogenous graft, i.e. a graft rather than a direct fistula."),
    "VEIN STRIPPING PACKAGE": ("37700", "medium",
        "Ligation and division of the long saphenous vein at the saphenofemoral junction; the "
        "dedicated stripping codes (37718/37722) are absent from this catalog."),
    "BRONCHOSCOPY PACKAGE": ("31622", "high", "Diagnostic flexible/rigid bronchoscopy."),
}

# Items deliberately left without an RVS code, with the reason. These keep their real MMC
# price; the app must report PhilHealth coverage as undetermined rather than assume zero.
UNMAPPED: dict[str, str] = {
    "PRECISION CATARACT PHACOEMULSIFICATION PER EYE PACKAGE":
        "No primary cataract-extraction-with-IOL code in this catalog (66984 absent; only "
        "66830 secondary membranous cataract and 66985 IOL not associated with extraction).",
    "VIDEO ASSISTED THORACIC SURGERY (VATS) PACKAGE":
        "VATS names the approach, not the operation. Sixteen surgical-thoracoscopy codes span "
        "P23,634-P90,675 and nothing in the item name selects among them.",
    "INFERIOR VENA CAVA (IVC) FILTER INSERTION PACKAGE": "No IVC filter code in this catalog.",
    "PICC LINE INSERTION PACKAGE": "No PICC/central-catheter insertion code in this catalog.",
    "PERM CATHETER INSERTION PACKAGE OUP": "No tunnelled-catheter insertion code in this catalog.",
    "PORTA CATHETER INSERTION PACKAGE OUP": "No implanted-port insertion code in this catalog.",
    "INTRA CORPOREAL LITHOTRIPSY SPINAL PACKAGE":
        "Ambiguous: neither the target organ nor the endoscopic route is stated.",
    "RADIOFREQUENCY ABLATION (RFA) PACKAGE":
        "RFA is a modality; the case rate depends on the target lesion, which is not stated.",
    "CESAREAN SECTION BABY PACKAGE": "Newborn care, not a maternal surgical procedure.",
    "SPONTANEOUS VAGINAL BABY PACKAGE": "Newborn care, not a maternal surgical procedure.",
    "DR LAPAROSCOPY PACKAGE": "Unqualified laparoscopy -- the operation performed is not stated.",
    "DR LAPAROSCOPY (KITTING)": "Instrument kitting charge, not a distinct operation.",
    "DR AMBULATORY-GYNE BIOPSY": "Unqualified biopsy -- site not stated.",
}

# Facility / equipment / ancillary lines: not procedures at all, so no RVS code applies.
NOT_PROCEDURES = {
    "USE OF DELIVERY ROOM", "ADDITIONAL USE OF DELIVERY ROOM 3OMINS",
    "USE OF WATERPROOF DOPPLER", "CAPILLARY BLOOD GLUCOSE - DR",
    "BIRTHING ROOM W/ WATER IMMERSION",
}

PACKAGE_TYPES = {"OPERATING ROOM", "DELIVERY SURGERY"}


def main() -> None:
    rates = {r["rvs_code"]: (r["procedure"], float(r["case_rate"]))
             for r in csv.DictReader(RATES.open(encoding="utf-8"))}
    raw = [r for r in csv.DictReader(RAW.open(encoding="utf-8"))
           if r["mmc_type"] in PACKAGE_TYPES]

    out, warnings, unseen = [], [], set(CURATED) | set(UNMAPPED)
    for row in raw:
        name = row["name"]
        unseen.discard(name)
        if name in NOT_PROCEDURES:
            continue
        if name in CURATED:
            code, conf, why = CURATED[name]
            proc, rate = rates.get(code, ("(CODE NOT IN CATALOG)", 0.0))
            if proc.startswith("("):
                warnings.append(f"{name}: RVS {code} is not in the catalog")
            # Sanity check: PhilHealth paying more than the hospital charges means the code
            # is almost certainly wrong. This is a check, not a chooser.
            low = float(row["price_low"])
            if rate > low:
                warnings.append(
                    f"{name}: case rate P{rate:,.0f} exceeds MMC low price P{low:,.0f} "
                    f"(RVS {code}) -- verify")
            out.append({"mmc_code": row["mmc_code"], "mmc_name": name,
                        "mmc_type": row["mmc_type"], "price_low": row["price_low"],
                        "price_high": row["price_high"], "rvs_code": code,
                        "rvs_procedure": proc, "case_rate": f"{rate:.2f}",
                        "confidence": conf, "rationale": why})
        elif name in UNMAPPED:
            out.append({"mmc_code": row["mmc_code"], "mmc_name": name,
                        "mmc_type": row["mmc_type"], "price_low": row["price_low"],
                        "price_high": row["price_high"], "rvs_code": "",
                        "rvs_procedure": "", "case_rate": "", "confidence": "unmapped",
                        "rationale": UNMAPPED[name]})
        else:
            warnings.append(f"{name}: not classified in CURATED, UNMAPPED or NOT_PROCEDURES")

    out.sort(key=lambda r: (r["confidence"] == "unmapped", r["mmc_name"]))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    mapped = [r for r in out if r["rvs_code"]]
    print(f"crosswalk rows: {len(out)}  (mapped {len(mapped)}, unmapped {len(out) - len(mapped)})")
    for conf in ("high", "medium", "low"):
        n = sum(1 for r in mapped if r["confidence"] == conf)
        print(f"  {conf:<7} {n}")
    if unseen:
        print(f"\nnames in CURATED/UNMAPPED not found in the raw pull ({len(unseen)}):")
        for n in sorted(unseen):
            print(f"  - {n}")
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for wmsg in warnings:
            print(f"  ! {wmsg}")
    else:
        print("\nno warnings: every mapped case rate is below its MMC price")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
