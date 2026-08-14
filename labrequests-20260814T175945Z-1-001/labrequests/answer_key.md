# Answer key

Ground truth for every sample, grouped so an image can be checked by eye against its expected answer.

Master seed `20260814`. Every sample is reproducible from it: `python -m labgen.run dataset`.

**Read this before spot-checking:**

- A **struck-through row means the test was CANCELLED**, not ordered. Cancelled codes are listed separately and are deliberately absent from the checked set (DECISIONS.md 3.7).
- Every other mark style — tick, tick overflowing the box, cross, filled box, slash through the box, circle round the box, circle round the label — means **ordered**.
- Labels are shown exactly as printed. Roughly 12% are printed from the resolver's alias set rather than the canonical surface form, so the printed string and the code will not always look alike.
- No prices anywhere. This repo emits test codes; money is a separate layer (DECISIONS.md 1.1).

Contact sheet: `contact_sheet.png`

## Totals

| | Count |
|---|---:|
| Samples | 260 |
| — marked forms | 240 |
| — blank forms | 10 |
| — not a lab request | 10 |
| — stress cases | 40 |
| Checked tests, all samples | 1407 |
| Cancelled (struck-through) rows | 45 |
| Variant sub-options selected | 18 |
| Modifier options selected | 5 |

## By template

| | Count |
|---|---:|
| tpl_01_onecol_sans | 61 |
| tpl_02_twocol_serif | 76 |
| tpl_03_threecol_dense | 58 |
| tpl_04_halfsheet_compact | 55 |

## By media class

| | Count |
|---|---:|
| clean | 52 |
| fax | 52 |
| photocopy_gen1 | 52 |
| photocopy_gen3 | 52 |
| scan | 52 |

## By difficulty

| | Count |
|---|---:|
| easy | 104 |
| hard | 104 |
| medium | 52 |

---

## Samples

### 0000000

`tpl_01_onecol_sans` · `clean` · `easy` · profile `cardiac_chest_pain` · mark `tick_in_box`

`media/0000000_clean.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CPK Total | `CPK_TOTAL` |
| 2 | Chest CT | `CT_CHEST` |
| 3 | 12-lead ECG | `ECG_12L` |
| 4 | 2D Echo | `ECHO_2D` |
| 5 | LDH | `LDH` |
| 6 | Troponin-I | `TROPONIN_I` |
| 7 | Chest PA/L | `XR_CHEST_PA_L` |

**Modifiers ticked:** `CT_CHEST` → **iv_contrast**

---

### 0000001

`tpl_01_onecol_sans` · `clean` · `easy` · profile `annual_physical` · mark `tick_overflowing`

`media/0000001_clean.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |
| 2 | Fasting Blood Glucose | `FBS` |
| 3 | Stool Examination | `FECALYSIS` |
| 4 | Urinalysis | `URINALYSIS` |
| 5 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000002

`tpl_01_onecol_sans` · `clean` · `easy` · profile `annual_physical` · mark `circle_around_box`

`media/0000002_clean.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT CT | `CBC_PLT` |
| 2 | FBS | `FBS` |
| 3 | Fecalysis | `FECALYSIS` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Liver Profile | `LIVER_PROFILE` |
| 6 | Urinalysis | `URINALYSIS` |
| 7 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000003

`tpl_01_onecol_sans` · `clean` · `easy` · profile `diabetes_monitoring` · mark `tick_overflowing`

`media/0000003_clean.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Creatinine | `CREATININE` |
| 2 | FBS | `FBS` |
| 3 | HbA1c | `HBA1C` |
| 4 | Urinalysis | `URINALYSIS` |

---

### 0000004

`tpl_01_onecol_sans` · `clean` · `easy` · profile `liver_evaluation` · mark `cross`

`media/0000004_clean.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | HBsAg Qualitative | `HBSAG_SCREENING` |
| 2 | Liver Profile | `LIVER_PROFILE` |
| 3 | HBT (Liver) | `US_HBT` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000005

`tpl_01_onecol_sans` · `clean` · `easy` · profile `broad` · mark `tick_in_box`

`media/0000005_clean.png`

**12 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Urea Nitrogen | `BUN` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | FBS (Fasting Blood Sugar) | `FBS` |
| 7 | Fecalysis | `FECALYSIS` |
| 8 | FT4 | `FT4` |
| 9 | HbA1c | `HBA1C` |
| 10 | Lipid Profile | `LIPID_PROFILE` |
| 11 | TSH | `TSH` |
| 12 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000006

`tpl_01_onecol_sans` · `clean` · `easy` · profile `preoperative_clearance` · mark `cross`

`media/0000006_clean.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ Platelet Count | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000007

`tpl_01_onecol_sans` · `clean` · `easy` · profile `prenatal` · mark `cross`

`media/0000007_clean.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Typing/Rh | `BLOOD_TYPING_RH` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | OGTT | `OGTT` |
| 5 | Pregnancy Test | `PREGNANCY_TEST` |
| 6 | Urinalysis | `URINALYSIS` |
| 7 | VDRL / RPR | `VDRL_RPR` |

---

### 0000008

`tpl_01_onecol_sans` · `clean` · `easy` · profile `renal_panel` · mark `filled_scribble`

`media/0000008_clean.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Creat | `CREATININE` |
| 3 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 4 | BUA | `URIC_ACID` |
| 5 | Urinalysis | `URINALYSIS` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Calcium (Ca)~~ `CA_SERUM`

⚠ 2 mark(s) drawn faint or ambiguous.

---

### 0000009

`tpl_01_onecol_sans` · `clean` · `easy` · profile `broad` · mark `cross`

`media/0000009_clean.png`

**15 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |
| 2 | Creatinine | `CREATININE` |
| 3 | 12 Lead ECG | `ECG_12L` |
| 4 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 5 | FBS (Fasting Blood Sugar) | `FBS` |
| 6 | FT4 | `FT4` |
| 7 | HbA1c | `HBA1C` |
| 8 | HBsAg Screening | `HBSAG_SCREENING` |
| 9 | Lipid Profile | `LIPID_PROFILE` |
| 10 | Liver Profile | `LIVER_PROFILE` |
| 11 | TSH | `TSH` |
| 12 | BUA | `URIC_ACID` |
| 13 | Urinalysis | `URINALYSIS` |
| 14 | VDRL / RPR | `VDRL_RPR` |
| 15 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000010

`tpl_01_onecol_sans` · `scan` · `easy` · profile `cardiac_chest_pain` · mark `tick_overflowing`

`media/0000010_scan.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total CPK | `CPK_TOTAL` |
| 2 | Chest CT | `CT_CHEST` |
| 3 | Electrocardiogram | `ECG_12L` |
| 4 | 2D Echocardiogram | `ECHO_2D` |
| 5 | LD | `LDH` |
| 6 | Troponin-I | `TROPONIN_I` |
| 7 | Chest PA and lateral | `XR_CHEST_PA_L` |

**Modifiers ticked:** `CT_CHEST` → **triple_contrast**

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000011

`tpl_01_onecol_sans` · `scan` · `easy` · profile `thyroid_workup` · mark `tick_in_box`

`media/0000011_scan.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | TSH | `TSH` |
| 3 | Thyroid | `US_THYROID` |

---

### 0000012

`tpl_01_onecol_sans` · `scan` · `easy` · profile `broad` · mark `tick_overflowing`

`media/0000012_scan.png`

**14 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Creatinine | `CREATININE` |
| 3 | 12-lead ECG | `ECG_12L` |
| 4 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 5 | FBS (Fasting Blood Sugar) | `FBS` |
| 6 | Fecalysis | `FECALYSIS` |
| 7 | FT4 | `FT4` |
| 8 | HBsAg Screening | `HBSAG_SCREENING` |
| 9 | Liver Profile | `LIVER_PROFILE` |
| 10 | TSH | `TSH` |
| 11 | BUA | `URIC_ACID` |
| 12 | Urinalysis | `URINALYSIS` |
| 13 | VDRL/RPR | `VDRL_RPR` |
| 14 | Chest PA/L | `XR_CHEST_PA_L` |

---

### 0000013

`tpl_01_onecol_sans` · `scan` · `easy` · profile `sparse` · mark `filled_scribble`

`media/0000013_scan.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT CT | `CBC_PLT` |
| 2 | Urinalysis | `URINALYSIS` |

---

### 0000014

`tpl_01_onecol_sans` · `scan` · `easy` · profile `preoperative_clearance` · mark `filled_scribble`

`media/0000014_scan.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ Platelet Count | `CBC_PLT` |
| 3 | Electrocardiogram | `ECG_12L` |
| 4 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 5 | PTT (Partial Thromboplastin) | `PTT` |
| 6 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000015

`tpl_01_onecol_sans` · `scan` · `easy` · profile `preoperative_clearance` · mark `cross`

`media/0000015_scan.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ Platelet Count | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | PTT (Partial Thromboplastin) | `PTT` |
| 6 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | Chest PA / L | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000016

`tpl_01_onecol_sans` · `scan` · `easy` · profile `preoperative_clearance` · mark `circle_around_label`

`media/0000016_scan.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ PLT CT | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12L ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000017

`tpl_01_onecol_sans` · `scan` · `easy` · profile `diabetes_monitoring` · mark `filled_scribble`

`media/0000017_scan.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Fasting Blood Sugar | `FBS` |
| 2 | HbA1c | `HBA1C` |
| 3 | Lipid Panel | `LIPID_PROFILE` |
| 4 | Urinalysis | `URINALYSIS` |

---

### 0000018

`tpl_01_onecol_sans` · `scan` · `easy` · profile `annual_physical` · mark `cross`

`media/0000018_scan.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FBS | `FBS` |
| 2 | Fecalysis | `FECALYSIS` |
| 3 | 2-hr PPBS | `PPBS_2HR` |
| 4 | Urinalysis | `URINALYSIS` |
| 5 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000019

`tpl_01_onecol_sans` · `scan` · `easy` · profile `diabetes_monitoring` · mark `cross`

`media/0000019_scan.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FBS (Fasting Blood Sugar) | `FBS` |
| 2 | HbA1c | `HBA1C` |
| 3 | Lipid Profile | `LIPID_PROFILE` |
| 4 | Urinalysis | `URINALYSIS` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Creatinine~~ `CREATININE`

---

### 0000020

`tpl_01_onecol_sans` · `photocopy_gen1` · `medium` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000020_photocopy_gen1.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | Creat | `CREATININE` |
| 4 | Electrocardiogram | `ECG_12L` |
| 5 | Lytes | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | Chest PA/L | `XR_CHEST_PA_L` |

---

### 0000021

`tpl_01_onecol_sans` · `photocopy_gen1` · `medium` · profile `renal_panel` · mark `cross`

`media/0000021_photocopy_gen1.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Calcium (Ca) | `CA_SERUM` |
| 3 | Creatinine | `CREATININE` |
| 4 | BUA | `URIC_ACID` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Urinalysis~~ `URINALYSIS`

**Variant sub-options circled:** `CA_SERUM` → **total**

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000022

`tpl_01_onecol_sans` · `photocopy_gen1` · `medium` · profile `sparse` · mark `tick_overflowing`

`media/0000022_photocopy_gen1.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |
| 2 | Urinalysis | `URINALYSIS` |

---

### 0000023

`tpl_01_onecol_sans` · `photocopy_gen1` · `medium` · profile `broad` · mark `tick_in_box`

`media/0000023_photocopy_gen1.png`

**16 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ Platelet Count | `CBC_PLT` |
| 3 | Serum Creatinine | `CREATININE` |
| 4 | Electrocardiography | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | FBS | `FBS` |
| 7 | Fecalysis | `FECALYSIS` |
| 8 | FT4 | `FT4` |
| 9 | HbA1c | `HBA1C` |
| 10 | HBsAg Screening | `HBSAG_SCREENING` |
| 11 | Lipid Profile | `LIPID_PROFILE` |
| 12 | Liver Profile | `LIVER_PROFILE` |
| 13 | BUA | `URIC_ACID` |
| 14 | Urinalysis | `URINALYSIS` |
| 15 | VDRL / RPR | `VDRL_RPR` |
| 16 | Chest PA-L | `XR_CHEST_PA_L` |

---

### 0000024

`tpl_01_onecol_sans` · `photocopy_gen1` · `medium` · profile `sparse` · mark `tick_in_box`

`media/0000024_photocopy_gen1.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT CT | `CBC_PLT` |
| 2 | Urinalysis | `URINALYSIS` |

---

### 0000025

`tpl_01_onecol_sans` · `photocopy_gen1` · `medium` · profile `thyroid_workup` · mark `tick_overflowing`

`media/0000025_photocopy_gen1.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | TSH | `TSH` |
| 4 | Thyroid | `US_THYROID` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000026

`tpl_01_onecol_sans` · `photocopy_gen1` · `medium` · profile `annual_physical` · mark `tick_overflowing`

`media/0000026_photocopy_gen1.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Fasting Blood Sugar | `FBS` |
| 2 | Fecalysis | `FECALYSIS` |
| 3 | Lipid Profile | `LIPID_PROFILE` |
| 4 | Urinalysis | `URINALYSIS` |
| 5 | Chest PA / L | `XR_CHEST_PA_L` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~CBC with Platelet Count~~ `CBC_PLT`

