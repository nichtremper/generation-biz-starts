# Session 2 — First Full Pipeline Run
Date: 2026-04-14

## Bugs fixed this session

- **`read_microdata` → `read_microdata_chunked`** (`02_match.py`): ipumspy silently returned a full DataFrame when `chunksize` was passed to `read_microdata`. Iterating over a DataFrame yields column name strings, so `pl.from_pandas(chunk)` blew up with a TypeError.
- **MISH coding** (`src/match.py`): Code assumed MISH 13–16 for the second rotation stint. IPUMS codes the second stint as 5–8. This left MOM missing ~half its pairs and YOY at zero.
  - MOM pairs before fix: 10,272,876 (first stint only)
  - MOM pairs after fix: 20,728,136 (both stints)
  - YOY pairs before fix: 0
  - YOY pairs after fix: 2,174,658
- **Age floor** (`src/rates.py`): `35_and_under` group spanned ages 0–35, including infants in the denominator. Fixed to 20–35. Upper cap on `51_plus` set to 64, matching Kauffman working-age convention.

---

## Results: Are ≤35-year-olds starting businesses at elevated rates?

**Short answer: No sustained above-baseline trend.**

Both methods show scattered above-baseline months, but no persistent elevation and the more reliable YOY series is nearly flat against baseline.

---

### Month-over-month (MOM) — age 20–35
*3-month rolling average entry rates. Baseline = 2005–2019 seasonal mean. Flag = z-score > 1.*

| Period | Entry rate (3mo avg) | Inc-only (3mo avg) | vs. baseline |
|---|---|---|---|
| Oct 2023 | 0.56% | 0.43% | — |
| Nov 2023 | 0.52% | 0.42% | — |
| Dec 2023 | 0.49% | 0.43% | — |
| Jan 2024 | 0.52% | 0.46% | — |
| **Feb 2024** | **0.58%** | **0.49%** | **above** (z=2.4) |
| Mar 2024 | 0.60% | 0.51% | no baseline¹ |
| Apr 2024 | 0.57% | 0.47% | — |
| May 2024 | 0.56% | 0.48% | — |
| Jun 2024 | 0.53% | 0.44% | — |
| **Jul 2024** | **0.56%** | **0.47%** | **above** (z=1.3) |
| Aug 2024 | 0.53% | 0.43% | — |
| Sep 2024 | 0.49% | 0.41% | below (z=−2.2) |
| **Oct 2024** | **0.48%** | **0.40%** | **above** (z=1.9) |
| Nov 2024 | 0.45% | 0.38% | — |
| Dec 2024 | 0.49% | 0.42% | — |
| Jan 2025 | 0.49% | 0.43% | — |
| **Feb 2025** | **0.56%** | **0.48%** | **above** (z=2.4) |
| Mar 2025 | 0.60% | 0.50% | no baseline¹ |
| **Apr 2025** | **0.62%** | **0.52%** | **above** (z=1.2) |
| May 2025 | 0.50% | 0.43% | below (z=−2.2) |
| **Jun 2025** | **0.54%** | **0.47%** | **above** (z=2.0) |
| **Jul 2025** | **0.53%** | **0.47%** | **above** (z=1.1) |
| **Aug 2025** | **0.60%** | **0.54%** | **above** (z=1.5) |
| **Nov 2025** | **0.58%** | **0.51%** | **above** (z=1.5) |

¹ March has no computed baseline — investigate whether March 2005–2019 MOM data is present.

**Pattern:** February and spring/summer months tend to exceed baseline. This is a seasonal pattern, not a structural shift. The below-baseline readings in Sep 2024 and May 2025 further argue against a persistent trend.

---

### Year-over-year (YOY) — age 20–35
*Quarterly entry rates. Baseline = 2005–2019 seasonal mean per quarter-of-year.*

| Quarter | Entry rate | Inc-only | vs. baseline |
|---|---|---|---|
| 2023 Q4 | 1.83% | 1.81% | — (z=−1.0) |
| 2024 Q4 | 1.95% | 1.42% | — (z=−0.5) |
| **2025 Q1** | **2.50%** | **2.30%** | **above** (z=1.3) |
| 2025 Q2 | 2.08% | 1.72% | — (z=0.2) |
| 2025 Q3 | 2.01% | 1.79% | — (z=0.0) |
| 2025 Q4 | 2.13% | 1.85% | — (z=0.1) |

**Gap:** 2024 Q1–Q3 are missing from YOY. The extract skips Jan–Sep 2023, which are the T0 observations needed to produce T1 pairs landing in 2024 Q1–Q3. A supplemental extract covering Jan–Sep 2023 would fill this gap.

**Pattern:** 2025 Q1 is the only above-baseline quarter, and only modestly so (z=1.3). The series is otherwise flat against baseline.

---

### Divergence check

Several MOM above-baseline periods (Feb 2024, Jul 2024, Feb 2025, Jun–Aug 2025) have no corresponding YOY above-baseline reading. Per the Kauffman methodology, MOM spikes without YOY confirmation suggest attempted but abandoned self-employment — gig or informal arrangements that don't survive 12 months — rather than durable business formation.

---

## Next steps

1. Fill the Jan–Sep 2023 extract gap to recover 2024 Q1–Q3 YOY data.
2. Investigate the March baseline NaN — confirm March 2005–2019 MOM pairs are present.
3. Run the same analysis for the 36–50 and 51–64 age groups to contextualize whether the ≤35 pattern is age-specific or economy-wide.
4. Consider confidence intervals — the post-age-filter sample is small per quarter and z-scores alone may be noisy.
