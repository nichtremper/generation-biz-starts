# Robustness Check Findings

**Branch:** `robustness-checks`  
**Run date:** 2026-04-16  
**Scripts:** `scripts/robustness/01–10_*.py`  
**Figures:** `figures/robustness/`

All checks use `data/processed/` parquets built from the same matched-pair
pipeline. For each check, the verdict indicates whether the main conclusions
in `index.html` survive.

---

## Check 01 — Baseline Period Sensitivity
**Figures:** `01_baseline_sensitivity_yoy.png`, `01_baseline_sensitivity_stock.png`

| Baseline window | 20–34 YOY mean entry rate |
|-----------------|--------------------------|
| 2005–2019 (canonical) | 1.996% |
| 2010–2019 | 1.916% |
| 2015–2019 | 1.993% |
| 2016–2019 (pre-COVID) | 2.019% |

All four windows give nearly identical means (range: 0.10pp). The SE stock
baseline is similarly stable across windows.

**Verdict:** No material sensitivity. The "at historical norms" characterization
of YOY entry rates holds regardless of baseline choice. The "above 2016–2019
baseline" stock claim holds under all windows.

---

## Check 02 — Design Effect (DEFF) Sensitivity
**Figure:** `02_deff_sensitivity.png`

Most recent quarter (2025Q4), 20–34 YOY entry rate = 1.82%, n_at_risk = 1,566:

| DEFF | 95% CI half-width | CI range |
|------|-------------------|----------|
| 1.0 (no correction) | ±0.66 pp | [1.15%, 2.48%] |
| 1.5 (canonical) | ±0.81 pp | [1.00%, 2.63%] |
| 2.0 | ±0.94 pp | [0.88%, 2.75%] |
| 2.5 | ±1.05 pp | [0.77%, 2.86%] |

The CI lower bound stays well above zero under all DEFF values. Going from 1.5
to 2.5 widens the CI by ~29%.