---

### 0000027

`tpl_01_onecol_sans` · `photocopy_gen1` · `medium` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000027_photocopy_gen1.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | Serum Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | Chest PA-L | `XR_CHEST_PA_L` |

⚠ 2 mark(s) drawn faint or ambiguous.

---

### 0000028

`tpl_01_onecol_sans` · `photocopy_gen1` · `medium` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000028_photocopy_gen1.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ Platelet Count | `CBC_PLT` |
| 3 | 12L ECG | `ECG_12L` |
| 4 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 5 | PTT (Partial Thromboplastin) | `PTT` |
| 6 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | Chest PA and lateral | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000029

`tpl_01_onecol_sans` · `photocopy_gen1` · `medium` · profile `prenatal` · mark `tick_in_box`

`media/0000029_photocopy_gen1.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |
| 2 | HBsAg Screening | `HBSAG_SCREENING` |
| 3 | Pregnancy Test | `PREGNANCY_TEST` |
| 4 | Urinalysis | `URINALYSIS` |
| 5 | VDRL/RPR | `VDRL_RPR` |

**Variant sub-options circled:** `PREGNANCY_TEST` → **urine**

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000030

`tpl_01_onecol_sans` · `photocopy_gen3` · `hard` · profile `annual_physical` · mark `filled_scribble`

`media/0000030_photocopy_gen3.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |
| 2 | FBS (Fasting Blood Sugar) | `FBS` |
| 3 | Lipid Profile | `LIPID_PROFILE` |
| 4 | Urinalysis | `URINALYSIS` |
| 5 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000031

`tpl_01_onecol_sans` · `photocopy_gen3` · `hard` · profile `preoperative_clearance` · mark `diagonal_slash`

`media/0000031_photocopy_gen3.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC c Platelet Count | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |

---

### 0000032

`tpl_01_onecol_sans` · `photocopy_gen3` · `hard` · profile `hepatitis_screen` · mark `tick_overflowing`

`media/0000032_photocopy_gen3.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | HBsAg Screening | `HBSAG_SCREENING` |
| 2 | VDRL / RPR | `VDRL_RPR` |

---

### 0000033

`tpl_01_onecol_sans` · `photocopy_gen3` · `hard` · profile `breast_mass_workup` · mark `tick_in_box`

`media/0000033_photocopy_gen3.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC with Platelet Count | `CBC_PLT` |
| 2 | Mammogram | `MAMMOGRAM` |
| 3 | Breast | `US_BREAST` |

---

### 0000034

`tpl_01_onecol_sans` · `photocopy_gen3` · `hard` · profile `renal_panel` · mark `tick_overflowing`

`media/0000034_photocopy_gen3.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Urea Nitrogen | `BUN` |
| 2 | Calcium (Ca) | `CA_SERUM` |
| 3 | Creatinine | `CREATININE` |
| 4 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 5 | BUA | `URIC_ACID` |
| 6 | Urinalysis | `URINALYSIS` |

**Variant sub-options circled:** `CA_SERUM` → **ionized**

---

### 0000035

`tpl_01_onecol_sans` · `photocopy_gen3` · `hard` · profile `diabetes_monitoring` · mark `diagonal_slash`

`media/0000035_photocopy_gen3.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FBS (Fasting Blood Sugar) | `FBS` |
| 2 | HbA1c | `HBA1C` |
| 3 | Lipid Profile | `LIPID_PROFILE` |
| 4 | T3 | `T3` |
| 5 | Urinalysis | `URINALYSIS` |

---

### 0000036

`tpl_01_onecol_sans` · `photocopy_gen3` · `hard` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000036_photocopy_gen3.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Serum BUN | `BUN` |
| 2 | CBC w/ Platelet Count | `CBC_PLT` |
| 3 | Creat | `CREATININE` |
| 4 | 12L ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | Chest PA/L | `XR_CHEST_PA_L` |

---

### 0000037

`tpl_01_onecol_sans` · `photocopy_gen3` · `hard` · profile `annual_physical` · mark `tick_overflowing`

`media/0000037_photocopy_gen3.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |
| 2 | FBS (Fasting Blood Sugar) | `FBS` |
| 3 | Fecalysis | `FECALYSIS` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Chest PA / L~~ `XR_CHEST_PA_L`

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000038

`tpl_01_onecol_sans` · `photocopy_gen3` · `hard` · profile `preoperative_clearance` · mark `tick_overflowing`

`media/0000038_photocopy_gen3.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC + PLT | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | OGCT (50 Grams) | `OGCT_50G` |
| 7 | PTT (Partial Thromboplastin) | `PTT` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | Chest PA / L | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000039

`tpl_01_onecol_sans` · `photocopy_gen3` · `hard` · profile `sparse` · mark `tick_overflowing`

`media/0000039_photocopy_gen3.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC with Platelet Count | `CBC_PLT` |
| 2 | Urinalysis | `URINALYSIS` |

---

### 0000040

`tpl_01_onecol_sans` · `fax` · `hard` · profile `thyroid_workup` · mark `cross`

`media/0000040_fax.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | TSH | `TSH` |
| 4 | Thyroid | `US_THYROID` |

---

### 0000041

`tpl_01_onecol_sans` · `fax` · `hard` · profile `thyroid_workup` · mark `diagonal_slash`

`media/0000041_fax.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Free Triiodothyronine | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | TSH | `TSH` |
| 4 | Thyroid Ultrasound | `US_THYROID` |

---

### 0000042

`tpl_01_onecol_sans` · `fax` · `hard` · profile `prenatal` · mark `tick_in_box`

`media/0000042_fax.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Typing/Rh | `BLOOD_TYPING_RH` |
| 2 | CBC w/ PLT CT | `CBC_PLT` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | OGTT | `OGTT` |
| 5 | Pregnancy Test | `PREGNANCY_TEST` |
| 6 | BUA | `URIC_ACID` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | VDRL / RPR | `VDRL_RPR` |

**Variant sub-options circled:** `OGTT` → **g75**, `PREGNANCY_TEST` → **urine**

---

### 0000043

`tpl_01_onecol_sans` · `fax` · `hard` · profile `annual_physical` · mark `cross`

`media/0000043_fax.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT | `CBC_PLT` |
| 2 | Fecalysis | `FECALYSIS` |
| 3 | Lipid Profile | `LIPID_PROFILE` |
| 4 | Urinalysis | `URINALYSIS` |
| 5 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000044

`tpl_01_onecol_sans` · `fax` · `hard` · profile `thyroid_workup` · mark `tick_overflowing`

`media/0000044_fax.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | TSH | `TSH` |

---

### 0000045

`tpl_01_onecol_sans` · `fax` · `hard` · profile `sparse` · mark `tick_in_box`

`media/0000045_fax.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |
| 2 | Urinalysis | `URINALYSIS` |

---

### 0000046

`tpl_01_onecol_sans` · `fax` · `hard` · profile `hepatitis_screen` · mark `diagonal_slash`

`media/0000046_fax.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | HBsAg Screening | `HBSAG_SCREENING` |
| 2 | Liver Profile | `LIVER_PROFILE` |
| 3 | RPR | `VDRL_RPR` |

---

### 0000047

`tpl_01_onecol_sans` · `fax` · `hard` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000047_fax.png`

**10 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ PLT CT | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | KUB | `US_KUB` |
| 10 | Chest PA/L | `XR_CHEST_PA_L` |

---

### 0000048

`tpl_01_onecol_sans` · `fax` · `hard` · profile `prenatal` · mark `circle_around_label`

`media/0000048_fax.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Typing/Rh | `BLOOD_TYPING_RH` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | OGTT | `OGTT` |
| 5 | Pregnancy Test | `PREGNANCY_TEST` |
| 6 | Urinalysis | `URINALYSIS` |
| 7 | VDRL / RPR | `VDRL_RPR` |

**Variant sub-options circled:** `OGTT` → **g100**, `PREGNANCY_TEST` → **serum**

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000049

`tpl_01_onecol_sans` · `fax` · `hard` · profile `sparse` · mark `tick_in_box`

`media/0000049_fax.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |
| 2 | Urinalysis | `URINALYSIS` |

---

### 0000050

`tpl_02_twocol_serif` · `clean` · `easy` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000050_clean.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC/PC | `CBC_PLT` |
| 2 | Creatinine | `CREATININE` |
| 3 | Electrocardiogram | `ECG_12L` |
| 4 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 5 | PTT (Partial Thromboplastin) | `PTT` |
| 6 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 7 | Chest PA / L | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000051

`tpl_02_twocol_serif` · `clean` · `easy` · profile `liver_evaluation` · mark `circle_around_label`

`media/0000051_clean.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | ALP (Alkaline Phosphatase) | `ALP` |
| 2 | Bilirubins | `BILI_PANEL` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | Liver Profile | `LIVER_PROFILE` |
| 5 | HBT | `US_HBT` |

---

### 0000052

`tpl_02_twocol_serif` · `clean` · `easy` · profile `hepatitis_screen` · mark `tick_overflowing`

`media/0000052_clean.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | HBsAg Screening | `HBSAG_SCREENING` |
| 2 | Liver Profile | `LIVER_PROFILE` |
| 3 | VDRL/RPR | `VDRL_RPR` |

---

### 0000053

`tpl_02_twocol_serif` · `clean` · `easy` · profile `diabetes_monitoring` · mark `cross`

`media/0000053_clean.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | FBS (Fasting Blood Sugar) | `FBS` |
| 3 | Lipid Profile | `LIPID_PROFILE` |
| 4 | Urinalysis | `URINALYSIS` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~HbA1c~~ `HBA1C`

---

### 0000054

`tpl_02_twocol_serif` · `clean` · `easy` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000054_clean.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ PLT CT | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | Electrocardiogram | `ECG_12L` |
| 5 | PTT (Partial Thromboplastin) | `PTT` |
| 6 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | Chest PA/L | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000055

`tpl_02_twocol_serif` · `clean` · `easy` · profile `thyroid_workup` · mark `tick_in_box`

`media/0000055_clean.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |

**2 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~TSH~~ `TSH`
- ~~Thyroid~~ `US_THYROID`

---

### 0000056

`tpl_02_twocol_serif` · `clean` · `easy` · profile `prenatal` · mark `tick_overflowing`

`media/0000056_clean.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Typing/Rh | `BLOOD_TYPING_RH` |
| 2 | HBsAg Screening | `HBSAG_SCREENING` |
| 3 | OGTT (75 Grams) | `OGTT_75G` |
| 4 | Pregnancy Test | `PREGNANCY_TEST` |
| 5 | Urinalysis | `URINALYSIS` |
| 6 | VDRL | `VDRL_RPR` |

**Variant sub-options circled:** `PREGNANCY_TEST` → **urine**

---

### 0000057

`tpl_02_twocol_serif` · `clean` · `easy` · profile `diabetes_monitoring` · mark `tick_overflowing`

`media/0000057_clean.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Fasting Blood Sugar | `FBS` |
| 2 | HbA1c | `HBA1C` |
| 3 | Lipid Profile | `LIPID_PROFILE` |
| 4 | Urinalysis | `URINALYSIS` |

---

### 0000058

`tpl_02_twocol_serif` · `clean` · `easy` · profile `renal_panel` · mark `circle_around_box`

`media/0000058_clean.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Calcium (Ca) | `CA_SERUM` |
| 3 | Creatinine | `CREATININE` |
| 4 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 5 | BUA | `URIC_ACID` |
| 6 | Urinalysis (UA) | `URINALYSIS` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000059

`tpl_02_twocol_serif` · `clean` · `easy` · profile `annual_physical` · mark `tick_in_box`

`media/0000059_clean.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |
| 2 | FBS | `FBS` |
| 3 | Urinalysis | `URINALYSIS` |
| 4 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000060

`tpl_02_twocol_serif` · `scan` · `easy` · profile `hepatitis_screen` · mark `tick_overflowing`

`media/0000060_scan.png`

**1 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | HBsAg Screening | `HBSAG_SCREENING` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Liver Profile~~ `LIVER_PROFILE`

---

### 0000061

`tpl_02_twocol_serif` · `scan` · `easy` · profile `cardiac_chest_pain` · mark `tick_in_box`

`media/0000061_scan.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total CPK | `CPK_TOTAL` |
| 2 | 12-lead ECG | `ECG_12L` |
| 3 | 2DED | `ECHO_2D` |
| 4 | LDH | `LDH` |
| 5 | Chest PA/L | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000062

`tpl_02_twocol_serif` · `scan` · `easy` · profile `liver_evaluation` · mark `cross`

`media/0000062_scan.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Alkaline Phosphatase | `ALP` |
| 2 | Bilirubin (TB, DB, IB) | `BILI_PANEL` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | Liver Profile | `LIVER_PROFILE` |
| 5 | HBT | `US_HBT` |

---

### 0000063

`tpl_02_twocol_serif` · `scan` · `easy` · profile `cardiac_chest_pain` · mark `tick_overflowing`

`media/0000063_scan.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total CPK | `CPK_TOTAL` |
| 2 | Chest CT | `CT_CHEST` |
| 3 | 12L ECG | `ECG_12L` |
| 4 | 2D Echo | `ECHO_2D` |
| 5 | LD | `LDH` |
| 6 | Troponin-I | `TROPONIN_I` |
| 7 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000064

`tpl_02_twocol_serif` · `scan` · `easy` · profile `preoperative_clearance` · mark `filled_scribble`

`media/0000064_scan.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC + PLT | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | Electrocardiogram | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 8 | Routine Urinalysis | `URINALYSIS` |
| 9 | Chest PA and lateral | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000065

