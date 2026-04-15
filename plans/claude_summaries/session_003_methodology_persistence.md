# Session 3 — Methodology Alignment, Kauffman Comparison, Persistence Rates
Date: 2026-04-15

---

## Methodology changes this session

### Age brackets — now match Kauffman exactly
Previous brackets (20–35, 36–50, 51–64) replaced with Kauffman standard:

| Key | Range | Notes |
|---|---|---|
| `20_to_34` | 20–34 | Primary research group; matches Kauffman "young adult" |
| `35_to_44` | 35–44 | Kauffman bracket |
| `45_to_54` | 45–54 | Kauffman bracket |
| `55_to_64` | 55–64 | Kauffman bracket |
| `20_to_64` | 20–64 | All-age aggregate; direct comparison to published Kauffman overall rate |

### Hours worked filter (Kauffman comparability)
Added `UHRSWORKT` to the IPUMS extract. `classify.py` now applies Kauffman's ≥15 usual hours/week filter at T1 to define SE status. Where `UHRSWORKT_t1` is NaN (samples where the variable wasn't collected), falls back to CLASSWKR alone.

### Allocation flag exclusion — not implementable
Kauffman drops observations where CLASSWKR, EMPSTAT, or hours worked were imputed. IPUMS CPS allocation flags (`QCLASSWK`, `QEMPSTAT`, `QUHRSWORKT`) are not available via the extract API for our sample period (coverage ends ~2010). Documented as an unresolved methodological gap in `src/classify.py`.

### `new_entrant_inc_strict` added
`src/classify.py` now produces two incorporated SE entry measures:
- `new_entrant_inc`: not incorporated at T0 → incorporated at T1 (includes uninc→inc restructuring)
- `new_entrant_inc_strict`: not SE at all at T0 → incorporated at T1 (pure new formation)

### CI design-effect correction
`scripts/05_visualize.py` now applies `DESIGN_EFFECT = 1.5` scalar to CI bands: `se = sqrt(1.5 * p*(1-p)/n)`. CPS clustered sampling typically produces DEFF 1.5–2.0; this is a conservative approximation since PSU/stratum variables are not in the extract. Bands were previously 22–41% too narrow.

### Robustness baseline (2010–2019)
`src/rates.py` exports `BASELINE_YEARS_ROBUST = range(2010, 2020)`. `compute_baseline_stats` accepts a `baseline_years` parameter. `04_analysis.py` now runs both baselines and saves `*_robust.parquet` files alongside the main outputs.

### March NaN diagnostic
`compute_baseline_stats` now logs a warning for any seasonal bucket with fewer than 5 observations or a NaN mean. March MOM baseline remains NaN — root cause (genuine data sparsity vs. period-construction bug) still unresolved.

### Run pipeline shell script
`run_pipeline.sh` added at repo root. Supports `--from-step N` to skip completed stages:
```bash
./run_pipeline.sh              # full run
./run_pipeline.sh --from-step 4  # skip extract + match + classify
```
Step 1 (`01_extract.py`) also now retries automatically on connection timeouts and supports `--resume-id N` to attach to an already-submitted IPUMS extract without resubmitting.

---

## Kauffman comparison

### Where we match Kauffman
- Age brackets: 20–34, 35–44, 45–54, 55–64 ✓
- CPS data source, MOM matching ✓
- CLASSWKR to identify SE ✓
- Survey-weighted rates ✓
- ≥15 hours/week filter at T1 ✓ (post this session)

### Where we differ
| Issue | Kauffman | Us |
|---|---|---|
| Denominator | All non-SE adults (including unemployed/NILF) | Employed non-SE only (EMPSTAT 10/12) |
| Allocation exclusion | Drops imputed CLASSWKR/EMPSTAT/hours obs | Not possible — flags unavailable for our sample period |
| YOY track | MOM only | We add YOY (MISH 4→8) for durable formation |

### Level comparison
Fairlie 2023 (the post-Kauffman continuation series) reports an overall (ages 20–64) monthly rate of **0.35%** in 2023. Our 20–64 all-age MOM rate in the recent period averages **~0.42%**. The ~20% higher level is consistent with our employed-only denominator being smaller than Kauffman's all-adult denominator.

### What Fairlie 2023 does and doesn't report
The Fairlie 2023 paper (UCLA, January 2024) is the most current source extending the Kauffman series. It reports trends by sex, race/ethnicity, and nativity through 2023 but **does not include age-specific breakdowns**. The last published age-specific rates are from the 2021 Kauffman national report. Direct point-in-time comparison of our 20–34 rate to a published 20–34 Kauffman rate is not possible for 2023–2025.

---

## New analysis: SE persistence rates

### Motivation
Employment (CE16OV, FRED) was essentially flat YOY in mid-2024 (Jul–Oct 2024: +0.03–0.15% YOY) but elevated in absolute business formation counts (BFS/EIN applications). If employment is flat and more businesses are starting, the entry *rate* should rise — but our YOY series shows no elevation. Hypothesis: maybe the SE stock is growing because people are *staying* SE longer, not because more are entering.

### Method
New functions in `src/rates.py`:
- `compute_mom_persistence_rates`: fraction of SE workers at T0 still SE at T1 (1-month survival)
- `compute_yoy_persistence_rates`: fraction of SE workers at MISH=4 still SE at MISH=8 (~12-month survival)

