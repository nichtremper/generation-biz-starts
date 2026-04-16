# Robustness Check Plan

**Branch:** `robustness-checks`  
**Data:** IPUMS CPS matched pairs (MOM and YOY), `data/processed/`  
**Output directory:** `figures/robustness/`

---

## Overview

Ten checks cover the five main categories of analytical risk in this project:
baseline choice, statistical precision, sample definition, data quality, and
time-series inference. Checks are ordered roughly by severity of potential impact.

---

## Check 01 — Baseline Period Sensitivity
**Script:** `scripts/robustness/01_baseline_sensitivity.py`  
**Risk level:** High  
**Motivation:** The canonical baseline (2005–2019) includes the post-dot-com
decline years, which pull the long-run mean down. A tighter baseline (2016–2019)
makes the post-COVID recovery look more dramatic; excluding the Great Recession
(2010–2019 baseline) moderates it slightly.  
**Method:** Compute seasonal mean baselines under four windows: 2005–2019,
2010–2019, 2015–2019, 2016–2019. Show as step-function horizontal reference
lines for both the YOY entry rate series and the SE stock share.  
**Expected finding:** The claim that 20–34 SE share has "returned to the long-run
mean" is sensitive to which long-run mean you pick. Under the 2016–2019 baseline
the recovery looks more pronounced; under 2005–2019 less so.  
**Outputs:** `01_baseline_sensitivity_yoy.png`, `01_baseline_sensitivity_stock.png`

---

## Check 02 — Design Effect (DEFF) Sensitivity
**Script:** `scripts/robustness/02_deff_sensitivity.py`  
**Risk level:** Moderate  
**Motivation:** The canonical CI uses DEFF = 1.5. CPS documentation suggests
DEFF ranges from 1.5 to 2.0 for employment variables; SE status likely runs
higher. A scalar DEFF is a rough approximation. CIs widen by ~29% going from
DEFF 1.5 to 2.5.  
**Method:** Test DEFF ∈ {1.0, 1.5, 2.0, 2.5}. Show CI bands on full YOY series
and bar chart of CI half-width per recent quarter.  
**Expected finding:** Flow rate CIs are already wide relative to the signal;
higher DEFF further weakens precision claims without changing the point estimates.  
**Outputs:** `02_deff_sensitivity.png`

---

## Check 03 — Age Cutoff Sensitivity
**Script:** `scripts/robustness/03_age_cutoff_sensitivity.py`  
**Risk level:** Moderate  
**Motivation:** The 20–34 cutoff follows Kauffman exactly. The 35–39 group is
prime business-formation age; including them could dilute or amplify the signal.
The 20–29 cut isolates Gen Z from older millennials.  
**Method:** Recompute YOY entry rates for four age definitions: 20–29, 20–34
(canonical), 20–39, 18–34. Plot both raw rates and rates indexed to their own
2005–2019 baselines so level differences don't confound trend comparison.  
**Expected finding:** The indexed comparison removes level effects. If the
finding holds across all cutoffs, it is not an artifact of the 34-year boundary.  
**Outputs:** `03_age_cutoff_sensitivity.png`

---

## Check 04 — Hours Worked Filter (Documentation)
**Script:** `scripts/robustness/04_hours_filter.py`  
**Risk level:** Moderate (documentation only — filter cannot be applied)  
**Motivation:** Kauffman's NER requires SE at T1 to work ≥15 hrs/week
(UHRSWORKT ≥ 15). UHRSWORKT is absent from the raw CPS chunks despite being
listed in the extract request. Our rates include all SE workers regardless of
hours, overstating SE participation relative to Kauffman — especially for
unincorporated SE (more marginal/gig work).  
**Method:** (1) Audit raw chunks to confirm UHRSWORKT is missing. (2) Compare
our 20–64 YOY entry rate to Kauffman's published NER for years where both exist.
Gap = combined effect of hours filter + methodological differences.  
**Action required:** Re-submit IPUMS extract with UHRSWORKT explicitly requested.
Until then, label estimates "without hours-worked filter."  
**Outputs:** `04_hours_filter_audit.png`

---

## Check 05 — Incorporated SE Definition (Broad vs. Strict)
**Script:** `scripts/robustness/05_inc_definition.py`  
**Risk level:** High (for incorporated entry rate specifically)  
**Motivation:** The canonical `new_entrant_inc` uses `~se_inc_t0 & se_inc_t1`,
which includes unincorporated→incorporated restructurings (existing SE owners
formalizing their business). These are legal status changes, not new businesses.
The strict definition (`~se_t0 & se_inc_t1`) excludes them. Post-COVID, many
sole proprietors incorporated for liability and tax reasons — this could
significantly overstate incorporated new business formation.  
**Method:** Compare broad vs. strict definitions on both MOM and YOY series for
20–34 and 20–64. Show the restructuring component as a filled area gap.  
**Expected finding:** If restructurings are a large fraction of "new entrants,"
the canonical rate overstates new incorporated formation. The strict definition
is the more valid measure for claims about new business creation.  
**Outputs:** `05_inc_definition.png`

---