`tpl_02_twocol_serif` · `scan` · `easy` · profile `cardiac_chest_pain` · mark `circle_around_label`

`media/0000065_scan.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total CPK | `CPK_TOTAL` |
| 2 | Chest CT | `CT_CHEST` |
| 3 | 12-lead ECG | `ECG_12L` |
| 4 | 2D Echo | `ECHO_2D` |
| 5 | LD | `LDH` |
| 6 | Troponin-I | `TROPONIN_I` |
| 7 | Chest PA-L | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000066

`tpl_02_twocol_serif` · `scan` · `easy` · profile `thyroid_workup` · mark `tick_in_box`

`media/0000066_scan.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | Thyroid Stimulating Hormone | `TSH` |
| 4 | Thyroid | `US_THYROID` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000067

`tpl_02_twocol_serif` · `scan` · `easy` · profile `cardiac_chest_pain` · mark `tick_in_box`

`media/0000067_scan.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Chest CT | `CT_CHEST` |
| 2 | 12L ECG | `ECG_12L` |
| 3 | 2D Echocardiogram | `ECHO_2D` |
| 4 | Lactate Dehydrogenase | `LDH` |

---

### 0000068

`tpl_02_twocol_serif` · `scan` · `easy` · profile `preoperative_clearance` · mark `filled_scribble`

`media/0000068_scan.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ PLT CT | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | Chest PA-L | `XR_CHEST_PA_L` |

---

### 0000069

`tpl_02_twocol_serif` · `scan` · `easy` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000069_scan.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | 12-lead ECG | `ECG_12L` |
| 4 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 5 | PTT (Partial Thromboplastin) | `PTT` |
| 6 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 7 | Chest PA / L | `XR_CHEST_PA_L` |

⚠ 2 mark(s) drawn faint or ambiguous.

---

### 0000070

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `liver_evaluation` · mark `circle_around_label`

`media/0000070_photocopy_gen1.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | ALP (Alkaline Phosphatase) | `ALP` |
| 2 | Bilirubin (TBil, B1, B2) | `BILI_PANEL` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | Liver Profile | `LIVER_PROFILE` |
| 5 | HBT (Liver) | `US_HBT` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000071

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `broad` · mark `tick_overflowing`

`media/0000071_photocopy_gen1.png`

**18 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Alkaline Phosphatase | `ALP` |
| 2 | BUN | `BUN` |
| 3 | CBC w/ PLT CT | `CBC_PLT` |
| 4 | Creatinine | `CREATININE` |
| 5 | 12L ECG | `ECG_12L` |
| 6 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 7 | FBS | `FBS` |
| 8 | Fecalysis | `FECALYSIS` |
| 9 | FT4 | `FT4` |
| 10 | HbA1c | `HBA1C` |
| 11 | HBsAg Screen | `HBSAG_SCREENING` |
| 12 | Lipid Profile | `LIPID_PROFILE` |
| 13 | Liver Profile | `LIVER_PROFILE` |
| 14 | Thyrotropin | `TSH` |
| 15 | BUA | `URIC_ACID` |
| 16 | Urinalysis | `URINALYSIS` |
| 17 | VDRL/RPR | `VDRL_RPR` |
| 18 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000072

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `thyroid_workup` · mark `tick_in_box`

`media/0000072_photocopy_gen1.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 4 | TSH | `TSH` |
| 5 | Thyroid | `US_THYROID` |

---

### 0000073

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `renal_panel` · mark `tick_in_box`

`media/0000073_photocopy_gen1.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Calcium (Ca) | `CA_SERUM` |
| 3 | Creatinine | `CREATININE` |
| 4 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 5 | BUA | `URIC_ACID` |
| 6 | Urinalysis | `URINALYSIS` |

**Variant sub-options circled:** `CA_SERUM` → **total**

---

### 0000074

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `preoperative_clearance` · mark `tick_overflowing`

`media/0000074_photocopy_gen1.png`

**10 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | Creat | `CREATININE` |
| 4 | 12L ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | Prothrombin Time | `PT_PROTHROMBIN` |
| 8 | T4 | `T4` |
| 9 | Urinalysis | `URINALYSIS` |
| 10 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000075

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000075_photocopy_gen1.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ PLT | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12L ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000076

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `renal_panel` · mark `tick_in_box`

`media/0000076_photocopy_gen1.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Calcium (Ca) | `CA_SERUM` |
| 3 | Creatinine | `CREATININE` |
| 4 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 5 | BUA | `URIC_ACID` |
| 6 | Urinalysis | `URINALYSIS` |

**Variant sub-options circled:** `CA_SERUM` → **total**

⚠ 2 mark(s) drawn faint or ambiguous.

---

### 0000077

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `diabetes_monitoring` · mark `diagonal_slash`

`media/0000077_photocopy_gen1.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FBS | `FBS` |
| 2 | HbA1c | `HBA1C` |
| 3 | Urinalysis (Routine) | `URINALYSIS` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Creat~~ `CREATININE`

---

### 0000078

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `prenatal` · mark `diagonal_slash`

`media/0000078_photocopy_gen1.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Typing/Rh | `BLOOD_TYPING_RH` |
| 2 | HBsAg Screening | `HBSAG_SCREENING` |
| 3 | OGTT (75 Grams) | `OGTT_75G` |
| 4 | Pregnancy Test | `PREGNANCY_TEST` |
| 5 | Urinalysis | `URINALYSIS` |
| 6 | VDRL / RPR | `VDRL_RPR` |

---

### 0000079

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `preoperative_clearance` · mark `cross`

`media/0000079_photocopy_gen1.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Urea Nitrogen | `BUN` |
| 2 | CBC w/ PLT | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000080

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `preoperative_clearance` · mark `cross`

`media/0000080_photocopy_gen3.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Urea Nitrogen | `BUN` |
| 2 | CBC w/ Platelet Count | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | Electrocardiogram | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | Protime | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | VDRL | `VDRL_RPR` |

---

### 0000081

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `diabetes_monitoring` · mark `cross`

`media/0000081_photocopy_gen3.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Creatinine | `CREATININE` |
| 2 | FBS (Fasting Blood Sugar) | `FBS` |
| 3 | HbA1c | `HBA1C` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |

---

### 0000082

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `diabetes_monitoring` · mark `tick_overflowing`

`media/0000082_photocopy_gen3.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Creatinine | `CREATININE` |
| 2 | FBS (Fasting Blood Sugar) | `FBS` |
| 3 | HbA1c | `HBA1C` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |

---

### 0000083

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `liver_evaluation` · mark `diagonal_slash`

`media/0000083_photocopy_gen3.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | ALP (Alkaline Phosphatase) | `ALP` |
| 2 | Bilirubin (TB, DB, IB) | `BILI_PANEL` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | Hepatic Profile | `LIVER_PROFILE` |
| 5 | HBT | `US_HBT` |

---

### 0000084

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `prenatal` · mark `tick_overflowing`

`media/0000084_photocopy_gen3.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Typing | `BLOOD_TYPING_RH` |
| 2 | CBC w/ Platelet Count | `CBC_PLT` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | Pregnancy Test | `PREGNANCY_TEST` |
| 5 | Urinalysis (Routine) | `URINALYSIS` |
| 6 | RPR | `VDRL_RPR` |

**Variant sub-options circled:** `PREGNANCY_TEST` → **urine**

---

### 0000085

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `sparse` · mark `tick_overflowing`

`media/0000085_photocopy_gen3.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT CT | `CBC_PLT` |
| 2 | Urinalysis | `URINALYSIS` |

---

### 0000086

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000086_photocopy_gen3.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Urea Nitrogen | `BUN` |
| 2 | Complete Blood Count with Platelet | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | Pro-time | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | Chest PA/L | `XR_CHEST_PA_L` |

---

### 0000087

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `breast_mass_workup` · mark `tick_overflowing`

`media/0000087_photocopy_gen3.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Complete Blood Count with Platelet | `CBC_PLT` |
| 2 | Mammography (Bilateral) | `MAMMOGRAM` |
| 3 | Breast | `US_BREAST` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000088

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `sparse` · mark `cross`

`media/0000088_photocopy_gen3.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |
| 2 | Urinalysis | `URINALYSIS` |

---

### 0000089

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `renal_panel` · mark `cross`

`media/0000089_photocopy_gen3.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Calcium (Ca) | `CA_SERUM` |
| 2 | Creatinine | `CREATININE` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~BUN~~ `BUN`

**Variant sub-options circled:** `CA_SERUM` → **ionized**

---

### 0000090

`tpl_02_twocol_serif` · `fax` · `hard` · profile `cardiac_chest_pain` · mark `tick_overflowing`

`media/0000090_fax.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total CPK | `CPK_TOTAL` |
| 2 | Chest CT | `CT_CHEST` |
| 3 | 12L ECG | `ECG_12L` |
| 4 | 2D Echo | `ECHO_2D` |
| 5 | LDH | `LDH` |
| 6 | Troponin-I | `TROPONIN_I` |

**Modifiers ticked:** `CT_CHEST` → **triple_contrast**

---

### 0000091

`tpl_02_twocol_serif` · `fax` · `hard` · profile `broad` · mark `tick_overflowing`

`media/0000091_fax.png`

**17 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Alk Phos | `ALP` |
| 2 | Bilirubins | `BILI_PANEL` |
| 3 | BUN | `BUN` |
| 4 | CBC w/ Platelet Count | `CBC_PLT` |
| 5 | Creatinine | `CREATININE` |
| 6 | 12L ECG | `ECG_12L` |
| 7 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 8 | Fasting Blood Glucose | `FBS` |
| 9 | FT4 | `FT4` |
| 10 | HBsAg Screening | `HBSAG_SCREENING` |
| 11 | Lipid Profile | `LIPID_PROFILE` |
| 12 | Liver Profile | `LIVER_PROFILE` |
| 13 | TSH | `TSH` |
| 14 | BUA | `URIC_ACID` |
| 15 | Urinalysis (UA) | `URINALYSIS` |
| 16 | VDRL/RPR | `VDRL_RPR` |
| 17 | Chest PA/L | `XR_CHEST_PA_L` |

---

### 0000092

`tpl_02_twocol_serif` · `fax` · `hard` · profile `liver_evaluation` · mark `tick_overflowing`

`media/0000092_fax.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Liver Profile | `LIVER_PROFILE` |
| 2 | HBT (Liver) | `US_HBT` |

---

### 0000093

`tpl_02_twocol_serif` · `fax` · `hard` · profile `renal_panel` · mark `tick_in_box`

`media/0000093_fax.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Urea Nitrogen | `BUN` |
| 2 | Calcium (Ca) | `CA_SERUM` |
| 3 | Creatinine | `CREATININE` |
| 4 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 5 | BUA | `URIC_ACID` |
| 6 | Urinalysis | `URINALYSIS` |

**Variant sub-options circled:** `CA_SERUM` → **total**

---

### 0000094

`tpl_02_twocol_serif` · `fax` · `hard` · profile `preoperative_clearance` · mark `cross`

`media/0000094_fax.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | Creat | `CREATININE` |
| 4 | Electrocardiogram | `ECG_12L` |
| 5 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | CXR PA/L | `XR_CHEST_PA_L` |

---

### 0000095

`tpl_02_twocol_serif` · `fax` · `hard` · profile `sparse` · mark `diagonal_slash`

`media/0000095_fax.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT CT | `CBC_PLT` |
| 2 | Urinalysis | `URINALYSIS` |

---

### 0000096

`tpl_02_twocol_serif` · `fax` · `hard` · profile `sparse`

`media/0000096_fax.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000097

`tpl_02_twocol_serif` · `fax` · `hard` · profile `preoperative_clearance` · mark `cross`

`media/0000097_fax.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | Serum Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | PTT (Partial Thromboplastin) | `PTT` |
| 6 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | Chest PA/L | `XR_CHEST_PA_L` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Serum Electrolytes (Na, K, Cl)~~ `ELECTROLYTES`

---

### 0000098

`tpl_02_twocol_serif` · `fax` · `hard` · profile `renal_panel` · mark `cross`

`media/0000098_fax.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Calcium (Ca) | `CA_SERUM` |
| 3 | Creat | `CREATININE` |
| 4 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 5 | BUA | `URIC_ACID` |
| 6 | Urinalysis | `URINALYSIS` |

**Variant sub-options circled:** `CA_SERUM` → **total**

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000099

`tpl_02_twocol_serif` · `fax` · `hard` · profile `annual_physical` · mark `circle_around_label`

`media/0000099_fax.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT CT | `CBC_PLT` |
| 2 | FBS | `FBS` |
| 3 | Fecalysis | `FECALYSIS` |
| 4 | Lipid Profile (TC/TG/HDL/LDL/VLDL) | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |
| 6 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000100

`tpl_03_threecol_dense` · `clean` · `easy` · profile `renal_panel` · mark `tick_overflowing`

`media/0000100_clean.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Ionized Calcium | `CA_IONIZED` |
| 3 | Total Calcium | `CA_TOTAL` |
| 4 | Creatinine | `CREATININE` |
| 5 | Potassium (K) | `K` |
| 6 | Sodium (Na) | `NA` |
| 7 | BUA | `URIC_ACID` |
| 8 | VLDL | `VLDL` |

