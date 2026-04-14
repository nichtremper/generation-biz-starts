# Code Review — Generation Business Starts
Reviewer: Claude (acting as subject matter expert in entrepreneurship economics and IPUMS CPS)
Date: 2026-04-14

Severity labels: **Critical** (would materially affect conclusions), **Moderate** (affects validity or comparability), **Minor** (presentational or robustness).

---

## 1. Methodology

### [Critical] Denominator includes unemployed and NILF persons

`src/classify.py:58` sets `at_risk = ~se_t0`, which is `True` for every non-SE person regardless of employment status — including the unemployed, people not in the labor force, students, retirees, and (before the age fix) children.

The Kauffman New Entrepreneur Rate uses **employed civilians not in SE** as the denominator. Including unemployed and NILF persons massively inflates the denominator and depresses entry rates below Kauffman-comparable levels. This also distorts cross-period comparisons: when unemployment rises (e.g., 2009, 2020), the denominator grows, suppressing the measured entry rate independently of any change in actual SE formation behavior.

**Fix:** restrict `at_risk` to persons with `EMPSTAT` indicating employed (`EMPSTAT` codes 10–12 in IPUMS CPS). The extract already includes `EMPSTAT`, so no re-pull is needed. Same fix needed for `at_risk_inc`.

---

### [Critical] No temporal validation in MOM joins

`src/match.py:25` joins T0 and T1 on `CPSIDP` alone. There is no check that the T1 observation is actually one month after T0. A person with `MISH=1` could appear across multiple years — the join will match their `MISH=1` record from, say, January 2010 to any `MISH=2` record with the same `CPSIDP`, including one from a completely different rotation stint.

In practice the CPS rotation structure makes this rare (CPSIDP is designed to be unique per person-stint), but the correct validation is to confirm `(YEAR_t1, MONTH_t1)` is exactly one month after `(YEAR_t0, MONTH_t0)`. Without this, spurious cross-year or cross-rotation matches can silently enter the dataset.

**Fix:** after the join, add a filter:
```python
expected_month = (pl.col("MONTH_t0") % 12) + 1
expected_year = pl.col("YEAR_t0") + (pl.col("MONTH_t0") == 12).cast(pl.Int64)
validated = joined.filter(
    (pl.col("MONTH_t1") == expected_month) & (pl.col("YEAR_t1") == expected_year)
)
```

---

### [Critical] CPSIDP=0 creates spurious cross-joins

In IPUMS CPS, `CPSIDP=0` indicates a person who **cannot be longitudinally linked** (group quarters residents, households that changed composition, certain movers). Both `build_mom_pairs` and `build_yoy_pairs` join on `CPSIDP` without excluding zeros.