## Check 06 — Gender Decomposition
**Script:** `scripts/robustness/06_gender_decomp.py`  
**Risk level:** Moderate  
**Motivation:** If the recent SE elevation is concentrated in one gender, the
aggregate signal may mask opposite-direction changes in the other. Halving the
sample also doubles SE on rates (~√2 wider CIs).  
**Method:** Recompute MOM and YOY entry rates separately by SEX_t0 (1=male,
2=female) for the 20–34 age group. Compare to gender-specific 2005–2019 seasonal
means.  
**Expected finding:** If both genders show elevation, the headline is robust.
If only one gender drives the result, the claim needs to be qualified.  
**Outputs:** `06_gender_decomp.png`

---

## Check 07 — COVID Exclusion Window
**Script:** `scripts/robustness/07_covid_window.py`  
**Risk level:** Moderate  
**Motivation:** The canonical baseline excludes 2020–2022 from the reference
period. But the "right" COVID window is a judgment call. A broader exclusion
(2020–2023) changes which quarters are "unusual" because it removes more of the
post-COVID elevated period from the baseline.  
**Method:** Test four COVID exclusion windows: none, 2020–2021, 2020–2022
(canonical), 2020–2023. Show z-score time series and bar chart of recent-period
z-scores under each window.  
**Expected finding:** The choice of COVID window most strongly affects whether
2022–2023 quarters are "above baseline." Recent (2024–2025) quarters should be
robust to window choice.  
**Outputs:** `07_covid_window.png`

---

## Check 08 — March Data Gap
**Script:** `scripts/robustness/08_march_gap.py`  
**Risk level:** Low–Moderate  
**Motivation:** Some CPS years have zero SE observations for March (likely due
to ASEC supplement displacement of basic monthly sampling). Annual averages
currently exclude these months. Does treating them as missing (interpolation
or carry-forward) instead of simply excluding them change the annual averages?  
**Method:** Compare three treatments: (A) canonical exclude, (B) linear
interpolation from Feb/Apr, (C) carry-forward from February. Plot annual SE
share under all three and show the difference from canonical.  
**Expected finding:** Annual averages are unlikely to be sensitive to treatment
of a single month per year, but this confirms the assumption.  
**Outputs:** `08_march_gap.png`

---

## Check 09 — Autocorrelation-Corrected Inference
**Script:** `scripts/robustness/09_autocorrelation.py`  
**Risk level:** High (for precision claims)  
**Motivation:** The canonical z-scores treat historical entry rates as i.i.d.
observations. Quarterly time-series data exhibit positive autocorrelation, which
inflates test statistics. A Newey-West HAC correction deflates z-scores by a
factor proportional to the autocorrelation structure. Claims that recent quarters
are "significantly above baseline" may weaken after correction.  
**Method:** Estimate AR(1) coefficient for baseline rates (2005–2019). Apply
Newey-West variance correction with bandwidth L = floor(T^(1/3)). Recompute
z-scores. Compare which above-baseline flags survive. Implemented in pure numpy
(no scipy dependency).  
**Expected finding:** Positive autocorrelation in quarterly rates is likely ~0.3–0.6.
NW factor of 1.2–1.5× is typical, meaning z-scores shrink by ~15–30%. Claims
of "statistically above baseline" should be stated carefully.  
**Outputs:** `09_autocorrelation.png`

---

## Check 10 — CPS Redesign Structural Break (January 2014)
**Script:** `scripts/robustness/10_cps_redesign.py`  
**Risk level:** Moderate–High (for stock comparisons)  
**Motivation:** The CPS underwent a major questionnaire redesign in January 2014,
documented by BLS as inflating measured SE rates by approximately 0.3pp due to
question wording changes. If post-2014 levels are systematically higher by
measurement artifact, then:  
  (a) The 2005–2019 mixed baseline is pulled up, making recent comparisons conservative.  
  (b) Claims comparing recent levels to "2004 peaks" (pre-redesign) are not
      apples-to-apples.  
**Method:** Welch t-test for difference in means between 2005–2013 and 2014–2019
for both YOY entry rate and SE stock share. Compute separate baselines for each
sub-period and show how the recent period compares to each.  
**Expected finding:** A statistically significant break at 2014 would qualify any
long-run level comparisons spanning the redesign. Flow entry rates (transitions)
are likely less affected than stock levels.  
**Outputs:** `10_cps_redesign.png`

---

## Summary Risk Table

| Check | What it tests | Risk level | Impact if failed |
|-------|--------------|------------|-----------------|
| 01 | Baseline window | High | "Above baseline" finding partially baseline-dependent |
| 02 | DEFF / CI width | Moderate | Precision claims weaken |
| 03 | Age cutoff | Moderate | 20–34 result may be cutoff-specific |
| 04 | Hours filter | Moderate | All rates overstated vs. Kauffman; cannot fix without new extract |
| 05 | Inc definition | High | Incorporated entry rate overstates new formation |
| 06 | Gender decomp | Moderate | Headline driven by one gender |
| 07 | COVID window | Moderate | 2022–2023 above-baseline flags are window-dependent |
| 08 | March gap | Low | Annual averages unaffected |
| 09 | Autocorrelation | High | z-score claims overstate statistical confidence |
| 10 | CPS redesign | Moderate–High | Long-run level comparisons not apples-to-apples |