---

### 0000101

`tpl_03_threecol_dense` · `clean` · `easy` · profile `preoperative_clearance` · mark `tick_overflowing`

`media/0000101_clean.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC | `CBC` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Potassium (K) | `K` |
| 6 | aPTT | `PTT` |
| 7 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000102

`tpl_03_threecol_dense` · `clean` · `easy` · profile `sparse` · mark `tick_in_box`

`media/0000102_clean.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Complete Blood Count (CBC) | `CBC` |
| 2 | Urinalysis | `URINALYSIS` |

---

### 0000103

`tpl_03_threecol_dense` · `clean` · `easy` · profile `preoperative_clearance` · mark `tick_overflowing`

`media/0000103_clean.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC | `CBC` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Potassium (K) | `K` |
| 6 | Sodium (Na) | `NA` |
| 7 | PTT (Partial Thromboplastin) | `PTT` |
| 8 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |

---

### 0000104

`tpl_03_threecol_dense` · `clean` · `easy` · profile `renal_panel` · mark `tick_in_box`

`media/0000104_clean.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Ionized Calcium | `CA_IONIZED` |
| 3 | Total Calcium | `CA_TOTAL` |
| 4 | Creatinine | `CREATININE` |
| 5 | Potassium (K) | `K` |
| 6 | Sodium (Na) | `NA` |
| 7 | Uric Acid | `URIC_ACID` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Urinalysis~~ `URINALYSIS`

---

### 0000105

`tpl_03_threecol_dense` · `clean` · `easy` · profile `thyroid_workup` · mark `tick_overflowing`

`media/0000105_clean.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | TSH | `TSH` |
| 4 | Thyroid | `US_THYROID` |

---

### 0000106

`tpl_03_threecol_dense` · `clean` · `easy` · profile `broad` · mark `tick_overflowing`

`media/0000106_clean.png`

**22 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | ALP (Alkaline Phosphatase) | `ALP` |
| 2 | Bilirubins | `BILI_PANEL` |
| 3 | BUN | `BUN` |
| 4 | CBC | `CBC` |
| 5 | Total Cholesterol | `CHOL_TOTAL` |
| 6 | Creatinine | `CREATININE` |
| 7 | Electrocardiography | `ECG_12L` |
| 8 | Free T4 | `FT4` |
| 9 | Glycosylated Hemoglobin | `HBA1C` |
| 10 | HBsAg Screening | `HBSAG_SCREENING` |
| 11 | HDL | `HDL` |
| 12 | Potassium (K) | `K` |
| 13 | LDL | `LDL` |
| 14 | Sodium (Na) | `NA` |
| 15 | SGOT/AST | `SGOT_AST` |
| 16 | SGPT/ALT | `SGPT_ALT` |
| 17 | Triglycerides | `TRIGLYCERIDES` |
| 18 | TSH | `TSH` |
| 19 | Uric Acid | `URIC_ACID` |
| 20 | Urinalysis | `URINALYSIS` |
| 21 | VDRL/RPR | `VDRL_RPR` |
| 22 | Chest X-ray PA and Lateral | `XR_CHEST_PA_L` |

⚠ 3 mark(s) drawn faint or ambiguous.

---

### 0000107

`tpl_03_threecol_dense` · `clean` · `easy` · profile `renal_panel` · mark `filled_scribble`

`media/0000107_clean.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | iCa | `CA_IONIZED` |
| 2 | Total Calcium | `CA_TOTAL` |
| 3 | Creatinine | `CREATININE` |
| 4 | Serum Potassium | `K` |
| 5 | Uric Acid | `URIC_ACID` |
| 6 | Urinalysis | `URINALYSIS` |

---

### 0000108

`tpl_03_threecol_dense` · `clean` · `easy` · profile `broad` · mark `circle_around_label`

`media/0000108_clean.png`

**24 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | ALP | `ALP` |
| 2 | Bilirubins | `BILI_PANEL` |
| 3 | BUN | `BUN` |
| 4 | CBC | `CBC` |
| 5 | Cholesterol | `CHOL_TOTAL` |
| 6 | Creatinine | `CREATININE` |
| 7 | 12L ECG | `ECG_12L` |
| 8 | FBS (Fasting Blood Sugar) | `FBS` |
| 9 | Fecalysis | `FECALYSIS` |
| 10 | FT-4 | `FT4` |
| 11 | HbA1c | `HBA1C` |
| 12 | HBsAg Screening | `HBSAG_SCREENING` |
| 13 | HDL | `HDL` |
| 14 | Potassium (K) | `K` |
| 15 | LDL | `LDL` |
| 16 | Sodium | `NA` |
| 17 | SGOT / AST | `SGOT_AST` |
| 18 | SGPT / ALT | `SGPT_ALT` |
| 19 | Triglycerides | `TRIGLYCERIDES` |
| 20 | TSH | `TSH` |
| 21 | Serum Uric Acid | `URIC_ACID` |
| 22 | Urinalysis | `URINALYSIS` |
| 23 | VDRL/RPR | `VDRL_RPR` |
| 24 | Chest PA / L | `XR_CHEST_PA_L` |

⚠ 2 mark(s) drawn faint or ambiguous.

---

### 0000109

`tpl_03_threecol_dense` · `clean` · `easy` · profile `renal_panel` · mark `tick_overflowing`

`media/0000109_clean.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Ionized Calcium | `CA_IONIZED` |
| 3 | Total Calcium | `CA_TOTAL` |
| 4 | Creatinine | `CREATININE` |
| 5 | Potassium (K) | `K` |
| 6 | Sodium (Na) | `NA` |
| 7 | Blood Uric Acid | `URIC_ACID` |
| 8 | Urinalysis | `URINALYSIS` |

---

### 0000110

`tpl_03_threecol_dense` · `scan` · `easy` · profile `cardiac_chest_pain` · mark `tick_in_box`

`media/0000110_scan.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total CPK | `CPK_TOTAL` |
| 2 | 12L ECG | `ECG_12L` |
| 3 | 2D Echo | `ECHO_2D` |
| 4 | Troponin-I | `TROPONIN_I` |
| 5 | Chest PA/L | `XR_CHEST_PA_L` |

---

### 0000111

`tpl_03_threecol_dense` · `scan` · `easy` · profile `diabetes_monitoring` · mark `circle_around_box`

`media/0000111_scan.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total Cholesterol | `CHOL_TOTAL` |
| 2 | Creatinine | `CREATININE` |
| 3 | FBS (Fasting Blood Sugar) | `FBS` |
| 4 | HbA1c | `HBA1C` |
| 5 | HDL | `HDL` |
| 6 | Triglycerides | `TRIGLYCERIDES` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | VLDL Cholesterol | `VLDL` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000112

`tpl_03_threecol_dense` · `scan` · `easy` · profile `diabetes_monitoring` · mark `circle_around_box`

`media/0000112_scan.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total Cholesterol | `CHOL_TOTAL` |
| 2 | Creatinine | `CREATININE` |
| 3 | FBS | `FBS` |
| 4 | HbA1c | `HBA1C` |
| 5 | HDL | `HDL` |
| 6 | LDL Cholesterol | `LDL` |
| 7 | Triglycerides | `TRIGLYCERIDES` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | VLDL | `VLDL` |

---

### 0000113

`tpl_03_threecol_dense` · `scan` · `easy` · profile `preoperative_clearance` · mark `diagonal_slash`

`media/0000113_scan.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Complete Blood Count | `CBC` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Potassium (K) | `K` |
| 6 | Sodium (Na) | `NA` |
| 7 | PTT (Partial Thromboplastin) | `PTT` |
| 8 | Urinalysis | `URINALYSIS` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~PT (Prothrombin)~~ `PT_PROTHROMBIN`

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000114

`tpl_03_threecol_dense` · `scan` · `easy` · profile `annual_physical` · mark `tick_overflowing`

`media/0000114_scan.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC | `CBC` |
| 2 | Total Cholesterol | `CHOL_TOTAL` |
| 3 | FBS (Fasting Blood Sugar) | `FBS` |
| 4 | Fecalysis | `FECALYSIS` |
| 5 | HDL | `HDL` |
| 6 | LDL | `LDL` |
| 7 | Triglycerides | `TRIGLYCERIDES` |
| 8 | VLDL | `VLDL` |
| 9 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000115

`tpl_03_threecol_dense` · `scan` · `easy` · profile `prenatal` · mark `circle_around_label`

`media/0000115_scan.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Typing/Rh | `BLOOD_TYPING_RH` |
| 2 | CBC | `CBC` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | OGTT (75 Grams) | `OGTT_75G` |
| 5 | Urinalysis | `URINALYSIS` |
| 6 | VDRL/RPR | `VDRL_RPR` |

---

### 0000116

`tpl_03_threecol_dense` · `scan` · `easy` · profile `breast_mass_workup` · mark `diagonal_slash`

`media/0000116_scan.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC | `CBC` |
| 2 | Mammography (Bilateral) | `MAMMOGRAM` |
| 3 | Breast | `US_BREAST` |

---

### 0000117

`tpl_03_threecol_dense` · `scan` · `easy` · profile `diabetes_monitoring` · mark `tick_in_box`

`media/0000117_scan.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total Cholesterol | `CHOL_TOTAL` |
| 2 | Creatinine | `CREATININE` |
| 3 | FBS (Fasting Blood Sugar) | `FBS` |
| 4 | HbA1c | `HBA1C` |
| 5 | HDL | `HDL` |
| 6 | LDL | `LDL` |
| 7 | Triglycerides | `TRIGLYCERIDES` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | VLDL | `VLDL` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000118

`tpl_03_threecol_dense` · `scan` · `easy` · profile `annual_physical` · mark `diagonal_slash`

`media/0000118_scan.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total Cholesterol | `CHOL_TOTAL` |
| 2 | HDL | `HDL` |
| 3 | Low Density Lipoprotein | `LDL` |
| 4 | Triglycerides | `TRIGLYCERIDES` |
| 5 | Urinalysis | `URINALYSIS` |
| 6 | VLDL | `VLDL` |
| 7 | Chest PA / L | `XR_CHEST_PA_L` |

**2 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~FBS (Fasting Blood Sugar)~~ `FBS`
- ~~Fecalysis~~ `FECALYSIS`

---

### 0000119

`tpl_03_threecol_dense` · `scan` · `easy` · profile `liver_evaluation` · mark `tick_in_box`

`media/0000119_scan.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | ALP (Alkaline Phosphatase) | `ALP` |
| 2 | Bilirubin (TB, DB, IB) | `BILI_PANEL` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | SGOT / AST | `SGOT_AST` |
| 5 | SGPT / ALT | `SGPT_ALT` |
| 6 | HBT (Liver) | `US_HBT` |

---

### 0000120

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `liver_evaluation` · mark `tick_in_box`

`media/0000120_photocopy_gen1.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Bilirubin (TB, DB, IB) | `BILI_PANEL` |
| 2 | HBsAg Screening | `HBSAG_SCREENING` |
| 3 | SGOT / AST | `SGOT_AST` |
| 4 | SGPT / ALT | `SGPT_ALT` |
| 5 | HBT (Liver) | `US_HBT` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000121

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `prenatal` · mark `tick_in_box`

`media/0000121_photocopy_gen1.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Typing/Rh | `BLOOD_TYPING_RH` |
| 2 | CBC | `CBC` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | OGTT (75 Grams) | `OGTT_75G` |
| 5 | Urinalysis | `URINALYSIS` |

---

### 0000122

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `annual_physical` · mark `tick_in_box`

`media/0000122_photocopy_gen1.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Complete Blood Count | `CBC` |
| 2 | Total Cholesterol | `CHOL_TOTAL` |
| 3 | FBS | `FBS` |
| 4 | Fecalysis (Routine) | `FECALYSIS` |
| 5 | High Density Lipoprotein | `HDL` |
| 6 | Triglycerides | `TRIGLYCERIDES` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | Very Low Density Lipoprotein | `VLDL` |
| 9 | Chest PA and lateral | `XR_CHEST_PA_L` |

⚠ 2 mark(s) drawn faint or ambiguous.

---

### 0000123

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `diabetes_monitoring` · mark `tick_in_box`

`media/0000123_photocopy_gen1.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | T. Chole | `CHOL_TOTAL` |
| 2 | Creatinine | `CREATININE` |
| 3 | FBS (Fasting Blood Sugar) | `FBS` |
| 4 | HbA1c | `HBA1C` |
| 5 | High Density Lipoprotein | `HDL` |
| 6 | LDL | `LDL` |
| 7 | Triglycerides | `TRIGLYCERIDES` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | VLDL | `VLDL` |

---

### 0000124

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `prenatal` · mark `tick_overflowing`

`media/0000124_photocopy_gen1.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Typing/Rh | `BLOOD_TYPING_RH` |
| 2 | CBC | `CBC` |
| 3 | OGTT 75g | `OGTT_75G` |
| 4 | Urinalysis | `URINALYSIS` |
| 5 | VDRL/RPR | `VDRL_RPR` |

