# Project Summary — Generation Business Starts
Last updated: 2026-04-15

## Research question
Are people 35 and younger starting businesses at higher rates than historical averages?

## Answer
**No.** Young adults (20–34) are not starting businesses at elevated rates relative to their own history. The YOY series (the more reliable indicator of durable formation) shows 20–34 rates tracking at or slightly below the 2005–2019 historical baseline across all recent quarters. The post-pandemic entrepreneurship bump documented by Kauffman for the overall adult population does not appear to be concentrated in the youngest age group, nor in any specific older group either — the YOY series is flat across all age brackets.

The MOM series shows sporadic above-baseline months but no sustained elevation. The MOM/YOY divergence is consistent with increased *attempted* SE that doesn't survive 12 months, not durable formation.

SE persistence (12-month survival rate) was *below* baseline in 2024Q4–2025Q2, ruling out the alternative explanation that the SE stock is growing because people are staying SE longer.

---

## Data and methodology

**Source:** IPUMS CPS monthly microdata, pulled via the IPUMS API. Extract covers:
- Baseline: January 2005 – December 2019
- COVID era: January 2020 – December 2022 (analyzed separately, never folded into baseline)
- Recent: October 2023 – present (through ~late 2025)

**Two parallel matching methods**, following the Kauffman Foundation New Entrepreneur Rate methodology:

| Method | Logic | Pairs produced | Best for |
|---|---|---|---|
| MOM (month-over-month) | Match consecutive MISH values (1→2, 2→3, 3→4, 5→6, 6→7, 7→8) | ~20.7M | Rapid/gig entry, high volatility |
| YOY (year-over-year) | Match MISH=4 to MISH=8 (~12 months later) | ~2.2M | Durable formation, lower volatility |

**Entry rate formula:** `(# not-SE at T0 who are SE at T1) / (# not-SE at T0)`, weighted by `WTFINL` (MOM) or `LNKFW1YWT` (YOY, with fallback to `WTFINL`).

**Persistence rate formula:** `(# SE at T0 still SE at T1) / (# SE at T0)`, same weights.

**Denominator convention (Kauffman):** Restricted to *employed* non-SE at T0 (EMPSTAT 10 or 12). Excludes unemployed and NILF. Note: Kauffman's published denominator is described as "all non-business-owner adults" — this is an unresolved methodological ambiguity that inflates our rates slightly relative to published Kauffman figures.

**SE definition:** CLASSWKR 13 (incorporated) or 14 (unincorporated). T1 SE status requires UHRSWORKT ≥ 15 hrs/week (Kauffman convention), falling back to CLASSWKR alone where UHRSWORKT is unavailable.

**Two SE tracks reported in parallel:**
- Combined: CLASSWKR 13 or 14
- Incorporated only: CLASSWKR 13

**Age groups (Kauffman standard):**
| Key | Range |
|---|---|
| `20_to_34` | Primary research group |
| `35_to_44` | Comparison |
| `45_to_54` | Comparison |
| `55_to_64` | Comparison |
| `20_to_64` | All-age aggregate; matches published Kauffman overall rate |

---

## Key results

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

Our all-age rate (~0.42%/month MOM) is modestly above Kauffman's published 0.35% for 2023, consistent with our smaller employed-only denominator.

### Time series observations

- **No recent elevation for 20–34.** Post-Oct 2023 YOY rates are near the 2005–2019 historical baseline. MOM shows scattered above-baseline months (Feb, summer/fall 2024, scattered 2025) but no structural shift.
- **No elevation for older groups either.** 35–44, 45–54, and 55–64 YOY series are similarly flat. The Kauffman-documented post-pandemic overall rate elevation does not appear in our YOY data for any age group.
- **COVID spike reversed.** All groups show elevated rates in 2020–2022. Post-2022 rates returned to pre-COVID levels.
- **Secular post-GFC decline.** Downward drift visible 2006–2013, stabilizing after 2014. The 2005–2019 baseline mean embeds this decline; a 2010–2019 robustness baseline is also computed and saved.
- **MOM/YOY divergence.** Persistent pattern where MOM exceeds baseline but YOY does not. Per Kauffman methodology, this signals attempted but abandoned SE rather than durable formation.
- **Persistence below baseline in 2024.** 12-month SE survival rate (YOY) was below the 2005–2019 baseline in 2024Q4 (z=−2.68 for 20–64) and 2025Q1–Q2. People are exiting SE faster than historical norms, not staying longer. This rules out a "growing SE stock via retention" explanation.