**Verdict:** Point estimates are unaffected. Precision claims ("rates near
historical norms") are appropriately hedged by the already-shown CI bands.
A more conservative DEFF weakens any "significantly above baseline" language
but doesn't change the trend narrative.

---

## Check 03 — Age Cutoff Sensitivity
**Figure:** `03_age_cutoff_sensitivity.png`

Recent period YOY entry rate vs. own 2005–2019 baseline mean:

| Age cutoff | Mean rate | vs. own baseline |
|------------|-----------|-----------------|
| 20–29 | 1.815% | **+6.8%** |
| 20–34 (canonical) | 1.950% | −2.0% |
| 20–39 | 2.146% | −4.4% |
| 18–34 | 1.884% | −1.3% |

The canonical 20–34 cutoff is near or slightly below its own baseline. The
20–29 sub-cohort (Gen Z) shows a meaningfully elevated entry rate. Including
35–39 (peak career-building years) pulls the rate above baseline in levels but
further below baseline in indexed terms.

**Verdict:** The "broadly at historical norms" characterization for 20–34 is
correct. The more specific finding — Gen Z (20–29) is the elevated sub-cohort —
strengthens the narrative about young adults forming businesses at higher rates;
it just sharpens the age range. Added to index.html.

---

## Check 04 — Hours Worked Filter (Documentation Only)
**Figure:** `04_hours_filter_audit.png`

UHRSWORKT is absent from the raw CPS chunks. The Kauffman ≥15 hrs/week filter
cannot be applied. Our 20–64 YOY entry rate visually tracks above the
approximate Kauffman published NER values (the gap reflects the hours filter
plus methodological differences).

**Verdict:** All flow rates in the report are overstated relative to Kauffman's
published figures by an unknown amount (likely small for incorporated SE, larger
for unincorporated SE). Caveat added to Figure 4 caption and methodology card.
**Action required:** Re-submit IPUMS extract with UHRSWORKT to enable direct
Kauffman comparison.

---

## Check 05 — Incorporated SE Definition (Broad vs. Strict)
**Figure:** `05_inc_definition.png`

Restructurings (unincorporated→incorporated switches) as share of "broad"
incorporated new entrants, 20–34, recent period:

- Mean restructure rate: **0.043%** of the at-risk population
- As % of the broad incorporated entry rate: **15.0%**

The gap between broad and strict definitions is visible in both MOM and YOY
series. The strict rate (now the default in `src/rates.py`) is about 85% of
the broad rate.

**Verdict:** The fix reduces the "Incorporated SE only" line in the main figures
by ~15%. No headline conclusions change (the main claims use combined SE or YOY
entry rates, not the incorporated-only rate). The strict definition is now
the correct measure for any claim about new incorporated business formation
specifically.

---

## Check 06 — Gender Decomposition
**Figure:** `06_gender_decomp.png`

Recent period (2023Q4+) YOY entry rate vs. gender-specific 2005–2019 baseline:

| Gender | Mean rate | vs. own baseline |
|--------|-----------|-----------------|
| Male | 2.355% | −3.3% |
| Female | 1.498% | −0.0% |

Both genders are near their own historical baselines. Female entry is
essentially at the mean; male entry is slightly below. No gender shows a
dramatic spike.

**Verdict:** The aggregate finding is not driven by one gender. Both are at
or near their baselines, consistent with the "at historical norms" conclusion
for YOY entry rates.

---

## Check 07 — COVID Exclusion Window
**Figure:** `07_covid_window.png`

Mean z-score for 20–34 YOY entry rate in the recent period (2023Q4+) under
four COVID exclusion definitions:

| Window | Mean z-score | Quarters above 1 SD |
|--------|-------------|---------------------|
| No exclusion (2005–present baseline) | −0.13 | 0/6 |
| Exclude 2020–2021 | −0.13 | 0/6 |
| Exclude 2020–2022 (canonical) | −0.13 | 0/6 |
| Exclude 2020–2023 | −0.13 | 0/6 |

The mean z-score is identically −0.13 across all windows, and 0 of 6 recent
quarters exceed any threshold under any definition.

**Verdict:** The "durable formation rates at historical norms" conclusion is
the most robust finding in the analysis. It is completely insensitive to how
the COVID exclusion window is defined.

---

## Check 08 — March Data Gap
**Figure:** `08_march_gap.png`

20 of 21 years in the dataset have a March data gap (zero SE observations in
March). Annual averages exclude these months in the canonical treatment.

| Treatment | Max difference from canonical |
|-----------|------------------------------|
| Linear interpolation (Feb/Apr midpoint) | 0.0304 pp |
| Carry-forward (February value) | 0.0440 pp |

The largest possible difference from treating March gaps differently is
<0.05 pp — well within noise.

**Verdict:** Negligible. The March exclusion treatment does not meaningfully
affect annual stock averages.

---

## Check 09 — Autocorrelation-Corrected Inference
**Figure:** `09_autocorrelation.png`

Baseline (2005–2019) AR(1) autocorrelation and Newey-West correction:

| Age group | Mean AR(1) ρ̂ | Mean NW inflation factor | Recent quarters above 1 SD (naive) | Recent quarters above 1 SD (NW) |
|-----------|--------------|--------------------------|------------------------------------|---------------------------------|
| 20–34 | 0.239 | 1.130× | 0/6 | 0/6 |
| 20–64 | 0.037 | 0.986× | 2/6 | 2/6 |

For 20–34, the quarterly YOY series has meaningful autocorrelation (ρ̂ = 0.24).
The NW correction inflates the effective SD by 13%. Under both naive and
NW-corrected z-scores, **zero of six recent quarters are above any threshold**
for the 20–34 group.

NW-corrected z-scores are now the default in `src/rates.py`
(`above_baseline_nw` column). The `baseline_nw_sd` is used as the denominator
(wider than naive SD, giving more conservative z-scores).

**Verdict:** Autocorrelation correction slightly weakens z-scores but changes
no flags. The "at historical norms" conclusion is robust to autocorrelation
correction.

---

## Check 10 — CPS 2014 Redesign Structural Break
**Figure:** `10_cps_redesign.png`

Welch t-test for difference in means between 2005–2013 and 2014–2019:

| Series | Pre-2014 mean | Post-2014 mean | Difference | t-stat | p-value |
|--------|--------------|----------------|------------|--------|---------|
| YOY entry rate (20–34) | 2.033% | 1.947% | −0.085 pp | 0.94 | **0.348** |
| SE stock share (20–34) | 5.27% | 4.76% | −0.513 pp | 10.16 | **< 0.001** |

The entry rate shows **no statistically significant break** at 2014 — flow
measures are unaffected by the redesign. The stock share shows a **highly
significant break**, but the direction (higher pre-2014) and the timing (the
2005–2013 window includes the Great Recession and its elevated necessity SE)
suggest this reflects genuine economic change rather than a pure measurement
artifact.

**Implication:** Comparisons of current YOY entry rates to pre-2014 historical
norms are valid. Comparisons of current SE stock levels to early-2000s peaks
should be qualified: they span the redesign *and* the Great Recession, making
the pre-2014 stock mean a mixed baseline. Within-redesign-era comparisons
(2014–present vs. 2016–2019 baseline) are fully apples-to-apples.

Caveat added to `index.html` stock section.

---

## Overall Robustness Assessment

| Finding | Robustness |
|---------|-----------|
| All cohorts above 2016–2019 SE stock baseline | **High** — holds across all baseline windows, unaffected by March treatment or DEFF |
| 20–34 SE stock near long-run 2005–2019 mean | **Moderate** — qualifications needed for pre-2014 comparisons (see Check 10); the 2016–2019 relative claim is robust |
| YOY durable entry rates at historical norms | **Very high** — z = −0.13 under all COVID windows, 0/6 recent quarters above any threshold, autocorrelation correction changes nothing |
| Opportunity (not necessity) mechanism for 20–34 | **Moderate** — directionally supported; employment→SE elevated; but caution warranted given noisy unemployment pathway and YOY rates at norms |
| Gen Z (20–29) as primary driver of elevated signal | **Moderate** — new finding from Check 03; YOY +6.8% above baseline vs. −2.0% for canonical 20–34 |
| Incorporated rate (strict definition) | **Fixed** — restructurings were 15% of the broad incorporated rate; strict definition now default |