---

### 0000125

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `cardiac_chest_pain` · mark `tick_in_box`

`media/0000125_photocopy_gen1.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total CPK | `CPK_TOTAL` |
| 2 | Chest CT | `CT_CHEST` |
| 3 | 12L ECG | `ECG_12L` |
| 4 | 2D Echo | `ECHO_2D` |
| 5 | LDH | `LDH` |
| 6 | Troponin-I | `TROPONIN_I` |
| 7 | Chest PA/L | `XR_CHEST_PA_L` |

**Modifiers ticked:** `CT_CHEST` → **triple_contrast**

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000126

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `thyroid_workup` · mark `diagonal_slash`

`media/0000126_photocopy_gen1.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | TSH | `TSH` |
| 3 | Thyroid | `US_THYROID` |

---

### 0000127

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `diabetes_monitoring` · mark `tick_in_box`

`media/0000127_photocopy_gen1.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total Cholesterol | `CHOL_TOTAL` |
| 2 | Creatinine | `CREATININE` |
| 3 | FBS | `FBS` |
| 4 | HbA1c | `HBA1C` |
| 5 | HDL | `HDL` |
| 6 | LDL | `LDL` |
| 7 | Triglycerides | `TRIGLYCERIDES` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | VLDL | `VLDL` |

---

### 0000128

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `preoperative_clearance` · mark `circle_around_box`

`media/0000128_photocopy_gen1.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC | `CBC` |
| 3 | Sodium (Na) | `NA` |
| 4 | PTT (Partial Thromboplastin) | `PTT` |
| 5 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 6 | Routine Urinalysis | `URINALYSIS` |
| 7 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000129

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `broad` · mark `tick_overflowing`

`media/0000129_photocopy_gen1.png`

**23 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | ALP | `ALP` |
| 2 | Bilirubins | `BILI_PANEL` |
| 3 | BUN | `BUN` |
| 4 | CBC | `CBC` |
| 5 | Total Cholesterol | `CHOL_TOTAL` |
| 6 | Creatinine | `CREATININE` |
| 7 | FBS | `FBS` |
| 8 | Fecal Analysis | `FECALYSIS` |
| 9 | FT4 | `FT4` |
| 10 | HbA1c | `HBA1C` |
| 11 | HBsAg Screening | `HBSAG_SCREENING` |
| 12 | HDL | `HDL` |
| 13 | Serum Potassium | `K` |
| 14 | LDL | `LDL` |
| 15 | Sodium (Na) | `NA` |
| 16 | SGOT/AST | `SGOT_AST` |
| 17 | SGPT / ALT | `SGPT_ALT` |
| 18 | Triglycerides | `TRIGLYCERIDES` |
| 19 | Uric Acid | `URIC_ACID` |
| 20 | Urinalysis | `URINALYSIS` |
| 21 | VDRL/RPR | `VDRL_RPR` |
| 22 | VLDL | `VLDL` |
| 23 | Chest PA/L | `XR_CHEST_PA_L` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~12 Lead ECG~~ `ECG_12L`

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000130

`tpl_03_threecol_dense` · `photocopy_gen3` · `hard` · profile `cardiac_chest_pain` · mark `tick_in_box`

`media/0000130_photocopy_gen3.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total CPK | `CPK_TOTAL` |
| 2 | Chest CT | `CT_CHEST` |
| 3 | Electrocardiogram | `ECG_12L` |
| 4 | 2D Echo | `ECHO_2D` |
| 5 | Troponin-I | `TROPONIN_I` |
| 6 | Thyroid | `US_THYROID` |
| 7 | Chest PA/L | `XR_CHEST_PA_L` |

**Modifiers ticked:** `CT_CHEST` → **triple_contrast**

⚠ 2 mark(s) drawn faint or ambiguous.

---

### 0000131

`tpl_03_threecol_dense` · `photocopy_gen3` · `hard` · profile `diabetes_monitoring` · mark `tick_overflowing`

`media/0000131_photocopy_gen3.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Creatinine | `CREATININE` |
| 2 | FBS | `FBS` |
| 3 | HbA1c | `HBA1C` |
| 4 | HDL | `HDL` |
| 5 | LDL | `LDL` |
| 6 | Triglycerides | `TRIGLYCERIDES` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | VLDL | `VLDL` |

---

### 0000132

`tpl_03_threecol_dense` · `photocopy_gen3` · `hard` · profile `annual_physical` · mark `tick_in_box`

`media/0000132_photocopy_gen3.png`

**10 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC | `CBC` |
| 2 | Total Cholesterol | `CHOL_TOTAL` |
| 3 | FBS (Fasting Blood Sugar) | `FBS` |
| 4 | Fecal Analysis | `FECALYSIS` |
| 5 | HDL-C | `HDL` |
| 6 | LDL | `LDL` |
| 7 | Triglycerides | `TRIGLYCERIDES` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | VLDL | `VLDL` |
| 10 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000133

`tpl_03_threecol_dense` · `photocopy_gen3` · `hard` · profile `sparse` · mark `tick_overflowing`

`media/0000133_photocopy_gen3.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000134

`tpl_03_threecol_dense` · `photocopy_gen3` · `hard` · profile `hepatitis_screen` · mark `tick_overflowing`

`media/0000134_photocopy_gen3.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | HBsAg (Screening) | `HBSAG_SCREENING` |
| 2 | SGOT/AST | `SGOT_AST` |
| 3 | SGPT/ALT | `SGPT_ALT` |
| 4 | VDRL / RPR | `VDRL_RPR` |

---

### 0000135

`tpl_03_threecol_dense` · `photocopy_gen3` · `hard` · profile `broad` · mark `tick_in_box`

`media/0000135_photocopy_gen3.png`

**23 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Alkaline Phosphatase | `ALP` |
| 2 | Bilirubin (TB, DB, IB) | `BILI_PANEL` |
| 3 | Urea Nitrogen | `BUN` |
| 4 | CBC | `CBC` |
| 5 | Total Cholesterol | `CHOL_TOTAL` |
| 6 | Creatinine | `CREATININE` |
| 7 | 12L ECG | `ECG_12L` |
| 8 | FBS | `FBS` |
| 9 | Fecalysis | `FECALYSIS` |
| 10 | FT4 | `FT4` |
| 11 | HbA1c | `HBA1C` |
| 12 | HBsAg Screening | `HBSAG_SCREENING` |
| 13 | High Density Lipoprotein | `HDL` |
| 14 | K | `K` |
| 15 | Sodium (Na) | `NA` |
| 16 | SGOT / AST | `SGOT_AST` |
| 17 | SGPT / ALT | `SGPT_ALT` |
| 18 | Triglycerides | `TRIGLYCERIDES` |
| 19 | TSH | `TSH` |
| 20 | BUA | `URIC_ACID` |
| 21 | VDRL/RPR | `VDRL_RPR` |
| 22 | VLDL | `VLDL` |
| 23 | Chest PA / L | `XR_CHEST_PA_L` |

⚠ 3 mark(s) drawn faint or ambiguous.

---

### 0000136

`tpl_03_threecol_dense` · `photocopy_gen3` · `hard` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000136_photocopy_gen3.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC | `CBC` |
| 3 | Creatinine | `CREATININE` |
| 4 | Electrocardiogram | `ECG_12L` |
| 5 | PTT (Partial Thromboplastin) | `PTT` |
| 6 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000137

`tpl_03_threecol_dense` · `photocopy_gen3` · `hard` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000137_photocopy_gen3.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC | `CBC` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Potassium (K) | `K` |
| 6 | Sodium (Na) | `NA` |
| 7 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000138

`tpl_03_threecol_dense` · `photocopy_gen3` · `hard` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000138_photocopy_gen3.png`

**10 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC | `CBC` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Potassium (K) | `K` |
| 6 | Sodium (Na) | `NA` |
| 7 | PTT (Partial Thromboplastin) | `PTT` |
| 8 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 9 | UA | `URINALYSIS` |
| 10 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000139

`tpl_03_threecol_dense` · `photocopy_gen3` · `hard` · profile `broad` · mark `diagonal_slash`

`media/0000139_photocopy_gen3.png`

**24 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Alkaline Phosphatase | `ALP` |
| 2 | Bilirubin (TBil, B1, B2) | `BILI_PANEL` |
| 3 | BUN | `BUN` |
| 4 | Complete Blood Count | `CBC` |
| 5 | Total Cholesterol | `CHOL_TOTAL` |
| 6 | Electrocardiogram | `ECG_12L` |
| 7 | FBS | `FBS` |
| 8 | Fecalysis | `FECALYSIS` |
| 9 | FT4 | `FT4` |
| 10 | HbA1c | `HBA1C` |
| 11 | HBsAg Screening | `HBSAG_SCREENING` |
| 12 | HDL | `HDL` |
| 13 | LDL | `LDL` |
| 14 | Sodium (Na) | `NA` |
| 15 | Retic Count | `RETIC` |
| 16 | SGOT/AST | `SGOT_AST` |
| 17 | SGPT/ALT | `SGPT_ALT` |
| 18 | Triglycerides | `TRIGLYCERIDES` |
| 19 | TSH | `TSH` |
| 20 | Uric Acid | `URIC_ACID` |
| 21 | Urinalysis | `URINALYSIS` |
| 22 | Syphilis Screening | `VDRL_RPR` |
| 23 | VLDL Cholesterol | `VLDL` |
| 24 | Chest PA/L | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000140

`tpl_03_threecol_dense` · `fax` · `hard` · profile `annual_physical` · mark `tick_in_box`

`media/0000140_fax.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC | `CBC` |
| 2 | Total Cholesterol | `CHOL_TOTAL` |
| 3 | FBS | `FBS` |
| 4 | Fecalysis | `FECALYSIS` |
| 5 | HDL | `HDL` |
| 6 | LDL | `LDL` |
| 7 | Triglycerides | `TRIGLYCERIDES` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | Chest PA/L | `XR_CHEST_PA_L` |

---

### 0000141

`tpl_03_threecol_dense` · `fax` · `hard` · profile `renal_panel` · mark `tick_in_box`

`media/0000141_fax.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Serum BUN | `BUN` |
| 2 | Ionized Calcium | `CA_IONIZED` |
| 3 | Total Calcium | `CA_TOTAL` |
| 4 | Creatinine | `CREATININE` |
| 5 | Potassium (K) | `K` |
| 6 | Sodium (Na) | `NA` |
| 7 | Urinalysis | `URINALYSIS` |

---

### 0000142

`tpl_03_threecol_dense` · `fax` · `hard` · profile `renal_panel` · mark `tick_in_box`

`media/0000142_fax.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Serum Total Calcium | `CA_TOTAL` |
| 3 | Creatinine | `CREATININE` |
| 4 | Potassium (K) | `K` |
| 5 | Sodium (Na) | `NA` |
| 6 | BUA | `URIC_ACID` |

---

### 0000143

`tpl_03_threecol_dense` · `fax` · `hard` · profile `annual_physical` · mark `tick_overflowing`

`media/0000143_fax.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Complete Blood Count (CBC) | `CBC` |
| 2 | Total Cholesterol | `CHOL_TOTAL` |
| 3 | FBS (Fasting Blood Sugar) | `FBS` |
| 4 | Stool Examination | `FECALYSIS` |
| 5 | HDL | `HDL` |
| 6 | Triglycerides | `TRIGLYCERIDES` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | VLDL | `VLDL` |
| 9 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000144

`tpl_03_threecol_dense` · `fax` · `hard` · profile `breast_mass_workup` · mark `cross`

`media/0000144_fax.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC | `CBC` |
| 2 | Mammogram | `MAMMOGRAM` |

---

### 0000145

`tpl_03_threecol_dense` · `fax` · `hard` · profile `breast_mass_workup` · mark `diagonal_slash`

`media/0000145_fax.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000146

`tpl_03_threecol_dense` · `fax` · `hard` · profile `sparse` · mark `tick_overflowing`

`media/0000146_fax.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC | `CBC` |
| 2 | Urinalysis | `URINALYSIS` |

---

### 0000147

`tpl_03_threecol_dense` · `fax` · `hard` · profile `annual_physical` · mark `circle_around_label`

`media/0000147_fax.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC | `CBC` |
| 2 | Total Cholesterol | `CHOL_TOTAL` |
| 3 | Fecalysis | `FECALYSIS` |
| 4 | HDL-C | `HDL` |
| 5 | LDL | `LDL` |
| 6 | Triglycerides | `TRIGLYCERIDES` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | VLDL | `VLDL` |
| 9 | Chest PA/L | `XR_CHEST_PA_L` |

---

### 0000148

`tpl_03_threecol_dense` · `fax` · `hard` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000148_fax.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC | `CBC` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Serum Potassium | `K` |
| 6 | Sodium | `NA` |
| 7 | PTT (Partial Thromboplastin) | `PTT` |
| 8 | PT (Prothrombin) | `PT_PROTHROMBIN` |
| 9 | Urinalysis | `URINALYSIS` |

---

### 0000149

`tpl_03_threecol_dense` · `fax` · `hard` · profile `renal_panel` · mark `tick_overflowing`

`media/0000149_fax.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Urea Nitrogen | `BUN` |
| 2 | Ionized Calcium | `CA_IONIZED` |
| 3 | Total Calcium | `CA_TOTAL` |
| 4 | Crea | `CREATININE` |
| 5 | Potassium (K) | `K` |
| 6 | Sodium (Na) | `NA` |
| 7 | Uric Acid | `URIC_ACID` |
| 8 | Urinalysis | `URINALYSIS` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000150

