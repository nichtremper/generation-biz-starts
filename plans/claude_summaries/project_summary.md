# Project Summary — Generation Business Starts
Last updated: 2026-04-14

## Research question
Are people 35 and younger starting businesses at higher rates than historical averages?

## Answer
**No.** Young adults (20–35) are not starting businesses at elevated rates relative to their own history. The more striking finding is structural: the 20–35 group enters self-employment at roughly **40% lower rates** than 36–64-year-olds — a gap that has held across the entire 2005–2025 series and shows no sign of narrowing.

---

## Data and methodology

**Source:** IPUMS CPS monthly microdata, pulled via the IPUMS API. Extract covers:
- Baseline: January 2005 – December 2019
- COVID era: January 2020 – December 2022 (analyzed separately, never folded into baseline)
- Recent: October 2023 – December 2025

**Total records:** 31,282,660 person-month observations across 63 chunks.

**Two parallel matching methods**, following the Kauffman Foundation New Entrepreneur Rate methodology:

| Method | Logic | Pairs produced | Best for |
|---|---|---|---|
| MOM (month-over-month) | Match consecutive MISH values (1→2, 2→3, 3→4, 5→6, 6→7, 7→8) | 20,728,136 | Rapid/gig entry, high volatility |
| YOY (year-over-year) | Match MISH=4 to MISH=8 (~12 months later) | 2,174,658 | Durable formation, lower volatility |

**Entry rate formula:** `(# not-SE at T0 who are SE at T1) / (# not-SE at T0)`, weighted by `WTFINL` (MOM) or `LNKFW1YWT` (YOY, with fallback to `WTFINL`).

**Two SE tracks reported in parallel:**
- Combined: CLASSWKR 13 (incorporated) or 14 (unincorporated)
- Incorporated only: CLASSWKR 13

**Age groups:** 20–35, 36–50, 51–64 (Kauffman working-age convention).

---

## Key results

### Recent period (Oct 2023–present) — average entry rates

**Month-over-month (3-month rolling average)**
| Age group | Combined SE | Incorporated only |
|---|---|---|
| 20–35 | 0.54% / month | 0.46% / month |
| 36–50 | 0.75% / month | 0.62% / month |
| 51–64 | 0.74% / month | 0.59% / month |

**Year-over-year (quarterly)**
| Age group | Combined SE | Incorporated only |
|---|---|---|
| 20–35 | 2.1% / year | 1.8% / year |
| 36–50 | 3.0% / year | 2.6% / year |
| 51–64 | 2.9% / year | 2.6% / year |

### Time series observations

- **No recent elevation for 20–35.** Post-Oct 2023 rates are near or slightly below the 2005–2019 historical range in both methods. MOM shows scattered above-baseline months (mostly February and summer) consistent with seasonality, not a structural shift. YOY flags only one above-baseline quarter (2025 Q1, z=1.3).
- **COVID spike reversed.** All groups show elevated rates in 2020–2022, most visibly in 36–50 and 51–64. Post-2022 rates returned to pre-COVID levels.
- **Secular post-GFC decline.** A gradual downward drift in entry rates is visible from 2006 to ~2013 across older groups, consistent with Kauffman's documented post-financial crisis entrepreneurship decline. Rates stabilized after 2014.
- **MOM/YOY divergence.** Several periods where MOM exceeds baseline but YOY does not. Per Kauffman methodology, this signals attempted but abandoned self-employment rather than durable formation.

### Confidence intervals
Median n_at_risk per month per age group: ~15–17k (MOM). Median 95% CI width: ±0.11%. Statistical uncertainty is workable; the structural age-group gap is well outside the confidence bands.

---

## Pipeline

Scripts run in order:

```bash
python scripts/01_extract.py   # Pull CPS data from IPUMS API
python scripts/02_match.py     # Build MOM and YOY matched person pairs
python scripts/03_classify.py  # Code SE transitions for each pair
python scripts/04_analysis.py  # Compute entry rates, flag vs. baseline
python scripts/05_visualize.py # Time-series charts with 95% CI shading
```

**Outputs:**
| File | Description |
|---|---|
| `data/raw/` | IPUMS fixed-width extract + DDI (gitignored) |
| `data/raw/chunks/` | Parquet chunk cache for memory-safe processing (gitignored) |
| `data/processed/matched_mom.parquet` | 20.7M MOM pairs with transition labels |
| `data/processed/matched_yoy.parquet` | 2.2M YOY pairs with transition labels |
| `data/processed/rates_mom.parquet` | Monthly entry rates by age group |
| `data/processed/rates_yoy.parquet` | Quarterly entry rates by age group |
| `data/processed/recent_vs_baseline_*.parquet` | Recent period flagged vs. baseline |
| `figures/entry_rates_mom.png` | MOM time series, all age groups, shared y-axis, 95% CI |
| `figures/entry_rates_yoy.png` | YOY time series, all age groups, shared y-axis, 95% CI |

---

## Bugs found and fixed

| Bug | File | Impact |
|---|---|---|
| `read_microdata` doesn't support `chunksize` — returned full DataFrame, iteration over it yielded column name strings, `pl.from_pandas` crashed | `scripts/02_match.py` | Script couldn't run at all |
| MISH coding: code used 13–16 for second rotation stint; IPUMS uses 5–8 | `src/match.py` | MOM missing ~half its pairs; YOY returned zero results |
| Age floor of 0 included infants in denominator, diluting entry rates | `src/rates.py` | Entry rates understated for all age groups |

---

## Known limitations and open items

1. **2024 Q1–Q3 missing from YOY.** The extract skips Jan–Sep 2023, so the T0 observations needed to produce those YOY pairs don't exist. A supplemental extract covering those 9 months would close the gap.
2. **March has no MOM baseline.** `compute_baseline_stats` returns NaN for March — worth investigating whether a data gap in the 2005–2019 March MOM pairs is causing it.
3. **MOM understates unincorporated SE entry.** Short month-to-month links disproportionately capture stable incorporated workers. Unincorporated/gig SE has high turnover and often doesn't survive the link. YOY is the more reliable series for unincorporated SE trends.
4. **CI method is approximate.** Uses unweighted `n_at_risk` as effective sample size. Does not correct for CPS survey design effects (typical DEFF ~1.5). Bands are indicative, not formal.