Formula: `Σ(weight × continuing) / Σ(weight × se_t0)` — uses `_entry_rate` with `continuing` as numerator and `se_t0` as denominator column.

Both functions compute combined SE and incorporated-only persistence. Output saved to `data/processed/persistence_mom.parquet` and `data/processed/persistence_yoy.parquet`.

New figures: `figures/persistence_rates_mom.png`, `figures/persistence_rates_yoy.png`.

### Results

**YOY 12-month persistence rate — all age 20–64 recent period**
| Quarter | Persistence | Baseline | Z-score |
|---|---|---|---|
| 2023Q4 | 66.1% | 68.4% | -1.37 |
| 2024Q4 | 63.9% | 68.4% | -2.68 |
| 2025Q1 | 67.9% | 67.9% | ~0 |
| 2025Q2 | 64.6% | 68.9% | -1.96 |
| 2025Q3 | 68.2% | 67.8% | ~0 |
| 2025Q4 | 69.1% | 68.4% | +0.43 |

**YOY 12-month persistence rate — age 20–34 recent period**
| Quarter | Persistence | Baseline | Z-score |
|---|---|---|---|
| 2023Q4 | 59.7% | 55.6% | +1.09 |
| 2024Q4 | 49.8% | 55.6% | -1.53 |
| 2025Q1 | 49.5% | 58.2% | -1.88 |
| 2025Q2 | 47.0% | 58.0% | -2.07 |
| 2025Q3 | 55.8% | 55.3% | ~0 |
| 2025Q4 | 57.8% | 55.6% | +0.58 |

**Hypothesis is falsified.** Persistence in 2024–early 2025 was *below* baseline — SE workers were churning out faster than historical norms, not staying longer. The "staying longer" explanation for the elevated SE stock does not hold.

---

## Updated entry rate results

### Recent period average entry rates (Oct 2023 – present)

**Month-over-month (3-month rolling)**
| Age group | Combined SE | Incorporated only |
|---|---|---|
| 20–34 | 0.34% / month | 0.29% / month |
| 35–44 | 0.45% / month | 0.40% / month |
| 45–54 | 0.47% / month | 0.42% / month |
| 55–64 | 0.45% / month | 0.40% / month |
| 20–64 (all) | 0.42% / month | 0.36% / month |

**Year-over-year (quarterly)**
| Age group | Combined SE | Incorporated only |
|---|---|---|
| 20–34 | 2.0% / year | 1.7% / year |
| 35–44 | 2.8% / year | 2.4% / year |
| 45–54 | 3.4% / year | 3.1% / year |
| 55–64 | 3.1% / year | 2.8% / year |
| 20–64 (all) | 2.7% / year | 2.5% / year |

### Revised answer to research question

**No.** YOY rates for 20–34 are essentially at their 2005–2019 historical average — z-scores near zero across all recent quarters. The post-pandemic entrepreneurship bump documented by Kauffman for the overall adult population does not appear to be concentrated in the 20–34 age group. Older groups (35–54) show similarly flat YOY rates.

The MOM series shows sporadic above-baseline months (particularly Feb and summer/fall 2024, and scattered 2025 months) but no sustained elevation. The MOM/YOY divergence — elevated MOM entry without corresponding YOY confirmation — is consistent with increased *attempted* SE that is not surviving 12 months, rather than durable business formation.

### The BFS vs. CPS discrepancy
Census Bureau BFS (EIN applications, high-propensity applications) remain elevated relative to pre-pandemic. This is not inconsistent with our findings: BFS captures legal entity formations including LLCs formed by people who remain wage-employed. CPS measures only *primary employment transitions* into SE. A person forming an LLC while keeping their W-2 would not appear in our measure at all.

### FRED employment context
CE16OV was flat YOY in mid-2024 (Jul–Oct: ~0% YOY), then grew ~1.2–1.8% in 2025, and has gone slightly negative in early 2026 (-0.3 to -0.6% YOY). The flat-employment period in mid-2024 coincides with the above-baseline MOM months (Oct 2024 z=3.79 was the strongest single month), consistent with the user's hypothesis that a flat denominator should amplify the rate — but this effect was transient, not structural.

---

## Updated pipeline outputs

| File | Description |
|---|---|
| `data/processed/persistence_mom.parquet` | Monthly 1-month SE persistence rates by age group |
| `data/processed/persistence_yoy.parquet` | Quarterly 12-month SE persistence rates by age group |
| `data/processed/recent_vs_baseline_persistence_*.parquet` | Recent persistence vs. baseline, flagged |
| `data/processed/recent_vs_baseline_*_robust.parquet` | Same using 2010–2019 robustness baseline |
| `figures/persistence_rates_mom.png` | MOM persistence time series, all age groups |
| `figures/persistence_rates_yoy.png` | YOY persistence time series, all age groups |

---

## Open items

1. **March MOM baseline NaN** — diagnostic logging now in place; root cause (genuine data sparsity vs. period-construction bug) unresolved.
2. **2024 Q1–Q3 missing from YOY** — extract skips Jan–Sep 2023 T0 observations. Still unresolved from session 2.
3. **Allocation flag exclusion** — not implementable with available IPUMS variables.
4. **BFS vs. CPS discrepancy** — worth investigating whether the elevated EIN applications are concentrated in incorporated side-ventures (LLC formations by wage employees), which would explain why they don't show up in CPS SE transitions.