`tpl_04_halfsheet_compact` · `clean` · `easy` · profile `annual_physical` · mark `cross`

`media/0000150_clean.png`

**1 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Chest PA / L | `XR_CHEST_PA_L` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Lipid Profile~~ `LIPID_PROFILE`

---

### 0000151

`tpl_04_halfsheet_compact` · `clean` · `easy` · profile `breast_mass_workup` · mark `filled_scribble`

`media/0000151_clean.png`

**1 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |

---

### 0000152

`tpl_04_halfsheet_compact` · `clean` · `easy` · profile `liver_evaluation` · mark `tick_in_box`

`media/0000152_clean.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | ALP (Alkaline Phosphatase) | `ALP` |
| 2 | Bilirubin (TB, DB, IB) | `BILI_PANEL` |
| 3 | SGOT / AST | `SGOT_AST` |
| 4 | SGPT (ALT) | `SGPT_ALT` |

---

### 0000153

`tpl_04_halfsheet_compact` · `clean` · `easy` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000153_clean.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ PLT CT | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12-lead ECG | `ECG_12L` |
| 5 | Sodium (Na) | `NA` |
| 6 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 7 | Urinalysis | `URINALYSIS` |
| 8 | Chest PA/L | `XR_CHEST_PA_L` |

---

### 0000154

`tpl_04_halfsheet_compact` · `clean` · `easy` · profile `thyroid_workup` · mark `tick_in_box`

`media/0000154_clean.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | TSH | `TSH` |
| 4 | Thyroid | `US_THYROID` |

---

### 0000155

`tpl_04_halfsheet_compact` · `clean` · `easy` · profile `cardiac_chest_pain` · mark `tick_overflowing`

`media/0000155_clean.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Serum Chloride | `CL` |
| 2 | Electrocardiography | `ECG_12L` |
| 3 | 2D Echocardiogram | `ECHO_2D` |
| 4 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000156

`tpl_04_halfsheet_compact` · `clean` · `easy` · profile `preoperative_clearance` · mark `tick_overflowing`

`media/0000156_clean.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | Electrocardiography | `ECG_12L` |
| 5 | Potassium (K) | `K` |
| 6 | Sodium (Na) | `NA` |
| 7 | PTT (Partial Thromboplastin) | `PTT` |
| 8 | Urinalysis (Routine) | `URINALYSIS` |

**2 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~PT (Prothrombin)~~ `PT_PROTHROMBIN`
- ~~Chest PA/L~~ `XR_CHEST_PA_L`

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000157

`tpl_04_halfsheet_compact` · `clean` · `easy` · profile `hepatitis_screen` · mark `tick_overflowing`

`media/0000157_clean.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | HBsAg Screening | `HBSAG_SCREENING` |
| 2 | SGOT/AST | `SGOT_AST` |
| 3 | SGPT/ALT | `SGPT_ALT` |
| 4 | VDRL / RPR | `VDRL_RPR` |

---

### 0000158

`tpl_04_halfsheet_compact` · `clean` · `easy` · profile `annual_physical` · mark `cross`

`media/0000158_clean.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT CT | `CBC_PLT` |
| 2 | FBG | `FBS` |
| 3 | Fecalysis | `FECALYSIS` |
| 4 | Lipid Studies | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |
| 6 | Chest PA / L | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000159

`tpl_04_halfsheet_compact` · `clean` · `easy` · profile `prenatal` · mark `filled_scribble`

`media/0000159_clean.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Typing / Rh | `BLOOD_TYPING_RH` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | OGTT | `OGTT` |
| 5 | Pregnancy Test | `PREGNANCY_TEST` |
| 6 | Urinalysis | `URINALYSIS` |
| 7 | Syphilis Screening | `VDRL_RPR` |

**Variant sub-options circled:** `OGTT` → **g100**

---

### 0000160

`tpl_04_halfsheet_compact` · `scan` · `easy` · profile `diabetes_monitoring` · mark `tick_in_box`

`media/0000160_scan.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Creatinine | `CREATININE` |
| 2 | Fasting Blood Sugar | `FBS` |
| 3 | HbA1c | `HBA1C` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |

---

### 0000161

`tpl_04_halfsheet_compact` · `scan` · `easy` · profile `annual_physical` · mark `tick_overflowing`

`media/0000161_scan.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |
| 2 | FBS | `FBS` |
| 3 | Stool Exam | `FECALYSIS` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |
| 6 | Chest PA/L | `XR_CHEST_PA_L` |

---

### 0000162

`tpl_04_halfsheet_compact` · `scan` · `easy` · profile `liver_evaluation` · mark `diagonal_slash`

`media/0000162_scan.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Alk Phos | `ALP` |
| 2 | Bilirubins | `BILI_PANEL` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | SGOT / AST | `SGOT_AST` |
| 5 | SGPT / ALT | `SGPT_ALT` |

---

### 0000163

`tpl_04_halfsheet_compact` · `scan` · `easy` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000163_scan.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Creatinine | `CREATININE` |
| 2 | 12L ECG | `ECG_12L` |
| 3 | Potassium (K) | `K` |
| 4 | Sodium (Na) | `NA` |
| 5 | PTT (Partial Thromboplastin) | `PTT` |
| 6 | Urinalysis | `URINALYSIS` |
| 7 | Chest PA / L | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000164

`tpl_04_halfsheet_compact` · `scan` · `easy` · profile `diabetes_monitoring` · mark `tick_in_box`

`media/0000164_scan.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Creatinine | `CREATININE` |
| 2 | FBS | `FBS` |
| 3 | HbA1c | `HBA1C` |
| 4 | Lipid Profile | `LIPID_PROFILE` |

---

### 0000165

`tpl_04_halfsheet_compact` · `scan` · `easy` · profile `diabetes_monitoring` · mark `diagonal_slash`

`media/0000165_scan.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Creatinine | `CREATININE` |
| 2 | FBS (Fasting Blood Sugar) | `FBS` |
| 3 | HbA1c | `HBA1C` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |
| 6 | Chest AP / L | `XR_CHEST_AP_L` |

---

### 0000166

`tpl_04_halfsheet_compact` · `scan` · `easy` · profile `liver_evaluation` · mark `tick_in_box`

`media/0000166_scan.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Bilirubin (TBil, B1, B2) | `BILI_PANEL` |
| 2 | SGOT/AST | `SGOT_AST` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~SGPT/ALT~~ `SGPT_ALT`

---

### 0000167

`tpl_04_halfsheet_compact` · `scan` · `easy` · profile `preoperative_clearance` · mark `cross`

`media/0000167_scan.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Creatinine | `CREATININE` |
| 3 | 12-lead ECG | `ECG_12L` |
| 4 | Potassium (K) | `K` |
| 5 | Sodium (Na) | `NA` |
| 6 | PTT (Partial Thromboplastin) | `PTT` |
| 7 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | Chest PA-L | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000168

`tpl_04_halfsheet_compact` · `scan` · `easy` · profile `annual_physical` · mark `cross`

`media/0000168_scan.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Fecalysis | `FECALYSIS` |
| 2 | Urinalysis | `URINALYSIS` |
| 3 | Chest PA / L | `XR_CHEST_PA_L` |

**2 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~CBC w/ Platelet Count~~ `CBC_PLT`
- ~~Lipid Profile~~ `LIPID_PROFILE`

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000169

`tpl_04_halfsheet_compact` · `scan` · `easy` · profile `annual_physical` · mark `circle_around_box`

`media/0000169_scan.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT CT | `CBC_PLT` |
| 2 | FBS (Fasting Blood Sugar) | `FBS` |
| 3 | Fecalysis | `FECALYSIS` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |
| 6 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000170

`tpl_04_halfsheet_compact` · `photocopy_gen1` · `medium` · profile `diabetes_monitoring` · mark `tick_overflowing`

`media/0000170_photocopy_gen1.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Creatinine | `CREATININE` |
| 2 | FBS | `FBS` |
| 3 | HbA1c | `HBA1C` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000171

`tpl_04_halfsheet_compact` · `photocopy_gen1` · `medium` · profile `liver_evaluation` · mark `cross`

`media/0000171_photocopy_gen1.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Alkaline Phosphatase | `ALP` |
| 2 | HBsAg Screening | `HBSAG_SCREENING` |
| 3 | SGOT/AST | `SGOT_AST` |
| 4 | SGPT / ALT | `SGPT_ALT` |

---

### 0000172

`tpl_04_halfsheet_compact` · `photocopy_gen1` · `medium` · profile `broad` · mark `tick_in_box`

`media/0000172_photocopy_gen1.png`

**18 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Alkaline Phosphatase | `ALP` |
| 2 | Bilirubin (TBil, B1, B2) | `BILI_PANEL` |
| 3 | BUN | `BUN` |
| 4 | Creatinine | `CREATININE` |
| 5 | Electrocardiogram | `ECG_12L` |
| 6 | FBS | `FBS` |
| 7 | Fecalysis | `FECALYSIS` |
| 8 | FT4 | `FT4` |
| 9 | HbA1c | `HBA1C` |
| 10 | HBsAg Screening | `HBSAG_SCREENING` |
| 11 | Potassium (K) | `K` |
| 12 | Lipid Profile | `LIPID_PROFILE` |
| 13 | Na | `NA` |
| 14 | SGOT / AST | `SGOT_AST` |
| 15 | SGPT/ALT | `SGPT_ALT` |
| 16 | BUA | `URIC_ACID` |
| 17 | Urinalysis | `URINALYSIS` |
| 18 | VDRL/RPR | `VDRL_RPR` |

---

### 0000173

`tpl_04_halfsheet_compact` · `photocopy_gen1` · `medium` · profile `thyroid_workup` · mark `tick_in_box`

`media/0000173_photocopy_gen1.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | TSH | `TSH` |

---

### 0000174

`tpl_04_halfsheet_compact` · `photocopy_gen1` · `medium` · profile `breast_mass_workup` · mark `cross`

`media/0000174_photocopy_gen1.png`

**1 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Breast | `US_BREAST` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~CBC w/ PLT CT~~ `CBC_PLT`

---

### 0000175

`tpl_04_halfsheet_compact` · `photocopy_gen1` · `medium` · profile `annual_physical` · mark `tick_in_box`

`media/0000175_photocopy_gen1.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC with Platelet Count | `CBC_PLT` |
| 2 | FBS (Fasting Blood Sugar) | `FBS` |
| 3 | Fecalysis | `FECALYSIS` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |
| 6 | Chest PA / L | `XR_CHEST_PA_L` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000176

`tpl_04_halfsheet_compact` · `photocopy_gen1` · `medium` · profile `annual_physical` · mark `tick_overflowing`

`media/0000176_photocopy_gen1.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC with Platelet Count | `CBC_PLT` |
| 2 | FBS | `FBS` |
| 3 | Stool Examination | `FECALYSIS` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |
| 6 | Chest X-ray PA and Lateral | `XR_CHEST_PA_L` |

---

### 0000177

`tpl_04_halfsheet_compact` · `photocopy_gen1` · `medium` · profile `liver_evaluation` · mark `filled_scribble`

`media/0000177_photocopy_gen1.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | ALP (Alkaline Phosphatase) | `ALP` |
| 2 | Bilirubins | `BILI_PANEL` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | SGPT/ALT | `SGPT_ALT` |

---

### 0000178

`tpl_04_halfsheet_compact` · `photocopy_gen1` · `medium` · profile `liver_evaluation` · mark `circle_around_box`

`media/0000178_photocopy_gen1.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Alkaline Phosphatase | `ALP` |
| 2 | Bilirubin (TB, DB, IB) | `BILI_PANEL` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | SGOT/AST | `SGOT_AST` |
| 5 | SGPT/ALT | `SGPT_ALT` |

---

### 0000179

`tpl_04_halfsheet_compact` · `photocopy_gen1` · `medium` · profile `hepatitis_screen` · mark `tick_in_box`

`media/0000179_photocopy_gen1.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | HBsAg Screening | `HBSAG_SCREENING` |
| 2 | SGOT / AST | `SGOT_AST` |
| 3 | VDRL / RPR | `VDRL_RPR` |

---

### 0000180

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `prenatal` · mark `tick_in_box`

`media/0000180_photocopy_gen3.png`

**7 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Blood Typing / Rh | `BLOOD_TYPING_RH` |
| 2 | CBC w/ PLT CT | `CBC_PLT` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | OGTT | `OGTT` |
| 5 | Pregnancy Test | `PREGNANCY_TEST` |
| 6 | Urinalysis | `URINALYSIS` |
| 7 | VDRL/RPR | `VDRL_RPR` |

**Variant sub-options circled:** `OGTT` → **g100**, `PREGNANCY_TEST` → **serum**

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000181

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `thyroid_workup` · mark `filled_scribble`

`media/0000181_photocopy_gen3.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | Thyroid | `US_THYROID` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~TSH~~ `TSH`

---

### 0000182

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000182_photocopy_gen3.png`