An inner join on `CPSIDP=0` cross-joins every non-linkable T0 person with every non-linkable T1 person — potentially thousands of spurious pairs per month. The age/sex validation filters some of these (a 25-year-old woman won't match a 60-year-old man) but not all: same-age, same-sex non-linkable persons will spuriously match.

This is silent — the code produces no warning, and the inflated pair count (20.7M MOM, 2.2M YOY) may include a meaningful fraction of false matches.

**Fix:** add `lf.filter(pl.col("CPSIDP") != 0)` before splitting into T0 and T1, in both functions.

---

### [Moderate] `new_entrant_inc` conflates new entrants with within-SE switchers

`src/classify.py:52` defines `new_entrant_inc = ~se_inc_t0 & se_inc_t1`. This counts:
1. Wage/salary → incorporated SE (true new entrant — what we want)
2. Unincorporated SE → incorporated SE (within-SE restructuring — not new formation)
3. Unemployed/NILF → incorporated SE (labor market entry — debatable)

Category (2) inflates the incorporated new entrant count and makes `new_entrant_inc` not directly interpretable as "new incorporated business formation." The session results showed 83,501 MOM `new_entrant_inc` vs 95,262 `new_entrant` combined — 87.6% incorporated. Some of that gap is category (2) switchers inflating the incorporated count, not a genuine signal that almost all new SE is incorporated.

**Fix:** define a cleaner `new_entrant_inc_strict = ~se_t0 & se_inc_t1` (was not SE at all at T0, is incorporated SE at T1). The current variable is still useful but should be labeled as "transitioned to incorporated" rather than "new incorporated entrant."

---

### [Moderate] Baseline period (2005–2019) embeds the Great Recession

The 15-year baseline spans a boom (2005–2007), a severe recession (2008–2010), and a slow recovery (2011–2019). This means the baseline mean and SD are influenced by a period of unusually depressed entrepreneurship (post-GFC). The session findings show a visible secular decline in SE entry rates from 2006 to ~2013. A recent rate that merely matches the 2005–2019 average could still be low relative to the pre-GFC norm.

There are legitimate arguments for keeping 2005–2019 (maximum data, includes full cycle), but the choice should be made explicitly, and results should be checked against a 2010–2019 baseline as a robustness test.

---

### [Moderate] Age range is non-standard relative to Kauffman

The code uses `(20, 35)` for the young group. Kauffman's New Entrepreneur Rate reports use **20–34** as the young adult category. Using 20–35 includes 35-year-olds who Kauffman classifies in the next bracket. This is a one-year difference but matters for comparability with published Kauffman figures. `rates.py:8` should be `(20, 34)` if direct comparison to Kauffman is intended.

---

### [Minor] YOY timing is approximately 12 months, not exactly

`MISH=4 → MISH=8` spans the 4th month of the first stint to the 4th month of the second stint. The gap is the remaining months of the first stint plus the 8-month rest period. In most cases this is close to 12 calendar months, but it is not guaranteed to be exactly 12. The code validates `AGE_t1 - AGE_t0 == 1` (which would catch most off-by-a-year errors) but does not validate that `MONTH_t0 == MONTH_t1`. If `MONTH_t0 != MONTH_t1`, the pair represents a different-calendar-month comparison, which undermines the "same seasonal position one year later" logic. This is likely rare but should be filtered.

---

### [Minor] Divergence interpretation overstates certainty

`04_analysis.py:83` prints "If MOM above_baseline=True but YOY above_baseline=False, this signals attempted but abandoned self-employment." This is one plausible interpretation, but another is simply differential attrition from the matched-pair design: unincorporated/gig SE workers have higher survey non-response and residential mobility, making them less likely to appear in YOY links. The "abandoned attempt" signal and the "measurement artifact" signal are observationally identical in this design. The language should be hedged.

---

## 2. Rates computation (`src/rates.py`)

### [Moderate] March baseline NaN is likely a symptom of a real data gap

`compute_baseline_stats` uses `pandas.std()` which returns `NaN` if fewer than 2 non-NaN observations exist for that seasonal bucket. March showing `NaN` baseline in both 2024 and 2025 output suggests that most or all March months in the 2005–2019 baseline have `NaN` entry rates — likely because the age-filtered MOM pairs for March in those years have zero weight or zero at-risk observations.

This could indicate a genuine data sparsity problem for March specifically (perhaps a CPS sampling artifact) or a bug in period construction. Either way, March rates cannot be compared to baseline in the current implementation, and the visualization will silently show March as unanchored.

**Fix:** add a diagnostic to `compute_baseline_stats` that logs which seasonal buckets have fewer than 5 observations or return NaN.

### [Minor] Rolling average can bleed across age group boundaries

`rates.py:61`:
```python
result.groupby("age_group")["entry_rate"]
.transform(lambda s: s.rolling(3, min_periods=1).mean())
```
The DataFrame is sorted by `["age_group", "period"]` before this operation, so the groupby correctly isolates each age group. This is fine — but the sort happens on line 58 and the rolling is computed on line 61 via transform. If the sort order ever changes upstream, the rolling will silently bleed across age group boundaries. The groupby in `transform` protects against this, but a comment noting the dependency would help.

### [Minor] String comparison for recent period start is fragile

`rates.py:149`:
```python
rates[period_col] >= "2023-10"
```
Comparing a `datetime64` column to a string works in current pandas but is version-dependent. Should be `pd.Timestamp("2023-10-01")`.

---

## 3. Confidence intervals (`scripts/05_visualize.py`)

### [Moderate] CI method underestimates uncertainty by ~22–41%

`ci_bounds` uses `se = sqrt(p * (1-p) / n_at_risk)` — the simple binomial formula assuming simple random sampling. CPS uses stratified cluster sampling with design effects (DEFF) typically 1.5–2.0 for employment/SE variables. The true standard error is `sqrt(DEFF) * sqrt(p*(1-p)/n)`, meaning the bands shown are 22–41% too narrow.

Without PSU/stratum variables in the extract (not currently pulled), exact design-effect correction isn't possible. A pragmatic fix is to apply a conservative scalar:

```python
DESIGN_EFFECT = 1.5
se = np.sqrt(DESIGN_EFFECT * rate * (1 - rate) / n.clip(lower=1))
```

This should be shown in the chart subtitle or a note.

### [Minor] `n_at_risk` overestimates effective sample size

The effective sample size for a weighted proportion is `n_eff = (Σw)² / Σw²`, which is almost always less than the raw count. `n_at_risk` is the unweighted head count, which will be larger than `n_eff` wherever weights are unequal. This compounds the underestimation of CI width noted above.

---

## 4. Matching logic (`src/match.py`)

### See Critical items above (CPSIDP=0, no temporal validation).

### [Minor] YOY age validation is slightly too strict

`build_yoy_pairs:54` requires `AGE_t1 - AGE_t0 == 1` exactly. If a respondent reports the same age at both MISH=4 and MISH=8 due to interview timing (both interviews before their birthday in consecutive years), the age difference would be 0. This is more likely to occur than in MOM, where allowing ±1 handles it. YOY should allow `is_between(0, 1)` to match the MOM convention and avoid dropping valid pairs.

---

## 5. Code quality and robustness

### [Moderate] `03_classify.py` loads full 722MB parquet into pandas

`classify.py:37`: `df = pd.read_parquet(path)` loads the entire MOM matched file into memory as a pandas DataFrame. This is the same memory pattern that caused the ~40GB RAM spike in `02_match.py` before it was refactored to use chunked Polars processing. It worked this run, but on a MacBook with limited RAM and other processes running, this is fragile. Classification logic is simple column operations and could be done entirely in Polars without loading into memory.

### [Minor] Interrupted chunk conversion produces corrupt cache silently

`02_match.py:53`: if the script is interrupted while writing chunks, the `CHUNK_DIR` will exist with an incomplete set of files. On the next run, `load_or_convert` finds existing chunks and skips conversion — silently working with a partial dataset. There is no row count validation against the full extract.

**Fix:** write chunks to a temp directory and atomically rename on completion, or write a manifest file with expected row count and validate on load.

### [Minor] `01_extract.py` requests future months that don't exist yet

`RECENT` includes all months through December 2025. If the script is run before some of those months are available in IPUMS, `resolve_samples` warns and skips them — but the downstream pipeline has no way to distinguish "month not yet in IPUMS" from "month genuinely absent." A stale extract re-run months later would silently add new data without any indication that the matched pairs and rates need to be regenerated.

---

## Summary: issues to address before publication

| Priority | Issue | File |
|---|---|---|
| Critical | Filter `CPSIDP=0` before joins | `src/match.py` |
| Critical | Add temporal validation to MOM joins | `src/match.py` |
| Critical | Restrict `at_risk` to employed non-SE only | `src/classify.py` |
| Moderate | Define `new_entrant_inc_strict` excluding uninc→inc switchers | `src/classify.py` |
| Moderate | Apply design effect scalar to CI bands | `scripts/05_visualize.py` |
| Moderate | Investigate and document March baseline NaN | `src/rates.py` |
| Moderate | Run robustness check with 2010–2019 baseline | `src/rates.py` |
| Minor | Fix age range to 20–34 for Kauffman comparability | `src/rates.py` |
| Minor | Validate `MONTH_t0 == MONTH_t1` in YOY | `src/match.py` |
| Minor | Fix string comparison to `pd.Timestamp` | `src/rates.py` |
| Minor | Harden chunk cache against partial writes | `scripts/02_match.py` |