### Structural age gap
20–34 enters SE at roughly 25–40% lower rates than 35–64 year olds, a gap that has persisted across the full 2005–2025 series.

---

## Pipeline

Scripts run in order:
```bash
./run_pipeline.sh              # full run (may take hours for step 1)
./run_pipeline.sh --from-step N  # skip completed stages
```

Individual scripts:
```bash
python scripts/01_extract.py   # Pull CPS data from IPUMS API (supports --resume-id N)
python scripts/02_match.py     # Build MOM and YOY matched person pairs
python scripts/03_classify.py  # Code SE transitions for each pair
python scripts/04_analysis.py  # Compute entry + persistence rates, flag vs. baseline
python scripts/05_visualize.py # Time-series charts with 95% CI shading
```

**Outputs:**
| File | Description |
|---|---|
| `data/raw/` | IPUMS fixed-width extract + DDI (gitignored) |
| `data/raw/chunks/` | Parquet chunk cache for memory-safe processing (gitignored) |
| `data/processed/matched_mom.parquet` | ~20.7M MOM pairs with transition labels |
| `data/processed/matched_yoy.parquet` | ~2.2M YOY pairs with transition labels |
| `data/processed/rates_mom.parquet` | Monthly entry rates by age group |
| `data/processed/rates_yoy.parquet` | Quarterly entry rates by age group |
| `data/processed/persistence_mom.parquet` | Monthly 1-month SE persistence rates by age group |
| `data/processed/persistence_yoy.parquet` | Quarterly 12-month SE persistence rates by age group |
| `data/processed/recent_vs_baseline_*.parquet` | Recent period flagged vs. 2005–2019 baseline |
| `data/processed/recent_vs_baseline_*_robust.parquet` | Same using 2010–2019 robustness baseline |
| `figures/entry_rates_mom.png` | MOM entry rate time series, all age groups |
| `figures/entry_rates_yoy.png` | YOY entry rate time series, all age groups |
| `figures/persistence_rates_mom.png` | MOM 1-month persistence time series |
| `figures/persistence_rates_yoy.png` | YOY 12-month persistence time series |

---

## Kauffman comparability

| Dimension | Kauffman | This project |
|---|---|---|
| Age brackets | 20–34, 35–44, 45–54, 55–64 | ✓ Same |
| Hours filter | ≥15 hrs/week at T1 | ✓ Applied (where UHRSWORKT available) |
| Allocation exclusion | Drops imputed obs | ✗ IPUMS flags unavailable post-2010 |
| Denominator | All non-SE adults (ambiguous) | Employed non-SE only |
| YOY track | MOM only | Extended with MISH 4→8 YOY |

---

## Known limitations and open items

1. **2024 Q1–Q3 missing from YOY.** Extract skips Jan–Sep 2023, so T0 observations for those YOY pairs don't exist. A supplemental extract would close the gap.
2. **March has no MOM baseline.** NaN baseline_mean for March in both 2024 and 2025 output. Diagnostic logging now in place; root cause unresolved.
3. **Allocation flag exclusion not implementable.** IPUMS doesn't expose quality flags for our sample period. Minor methodology gap vs. Kauffman.
4. **BFS vs. CPS discrepancy unresolved.** Census BFS (EIN applications) remains elevated relative to pre-pandemic while our CPS SE transition rates are flat. Likely explained by LLC formations among wage-employed people (side ventures) that don't appear as CPS employment transitions.
5. **CI method is approximate.** DESIGN_EFFECT=1.5 scalar applied; PSU/stratum variables not extracted so exact DEFF correction is not possible.