**9 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ Platelet Count | `CBC_PLT` |
| 3 | Creatinine | `CREATININE` |
| 4 | 12L ECG | `ECG_12L` |
| 5 | Potassium (K) | `K` |
| 6 | Sodium (Na) | `NA` |
| 7 | PTT (Partial Thromboplastin) | `PTT` |
| 8 | Urinalysis | `URINALYSIS` |
| 9 | Chest PA and lateral | `XR_CHEST_PA_L` |

---

### 0000183

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `sparse` · mark `circle_around_box`

`media/0000183_photocopy_gen3.png`

**1 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC with Platelet Count | `CBC_PLT` |

---

### 0000184

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `diabetes_monitoring` · mark `tick_in_box`

`media/0000184_photocopy_gen3.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Serum Creatinine | `CREATININE` |
| 2 | FBS | `FBS` |
| 3 | HbA1c | `HBA1C` |
| 4 | Lipid Profile (TC/TG/HDL/LDL/VLDL) | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |

---

### 0000185

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `thyroid_workup` · mark `tick_overflowing`

`media/0000185_photocopy_gen3.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | Free T4 | `FT4` |
| 3 | TSH | `TSH` |
| 4 | Thyroid | `US_THYROID` |

---

### 0000186

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `preoperative_clearance` · mark `tick_in_box`

`media/0000186_photocopy_gen3.png`

**8 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | CBC w/ PLT CT | `CBC_PLT` |
| 3 | Serum Creatinine | `CREATININE` |
| 4 | Electrocardiogram | `ECG_12L` |
| 5 | Potassium (K) | `K` |
| 6 | Sodium (Na) | `NA` |
| 7 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |
| 8 | Urinalysis | `URINALYSIS` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~PTT (Partial Thromboplastin)~~ `PTT`

---

### 0000187

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `liver_evaluation` · mark `diagonal_slash`

`media/0000187_photocopy_gen3.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | ALP (Alkaline Phosphatase) | `ALP` |
| 2 | Bilirubin (TBil, B1, B2) | `BILI_PANEL` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | SGOT / AST | `SGOT_AST` |
| 5 | SGPT/ALT | `SGPT_ALT` |

---

### 0000188

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `liver_evaluation` · mark `circle_around_box`

`media/0000188_photocopy_gen3.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | ALP (Alkaline Phosphatase) | `ALP` |
| 2 | Bilirubin (TB, DB, IB) | `BILI_PANEL` |
| 3 | HBsAg Screening | `HBSAG_SCREENING` |
| 4 | SGOT / AST | `SGOT_AST` |
| 5 | SGPT / ALT | `SGPT_ALT` |

---

### 0000189

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `annual_physical` · mark `circle_around_label`

`media/0000189_photocopy_gen3.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT CT | `CBC_PLT` |
| 2 | FBS | `FBS` |
| 3 | Stool Exam | `FECALYSIS` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |
| 6 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000190

`tpl_04_halfsheet_compact` · `fax` · `hard` · profile `annual_physical` · mark `cross`

`media/0000190_fax.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT CT | `CBC_PLT` |
| 2 | FBS | `FBS` |
| 3 | Lipid Profile | `LIPID_PROFILE` |
| 4 | Urinalysis | `URINALYSIS` |
| 5 | Chest PA/L | `XR_CHEST_PA_L` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Fecalysis~~ `FECALYSIS`

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000191

`tpl_04_halfsheet_compact` · `fax` · `hard` · profile `renal_panel` · mark `cross`

`media/0000191_fax.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | BUN | `BUN` |
| 2 | Calcium (Ca) | `CA_SERUM` |
| 3 | Creatinine | `CREATININE` |
| 4 | Potassium (K) | `K` |
| 5 | Sodium (Na) | `NA` |
| 6 | Urinalysis | `URINALYSIS` |

**Variant sub-options circled:** `CA_SERUM` → **ionized**

⚠ 2 mark(s) drawn faint or ambiguous.

---

### 0000192

`tpl_04_halfsheet_compact` · `fax` · `hard` · profile `sparse` · mark `circle_around_box`

`media/0000192_fax.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC with Platelet Count | `CBC_PLT` |
| 2 | Urinalysis | `URINALYSIS` |

---

### 0000193

`tpl_04_halfsheet_compact` · `fax` · `hard` · profile `annual_physical` · mark `tick_in_box`

`media/0000193_fax.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT CT | `CBC_PLT` |
| 2 | FBS | `FBS` |
| 3 | Lipid Profile | `LIPID_PROFILE` |
| 4 | Urinalysis | `URINALYSIS` |

---

### 0000194

`tpl_04_halfsheet_compact` · `fax` · `hard` · profile `sparse` · mark `cross`

`media/0000194_fax.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000195

`tpl_04_halfsheet_compact` · `fax` · `hard` · profile `sparse` · mark `tick_in_box`

`media/0000195_fax.png`

**1 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ PLT CT | `CBC_PLT` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Urinalysis~~ `URINALYSIS`

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000196

`tpl_04_halfsheet_compact` · `fax` · `hard` · profile `annual_physical` · mark `tick_in_box`

`media/0000196_fax.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC w/ Platelet Count | `CBC_PLT` |
| 2 | Fasting Blood Glucose | `FBS` |
| 3 | Fecalysis | `FECALYSIS` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Urinalysis | `URINALYSIS` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Chest X-ray PA and Lateral~~ `XR_CHEST_PA_L`

---

### 0000197

`tpl_04_halfsheet_compact` · `fax` · `hard` · profile `thyroid_workup` · mark `tick_overflowing`

`media/0000197_fax.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | TSH | `TSH` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Thyroid~~ `US_THYROID`

---

### 0000198

`tpl_04_halfsheet_compact` · `fax` · `hard` · profile `cardiac_chest_pain` · mark `tick_in_box`

`media/0000198_fax.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Electrocardiogram | `ECG_12L` |
| 2 | 2D Echo | `ECHO_2D` |
| 3 | Chest PA / L | `XR_CHEST_PA_L` |

---

### 0000199

`tpl_04_halfsheet_compact` · `fax` · `hard` · profile `liver_evaluation` · mark `filled_scribble`

`media/0000199_fax.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Alkaline Phosphatase | `ALP` |
| 2 | Bilirubins | `BILI_PANEL` |
| 3 | SGOT / AST | `SGOT_AST` |
| 4 | SGPT/ALT | `SGPT_ALT` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~HBsAg Screening~~ `HBSAG_SCREENING`

---

### 0000200  —  **stress: stress_bundle_and_components**

`tpl_02_twocol_serif` · `clean` · `easy` · profile `stress_bundle_and_components` · mark `tick_in_box`

`media/0000200_clean.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | T. Chole | `CHOL_TOTAL` |
| 2 | HDL | `HDL` |
| 3 | LDL Cholesterol | `LDL` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Trigs | `TRIGLYCERIDES` |
| 6 | VLDL | `VLDL` |

---

### 0000201  —  **stress: stress_bundle_and_components**

`tpl_02_twocol_serif` · `scan` · `easy` · profile `stress_bundle_and_components` · mark `tick_in_box`

`media/0000201_scan.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Serum Cholesterol | `CHOL_TOTAL` |
| 2 | HDL | `HDL` |
| 3 | LDL | `LDL` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Triglycerides | `TRIGLYCERIDES` |
| 6 | VLDL | `VLDL` |

---

### 0000202  —  **stress: stress_bundle_and_components**

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `stress_bundle_and_components` · mark `filled_scribble`

`media/0000202_photocopy_gen1.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total Cholesterol | `CHOL_TOTAL` |
| 2 | HDL | `HDL` |
| 3 | LDL Cholesterol | `LDL` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Triglycerides | `TRIGLYCERIDES` |
| 6 | VLDL | `VLDL` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000203  —  **stress: stress_bundle_and_components**

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `stress_bundle_and_components` · mark `cross`

`media/0000203_photocopy_gen3.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total Cholesterol | `CHOL_TOTAL` |
| 2 | HDL | `HDL` |
| 3 | LDL | `LDL` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Triglycerides | `TRIGLYCERIDES` |
| 6 | VLDL | `VLDL` |

---

### 0000204  —  **stress: stress_bundle_and_components**

`tpl_02_twocol_serif` · `fax` · `hard` · profile `stress_bundle_and_components` · mark `filled_scribble`

`media/0000204_fax.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total Cholesterol | `CHOL_TOTAL` |
| 2 | HDL | `HDL` |
| 3 | LDL | `LDL` |
| 4 | Lipid Profile | `LIPID_PROFILE` |
| 5 | Trigs | `TRIGLYCERIDES` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~VLDL~~ `VLDL`

---

### 0000205  —  **stress: stress_ldl_ldh**

`tpl_02_twocol_serif` · `clean` · `easy` · profile `stress_ldl_ldh` · mark `tick_overflowing`

`media/0000205_clean.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total CPK | `CPK_TOTAL` |
| 2 | HDL | `HDL` |
| 3 | LDH | `LDH` |
| 4 | LDL Cholesterol | `LDL` |

---

### 0000206  —  **stress: stress_ldl_ldh**

`tpl_03_threecol_dense` · `scan` · `easy` · profile `stress_ldl_ldh` · mark `tick_in_box`

`media/0000206_scan.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CPK | `CPK_TOTAL` |
| 2 | HDL | `HDL` |
| 3 | LDH | `LDH` |
| 4 | Low Density Lipoprotein | `LDL` |

---

### 0000207  —  **stress: stress_ldl_ldh**

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `stress_ldl_ldh` · mark `tick_in_box`

`media/0000207_photocopy_gen1.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Creatine Phosphokinase | `CPK_TOTAL` |
| 2 | LDH | `LDH` |
| 3 | LDL | `LDL` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~HDL~~ `HDL`

---

### 0000208  —  **stress: stress_ldl_ldh**

`tpl_03_threecol_dense` · `photocopy_gen3` · `hard` · profile `stress_ldl_ldh` · mark `cross`

`media/0000208_photocopy_gen3.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total CPK | `CPK_TOTAL` |
| 2 | HDL | `HDL` |
| 3 | LDH | `LDH` |
| 4 | LDL-C | `LDL` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000209  —  **stress: stress_ldl_ldh**

`tpl_02_twocol_serif` · `fax` · `hard` · profile `stress_ldl_ldh` · mark `cross`

`media/0000209_fax.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Total CPK | `CPK_TOTAL` |
| 2 | HDL | `HDL` |
| 3 | LDH | `LDH` |
| 4 | LDL Cholesterol | `LDL` |

---

### 0000210  —  **stress: stress_pt_ptt**

`tpl_01_onecol_sans` · `clean` · `easy` · profile `stress_pt_ptt` · mark `tick_in_box`

`media/0000210_clean.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Bleeding Time | `BLEEDING_TIME` |
| 2 | Clotting Time | `CLOTTING_TIME` |
| 3 | PTT (Partial Thromboplastin) | `PTT` |
| 4 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |

---

### 0000211  —  **stress: stress_pt_ptt**

`tpl_02_twocol_serif` · `scan` · `easy` · profile `stress_pt_ptt` · mark `diagonal_slash`

`media/0000211_scan.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Bleeding Time | `BLEEDING_TIME` |
| 2 | Clotting Time | `CLOTTING_TIME` |
| 3 | PTT (Partial Thromboplastin) | `PTT` |
| 4 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |

---

### 0000212  —  **stress: stress_pt_ptt**

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `stress_pt_ptt` · mark `tick_in_box`

`media/0000212_photocopy_gen1.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | PTT | `PTT` |
| 2 | PT (Prothrombin Time) | `PT_PROTHROMBIN` |

**2 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Bleeding Time~~ `BLEEDING_TIME`
- ~~Clotting Time~~ `CLOTTING_TIME`

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000213  —  **stress: stress_pt_ptt**

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `stress_pt_ptt` · mark `tick_in_box`

`media/0000213_photocopy_gen3.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Bleeding Time | `BLEEDING_TIME` |
| 2 | PTT (Partial Thromboplastin) | `PTT` |
| 3 | PT (Prothrombin) | `PT_PROTHROMBIN` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Clotting Time~~ `CLOTTING_TIME`

---

### 0000214  —  **stress: stress_pt_ptt**

`tpl_01_onecol_sans` · `fax` · `hard` · profile `stress_pt_ptt` · mark `circle_around_label`

`media/0000214_fax.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Bleeding Time | `BLEEDING_TIME` |
| 2 | Clotting Time | `CLOTTING_TIME` |
| 3 | aPTT | `PTT` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~PT (Prothrombin)~~ `PT_PROTHROMBIN`

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000215  —  **stress: stress_hepatitis_family**

`tpl_01_onecol_sans` · `clean` · `easy` · profile `stress_hepatitis_family` · mark `tick_in_box`

`media/0000215_clean.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Anti-HBc | `ANTI_HBC` |
| 2 | Anti-HBe | `ANTI_HBE` |
| 3 | Anti-HBs | `ANTI_HBS` |
| 4 | HBsAg Screening | `HBSAG_SCREENING` |
| 5 | HBsAg Quantitative | `HBSAG_TITER` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000216  —  **stress: stress_hepatitis_family**

`tpl_02_twocol_serif` · `scan` · `easy` · profile `stress_hepatitis_family` · mark `tick_overflowing`

`media/0000216_scan.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Anti-HBc | `ANTI_HBC` |
| 2 | Anti-HBe | `ANTI_HBE` |
| 3 | Anti-HBs | `ANTI_HBS` |
| 4 | HBsAg Screening | `HBSAG_SCREENING` |
| 5 | HBsAg with Titer | `HBSAG_TITER` |

---

### 0000217  —  **stress: stress_hepatitis_family**

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `stress_hepatitis_family` · mark `cross`

`media/0000217_photocopy_gen1.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Anti-HBc | `ANTI_HBC` |
| 2 | Anti-HBe | `ANTI_HBE` |
| 3 | Anti HBs | `ANTI_HBS` |
| 4 | HBsAg Screening | `HBSAG_SCREENING` |
| 5 | HBsAg with Titer | `HBSAG_TITER` |

---

### 0000218  —  **stress: stress_hepatitis_family**

`tpl_01_onecol_sans` · `photocopy_gen3` · `hard` · profile `stress_hepatitis_family` · mark `circle_around_label`

`media/0000218_photocopy_gen3.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Anti-HBc | `ANTI_HBC` |
| 2 | Anti-HBe | `ANTI_HBE` |
| 3 | Anti-HBs | `ANTI_HBS` |
| 4 | HBsAg Screening | `HBSAG_SCREENING` |
| 5 | HBsAg Quantitative | `HBSAG_TITER` |

---

### 0000219  —  **stress: stress_hepatitis_family**

`tpl_02_twocol_serif` · `fax` · `hard` · profile `stress_hepatitis_family` · mark `tick_in_box`

`media/0000219_fax.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Anti-HBc | `ANTI_HBC` |
| 2 | Anti-HBe | `ANTI_HBE` |
| 3 | Anti HBs | `ANTI_HBS` |
| 4 | HBsAg Screening | `HBSAG_SCREENING` |
| 5 | HBsAg with Titer | `HBSAG_TITER` |

---

### 0000220  —  **stress: stress_thyroid_panel_and_us**

`tpl_01_onecol_sans` · `clean` · `easy` · profile `stress_thyroid_panel_and_us` · mark `circle_around_label`

`media/0000220_clean.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | T3 | `T3` |
| 4 | T4 | `T4` |
| 5 | TSH | `TSH` |
| 6 | Thyroid | `US_THYROID` |

---

### 0000221  —  **stress: stress_thyroid_panel_and_us**

`tpl_02_twocol_serif` · `scan` · `easy` · profile `stress_thyroid_panel_and_us` · mark `cross`

`media/0000221_scan.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Free Triiodothyronine | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | Triiodothyronine | `T3` |
| 4 | T4 | `T4` |
| 5 | TSH | `TSH` |
| 6 | Thyroid | `US_THYROID` |

---

### 0000222  —  **stress: stress_thyroid_panel_and_us**

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `stress_thyroid_panel_and_us` · mark `circle_around_box`

`media/0000222_photocopy_gen1.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | T3 | `T3` |
| 4 | T4 | `T4` |
| 5 | TSH | `TSH` |
| 6 | Thyroid | `US_THYROID` |

---

### 0000223  —  **stress: stress_thyroid_panel_and_us**

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `stress_thyroid_panel_and_us` · mark `cross`

`media/0000223_photocopy_gen3.png`

**5 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | FT3 | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | T3 | `T3` |
| 4 | T4 | `T4` |
| 5 | TSH | `TSH` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Thyroid~~ `US_THYROID`

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000224  —  **stress: stress_thyroid_panel_and_us**

`tpl_01_onecol_sans` · `fax` · `hard` · profile `stress_thyroid_panel_and_us` · mark `tick_overflowing`

`media/0000224_fax.png`

**6 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Free Triiodothyronine | `FT3` |
| 2 | FT4 | `FT4` |
| 3 | T3 | `T3` |
| 4 | Total T4 | `T4` |
| 5 | TSH | `TSH` |
| 6 | Thyroid | `US_THYROID` |

---

### 0000225  —  **stress: stress_kub_both_sections**

`tpl_01_onecol_sans` · `clean` · `easy` · profile `stress_kub_both_sections` · mark `tick_overflowing`

`media/0000225_clean.png`

**1 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | KUB | `XR_KUB` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~KUB~~ `US_KUB`

---

### 0000226  —  **stress: stress_kub_both_sections**

`tpl_02_twocol_serif` · `scan` · `easy` · profile `stress_kub_both_sections` · mark `tick_overflowing`

`media/0000226_scan.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | KUB | `US_KUB` |
| 2 | KUB | `XR_KUB` |

---

### 0000227  —  **stress: stress_kub_both_sections**

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `stress_kub_both_sections` · mark `cross`

`media/0000227_photocopy_gen1.png`

**1 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | KUB | `US_KUB` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~KUB~~ `XR_KUB`

---

### 0000228  —  **stress: stress_kub_both_sections**

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `stress_kub_both_sections` · mark `tick_overflowing`

`media/0000228_photocopy_gen3.png`

**1 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | KUB | `US_KUB` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~KUB~~ `XR_KUB`

---

### 0000229  —  **stress: stress_kub_both_sections**

`tpl_01_onecol_sans` · `fax` · `hard` · profile `stress_kub_both_sections` · mark `filled_scribble`

`media/0000229_fax.png`

**2 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | KUB | `US_KUB` |
| 2 | Plain Abdomen | `XR_KUB` |

---

### 0000230  —  **stress: stress_electrolytes_bundle_and_parts**

`tpl_02_twocol_serif` · `clean` · `easy` · profile `stress_electrolytes_bundle_and_parts` · mark `tick_in_box`

`media/0000230_clean.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Chloride (Cl) | `CL` |
| 2 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 3 | Potassium (K) | `K` |
| 4 | Sodium (Na) | `NA` |

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000231  —  **stress: stress_electrolytes_bundle_and_parts**

`tpl_02_twocol_serif` · `scan` · `easy` · profile `stress_electrolytes_bundle_and_parts` · mark `tick_overflowing`

`media/0000231_scan.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Chloride | `CL` |
| 2 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 3 | Serum Potassium | `K` |
| 4 | Sodium (Na) | `NA` |

---

### 0000232  —  **stress: stress_electrolytes_bundle_and_parts**

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `stress_electrolytes_bundle_and_parts` · mark `tick_overflowing`

`media/0000232_photocopy_gen1.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Chloride (Cl) | `CL` |
| 2 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 3 | Potassium (K) | `K` |

**1 cancelled** — struck through, so NOT ordered and NOT in the expected set:

- ~~Serum Sodium~~ `NA`

⚠ 1 mark(s) drawn faint or ambiguous.

---

### 0000233  —  **stress: stress_electrolytes_bundle_and_parts**

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `stress_electrolytes_bundle_and_parts` · mark `diagonal_slash`

`media/0000233_photocopy_gen3.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Chloride (Cl) | `CL` |
| 2 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 3 | Potassium (K) | `K` |
| 4 | Sodium (Na) | `NA` |

---

### 0000234  —  **stress: stress_electrolytes_bundle_and_parts**

`tpl_02_twocol_serif` · `fax` · `hard` · profile `stress_electrolytes_bundle_and_parts` · mark `tick_overflowing`

`media/0000234_fax.png`

**4 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Chloride (Cl) | `CL` |
| 2 | Serum Electrolytes (Na, K, Cl) | `ELECTROLYTES` |
| 3 | Potassium (K) | `K` |
| 4 | Sodium (Na) | `NA` |

---

### 0000235  —  **stress: stress_cbc_both**

`tpl_02_twocol_serif` · `clean` · `easy` · profile `stress_cbc_both` · mark `tick_overflowing`

`media/0000235_clean.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC only | `CBC` |
| 2 | CBC w/ Platelet Count | `CBC_PLT` |
| 3 | Platelet Count | `PLATELET_COUNT` |

---

### 0000236  —  **stress: stress_cbc_both**

`tpl_02_twocol_serif` · `scan` · `easy` · profile `stress_cbc_both` · mark `cross`

`media/0000236_scan.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC | `CBC` |
| 2 | CBC w/ PLT CT | `CBC_PLT` |
| 3 | Platelet Count | `PLATELET_COUNT` |

---

### 0000237  —  **stress: stress_cbc_both**

`tpl_02_twocol_serif` · `photocopy_gen1` · `medium` · profile `stress_cbc_both` · mark `tick_in_box`

`media/0000237_photocopy_gen1.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC | `CBC` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | Plt Ct | `PLATELET_COUNT` |

---

### 0000238  —  **stress: stress_cbc_both**

`tpl_02_twocol_serif` · `photocopy_gen3` · `hard` · profile `stress_cbc_both` · mark `tick_in_box`

`media/0000238_photocopy_gen3.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | Complete Blood Count | `CBC` |
| 2 | CBC w/ PLT CT | `CBC_PLT` |
| 3 | Platelet Count | `PLATELET_COUNT` |

---

### 0000239  —  **stress: stress_cbc_both**

`tpl_02_twocol_serif` · `fax` · `hard` · profile `stress_cbc_both` · mark `cross`

`media/0000239_fax.png`

**3 checked**

| # | As printed on the form | Code |
|---:|---|---|
| 1 | CBC | `CBC` |
| 2 | CBC with Platelet Count | `CBC_PLT` |
| 3 | Platelet Count | `PLATELET_COUNT` |

---

### 0000240  —  **BLANK — zero marks**

`tpl_01_onecol_sans` · `clean` · `easy` · profile `blank_form`

`media/0000240_clean.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000241  —  **BLANK — zero marks**

`tpl_02_twocol_serif` · `scan` · `easy` · profile `blank_form`

`media/0000241_scan.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000242  —  **BLANK — zero marks**

`tpl_03_threecol_dense` · `photocopy_gen1` · `medium` · profile `blank_form`

`media/0000242_photocopy_gen1.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000243  —  **BLANK — zero marks**

`tpl_04_halfsheet_compact` · `photocopy_gen3` · `hard` · profile `blank_form`

`media/0000243_photocopy_gen3.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000244  —  **BLANK — zero marks**

`tpl_01_onecol_sans` · `fax` · `hard` · profile `blank_form`

`media/0000244_fax.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000245  —  **BLANK — zero marks**

`tpl_02_twocol_serif` · `clean` · `easy` · profile `blank_form`

`media/0000245_clean.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000246  —  **BLANK — zero marks**

`tpl_03_threecol_dense` · `scan` · `easy` · profile `blank_form`

`media/0000246_scan.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000247  —  **BLANK — zero marks**

`tpl_04_halfsheet_compact` · `photocopy_gen1` · `medium` · profile `blank_form`

`media/0000247_photocopy_gen1.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000248  —  **BLANK — zero marks**

`tpl_01_onecol_sans` · `photocopy_gen3` · `hard` · profile `blank_form`

`media/0000248_photocopy_gen3.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000249  —  **BLANK — zero marks**

`tpl_02_twocol_serif` · `fax` · `hard` · profile `blank_form`

`media/0000249_fax.png`

Expected: **no tests checked**. Anything reported here is a hallucination.

---

### 0000250  —  **NOT A LAB REQUEST** (lab_result_report)

`(no template)` · `clean` · `easy`

`media/0000250_clean.png`

Expected: empty set, and `is_laboratory_request: false`.

---

### 0000251  —  **NOT A LAB REQUEST** (prescription)

`(no template)` · `scan` · `easy`

`media/0000251_scan.png`

Expected: empty set, and `is_laboratory_request: false`.

---

### 0000252  —  **NOT A LAB REQUEST** (clinical_abstract)

`(no template)` · `photocopy_gen1` · `medium`

`media/0000252_photocopy_gen1.png`

Expected: empty set, and `is_laboratory_request: false`.

---

### 0000253  —  **NOT A LAB REQUEST** (medical_certificate)

`(no template)` · `photocopy_gen3` · `hard`

`media/0000253_photocopy_gen3.png`

Expected: empty set, and `is_laboratory_request: false`.

---

### 0000254  —  **NOT A LAB REQUEST** (referral_letter)

`(no template)` · `fax` · `hard`

`media/0000254_fax.png`

Expected: empty set, and `is_laboratory_request: false`.

---

### 0000255  —  **NOT A LAB REQUEST** (consent_form)

`(no template)` · `clean` · `easy`

`media/0000255_clean.png`

Expected: empty set, and `is_laboratory_request: false`.

---

### 0000256  —  **NOT A LAB REQUEST** (clinic_notice)

`(no template)` · `scan` · `easy`

`media/0000256_scan.png`

Expected: empty set, and `is_laboratory_request: false`.

---

### 0000257  —  **NOT A LAB REQUEST** (lab_result_report)

`(no template)` · `photocopy_gen1` · `medium`

`media/0000257_photocopy_gen1.png`

Expected: empty set, and `is_laboratory_request: false`.

---

### 0000258  —  **NOT A LAB REQUEST** (prescription)

`(no template)` · `photocopy_gen3` · `hard`

`media/0000258_photocopy_gen3.png`

Expected: empty set, and `is_laboratory_request: false`.

---

### 0000259  —  **NOT A LAB REQUEST** (clinical_abstract)

`(no template)` · `fax` · `hard`

`media/0000259_fax.png`

Expected: empty set, and `is_laboratory_request: false`.

---
