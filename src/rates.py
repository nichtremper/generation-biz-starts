"""
Entry rate and persistence rate computation for MOM and YOY matched pairs.
"""

import logging
import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

AGE_GROUPS = {
    # Brackets match Kauffman New Entrepreneur Rate exactly
    "20_to_34": (20, 34),
    "35_to_44": (35, 44),
    "45_to_54": (45, 54),
    "55_to_64": (55, 64),
    # Overall all-age group for direct comparison to published Kauffman rate
    "20_to_64": (20, 64),
}

# Baseline and analysis periods
BASELINE_YEARS = range(2005, 2020)
# Robustness baseline: excludes Great Recession, starts post-GFC recovery
BASELINE_YEARS_ROBUST = range(2010, 2020)
COVID_YEARS = range(2020, 2023)
RECENT_START = ("2023", "10")  # October 2023


def _newey_west_var_of_mean(series: np.ndarray) -> float:
    """
    Newey-West HAC variance estimate for the mean of `series`.

    Accounts for autocorrelation in a time series when estimating the
    precision of the mean. Returns Var(mean), not SD or SE.

    Bandwidth L = floor(T^(1/3)) per Newey & West (1987) recommendation.
    Falls back to classical variance / n for very short series (T < 4).
    """
    x = np.asarray(series, dtype=float)
    x = x[~np.isnan(x)]
    T = len(x)
    if T < 4:
        return float(np.var(x, ddof=1)) / max(T, 1)
    bandwidth = max(1, int(np.floor(T ** (1 / 3))))
    e = x - x.mean()
    s0 = np.dot(e, e) / T
    nw_sum = s0
    for k in range(1, bandwidth + 1):
        sk = np.dot(e[k:], e[:-k]) / T
        nw_sum += 2 * (1.0 - k / (bandwidth + 1)) * sk
    return max(nw_sum, 0.0) / T


def _entry_rate(df: pd.DataFrame, entrant_col: str, at_risk_col: str, weight_col: str) -> float:
    """Weighted entry rate: sum(weight * entrant) / sum(weight * at_risk)."""
    at_risk = df[df[at_risk_col]]
    if at_risk[weight_col].sum() == 0:
        return float("nan")
    return (at_risk[weight_col] * at_risk[entrant_col]).sum() / at_risk[weight_col].sum()


def compute_mom_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute monthly entry rates from MOM matched pairs, by age group.

    Uses WTFINL_t0 as the survey weight. Returns a tidy DataFrame with
    columns: year, month, age_group, entry_rate, entry_rate_inc, n_at_risk.
    Applies a 3-month rolling average per age group for visualization.
    """
    df = df.copy()
    df["period"] = pd.to_datetime(
        df["YEAR_t0"].astype(str) + "-" + df["MONTH_t0"].astype(str).str.zfill(2)
    )

    records = []
    for group, (age_min, age_max) in AGE_GROUPS.items():
        age_mask = df["AGE_t0"].between(age_min, age_max)
        subset = df[age_mask]

        for period, grp in subset.groupby("period"):
            rate = _entry_rate(grp, "new_entrant", "at_risk", "WTFINL_t0")
            # Use strict incorporated definition: ~se_t0 & se_inc_t1 with at_risk
            # denominator (employed non-SE). Excludes uninc→inc restructurings so
            # entry_rate_inc measures pure new incorporated business formation.
            rate_inc = _entry_rate(grp, "new_entrant_inc_strict", "at_risk", "WTFINL_t0")
            n_at_risk = grp["at_risk"].sum()
            records.append({
                "period": period,
                "age_group": group,
                "entry_rate": rate,
                "entry_rate_inc": rate_inc,
                "n_at_risk": n_at_risk,
            })

    result = pd.DataFrame(records).sort_values(["age_group", "period"])

    # 3-month rolling average
    result["entry_rate_3mo"] = (
        result.groupby("age_group")["entry_rate"]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
    )
    result["entry_rate_inc_3mo"] = (
        result.groupby("age_group")["entry_rate_inc"]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
    )

    return result


def compute_yoy_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute quarterly entry rates from YOY matched pairs, by age group.

    Uses LNKFW1YWT_t1 as the survey weight (linked year-over-year weight).
    Falls back to WTFINL_t0 if LNKFW1YWT is unavailable or zero.
    Returns a tidy DataFrame with columns: quarter, age_group, entry_rate,
    entry_rate_inc, n_at_risk.
    """
    df = df.copy()

    # Determine weight: prefer LNKFW1YWT_t1 if present and nonzero
    if "LNKFW1YWT_t1" in df.columns:
        df["weight"] = df["LNKFW1YWT_t1"].where(df["LNKFW1YWT_t1"] > 0, df["WTFINL_t0"])
    else:
        df["weight"] = df["WTFINL_t0"]

    df["quarter"] = pd.PeriodIndex(
        pd.to_datetime(
            df["YEAR_t1"].astype(str) + "-" + df["MONTH_t1"].astype(str).str.zfill(2)
        ),
        freq="Q",
    )

    records = []
    for group, (age_min, age_max) in AGE_GROUPS.items():
        age_mask = df["AGE_t0"].between(age_min, age_max)
        subset = df[age_mask]

        for quarter, grp in subset.groupby("quarter"):
            rate = _entry_rate(grp, "new_entrant", "at_risk", "weight")
            # Strict incorporated definition: see compute_mom_rates for rationale.
            rate_inc = _entry_rate(grp, "new_entrant_inc_strict", "at_risk", "weight")
            n_at_risk = grp["at_risk"].sum()
            records.append({
                "quarter": quarter,
                "age_group": group,
                "entry_rate": rate,
                "entry_rate_inc": rate_inc,
                "n_at_risk": n_at_risk,
            })

    return pd.DataFrame(records).sort_values(["age_group", "quarter"])


def compute_mom_persistence_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute monthly SE persistence (1-month survival) rates from MOM matched pairs.

    Persistence rate = fraction of SE workers at T0 still SE at T1.
    Uses WTFINL_t0 as the survey weight. Returns a tidy DataFrame with
    columns: period, age_group, persistence_rate, persistence_rate_inc, n_se.
    Applies a 3-month rolling average per age group for visualization.
    """
    df = df.copy()
    df["period"] = pd.to_datetime(
        df["YEAR_t0"].astype(str) + "-" + df["MONTH_t0"].astype(str).str.zfill(2)
    )

    records = []
    for group, (age_min, age_max) in AGE_GROUPS.items():
        age_mask = df["AGE_t0"].between(age_min, age_max)
        subset = df[age_mask]

        for period, grp in subset.groupby("period"):
            rate = _entry_rate(grp, "continuing", "se_t0", "WTFINL_t0")
            rate_inc = _entry_rate(grp, "continuing_inc", "se_inc_t0", "WTFINL_t0")
            n_se = int(grp["se_t0"].sum())
            records.append({
                "period": period,
                "age_group": group,
                "persistence_rate": rate,
                "persistence_rate_inc": rate_inc,
                "n_se": n_se,
            })

    result = pd.DataFrame(records).sort_values(["age_group", "period"])

    result["persistence_rate_3mo"] = (
        result.groupby("age_group")["persistence_rate"]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
    )
    result["persistence_rate_inc_3mo"] = (
        result.groupby("age_group")["persistence_rate_inc"]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
    )

    return result


def compute_yoy_persistence_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute quarterly SE persistence (12-month survival) rates from YOY matched pairs.

    Persistence rate = fraction of SE workers at MISH=4 still SE at MISH=8 (~1 year later).
    Uses LNKFW1YWT_t1 as the survey weight, falling back to WTFINL_t0 if unavailable.
    Returns a tidy DataFrame with columns: quarter, age_group, persistence_rate,
    persistence_rate_inc, n_se.
    """
    df = df.copy()

    if "LNKFW1YWT_t1" in df.columns:
        df["weight"] = df["LNKFW1YWT_t1"].where(df["LNKFW1YWT_t1"] > 0, df["WTFINL_t0"])
    else:
        df["weight"] = df["WTFINL_t0"]

    df["quarter"] = pd.PeriodIndex(
        pd.to_datetime(
            df["YEAR_t1"].astype(str) + "-" + df["MONTH_t1"].astype(str).str.zfill(2)
        ),
        freq="Q",
    )

    records = []
    for group, (age_min, age_max) in AGE_GROUPS.items():
        age_mask = df["AGE_t0"].between(age_min, age_max)
        subset = df[age_mask]

        for quarter, grp in subset.groupby("quarter"):
            rate = _entry_rate(grp, "continuing", "se_t0", "weight")
            rate_inc = _entry_rate(grp, "continuing_inc", "se_inc_t0", "weight")
            n_se = int(grp["se_t0"].sum())
            records.append({
                "quarter": quarter,
                "age_group": group,
                "persistence_rate": rate,
                "persistence_rate_inc": rate_inc,
                "n_se": n_se,
            })

    return pd.DataFrame(records).sort_values(["age_group", "quarter"])


def compute_mom_transition_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute monthly unemployment→SE and employment→SE transition rates from MOM pairs.

    Unemployment→SE rate: weighted share of persons unemployed at T0 (EMPSTAT in [20,21,22])
    who are SE at T1.
    Employment→SE rate: same as entry_rate — weighted share of employed non-SE at T0
    (the at_risk pool) who are SE at T1.

    Both rates are computed per age group per month and 3-month rolling averages appended.
    """
    UNEMPLOYED_CODES = [20, 21, 22]

    df = df.copy()
    df["period"] = pd.to_datetime(
        df["YEAR_t0"].astype(str) + "-" + df["MONTH_t0"].astype(str).str.zfill(2)
    )

    records = []
    for group, (age_min, age_max) in AGE_GROUPS.items():
        subset = df[df["AGE_t0"].between(age_min, age_max)]

        for period, grp in subset.groupby("period"):
            # Unemployment → SE
            unemp = grp[grp["EMPSTAT_t0"].isin(UNEMPLOYED_CODES)]
            wt_unemp = unemp["WTFINL_t0"].sum()
            unemp_rate = (
                (unemp["WTFINL_t0"] * unemp["new_entrant"]).sum() / wt_unemp
                if wt_unemp > 0 else float("nan")
            )

            # Employment → SE (existing at_risk formula)
            emp_rate = _entry_rate(grp, "new_entrant", "at_risk", "WTFINL_t0")

            records.append({
                "period":         period,
                "age_group":      group,
                "unemp_to_se":    unemp_rate,
                "emp_to_se":      emp_rate,
                "n_unemp":        len(unemp),
                "n_emp_at_risk":  int(grp["at_risk"].sum()),
            })

    result = pd.DataFrame(records).sort_values(["age_group", "period"])

    for col in ["unemp_to_se", "emp_to_se"]:
        result[f"{col}_3mo"] = (
            result.groupby("age_group")[col]
            .transform(lambda s: s.rolling(3, min_periods=1).mean())
        )

    return result


def compute_quarterly_transition_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute quarterly unemployment→SE and employment→SE transition rates from MOM pairs.

    Same logic as compute_mom_transition_rates but groups by T0 quarter, aggregating
    all month-to-month transitions within the quarter before computing rates.
    This pools ~3× the observations per period, substantially reducing noise
    relative to the monthly version.
    """
    UNEMPLOYED_CODES = [20, 21, 22]

    df = df.copy()
    df["quarter"] = pd.PeriodIndex(
        pd.to_datetime(
            df["YEAR_t0"].astype(str) + "-" + df["MONTH_t0"].astype(str).str.zfill(2)
        ),
        freq="Q",
    )

    records = []
    for group, (age_min, age_max) in AGE_GROUPS.items():
        subset = df[df["AGE_t0"].between(age_min, age_max)]

        for quarter, grp in subset.groupby("quarter"):
            unemp = grp[grp["EMPSTAT_t0"].isin(UNEMPLOYED_CODES)]
            wt_unemp = unemp["WTFINL_t0"].sum()
            unemp_rate = (
                (unemp["WTFINL_t0"] * unemp["new_entrant"]).sum() / wt_unemp
                if wt_unemp > 0 else float("nan")
            )
            emp_rate = _entry_rate(grp, "new_entrant", "at_risk", "WTFINL_t0")

            records.append({
                "quarter":       quarter,
                "age_group":     group,
                "unemp_to_se":   unemp_rate,
                "emp_to_se":     emp_rate,
                "n_unemp":       len(unemp),
                "n_emp_at_risk": int(grp["at_risk"].sum()),
            })

    return pd.DataFrame(records).sort_values(["age_group", "quarter"])


def compute_baseline_stats(
    rates: pd.DataFrame, period_col: str, baseline_years=None, rate_col: str = "entry_rate"
) -> pd.DataFrame:
    """
    Compute mean and SD of entry rates for a baseline window, controlling for seasonality.

    For MOM rates: groups by (age_group, month). For YOY rates: groups by (age_group, quarter-of-year).
    Returns a DataFrame with baseline_mean, baseline_sd, and n_obs for each seasonal bucket.

    Args:
        rates: Output of a compute_*_rates function.
        period_col: "period" for MOM, "quarter" for YOY.
        baseline_years: Iterable of years to include in the baseline.
            Defaults to BASELINE_YEARS (2005–2019). Pass BASELINE_YEARS_ROBUST
            (2010–2019) for the post-GFC robustness check.
        rate_col: Name of the rate column to aggregate. Defaults to "entry_rate".
            Pass "persistence_rate" for persistence rate DataFrames.
    """
    if baseline_years is None:
        baseline_years = BASELINE_YEARS

    if period_col == "period":
        baseline = rates[rates[period_col].dt.year.isin(baseline_years)].copy()
        baseline["season"] = baseline[period_col].dt.month
        group_cols = ["age_group", "season"]
    else:
        baseline = rates[rates[period_col].dt.year.isin(baseline_years)].copy()
        baseline["season"] = baseline[period_col].dt.quarter
        group_cols = ["age_group", "season"]

    stats = (
        baseline.groupby(group_cols)[rate_col]
        .agg(baseline_mean="mean", baseline_sd="std", n_obs="count")
        .reset_index()
    )

    # Newey-West HAC SD: corrects for autocorrelation in the baseline series so
    # that z-scores for a single new observation reflect the true spread of the
    # process (not just the precision of the estimated mean).
    #
    # For an AR(1) process with ρ > 0, positive autocorrelation means consecutive
    # observations are more similar than independent draws — the effective sample
    # size is reduced, and the estimated SD of the distribution is upward-biased.
    # NW corrects this: baseline_nw_sd = √(nw_sum) where
    #   nw_sum = γ_0 + 2 Σ_{k=1}^{L} w_k γ_k  (NW long-run variance)
    # This is LARGER than baseline_sd for ρ > 0, producing SMALLER (conservative)
    # z-scores. The SE of the mean baseline_nw_se = √(nw_sum/T) is also stored
    # for use in mean-comparison tests (e.g., is the mean of several recent
    # quarters statistically different from the baseline mean?).
    def _nw_sd(s):
        """NW long-run SD for a single-observation z-score (wider than naive SD)."""
        vals = s.values
        nw_var_mean = _newey_west_var_of_mean(vals)
        n = len(vals[~np.isnan(vals)])
        nw_sum = nw_var_mean * max(n, 1)  # long-run variance = Var_of_mean × T
        return float(np.sqrt(nw_sum))

    def _nw_se(s):
        """NW SE of the historical mean (for mean-comparison tests)."""
        return float(np.sqrt(_newey_west_var_of_mean(s.values)))

    nw_sd_series = (
        baseline.groupby(group_cols)[rate_col]
        .apply(_nw_sd)
        .reset_index(name="baseline_nw_sd")
    )
    nw_se_series = (
        baseline.groupby(group_cols)[rate_col]
        .apply(_nw_se)
        .reset_index(name="baseline_nw_se")
    )
    stats = stats.merge(nw_sd_series, on=group_cols, how="left")
    stats = stats.merge(nw_se_series, on=group_cols, how="left")

    # Diagnostic: flag sparse or NaN buckets so March-like gaps are visible
    sparse = stats[(stats["n_obs"] < 5) | stats["baseline_mean"].isna()]
    if not sparse.empty:
        for _, row in sparse.iterrows():
            log.warning(
                "Sparse baseline bucket: age_group=%s season=%s n_obs=%d "
                "baseline_mean=%s — rates for this bucket cannot be compared to baseline.",
                row["age_group"], row["season"], row["n_obs"], row["baseline_mean"],
            )

    return stats


def flag_recent_vs_baseline(
    rates: pd.DataFrame, baseline_stats: pd.DataFrame, period_col: str,
    rate_col: str = "entry_rate",
) -> pd.DataFrame:
    """
    Join baseline stats onto recent-period rates and flag periods >1 SD from baseline mean.

    Args:
        rate_col: Name of the rate column to compare. Defaults to "entry_rate".
            Pass "persistence_rate" for persistence rate DataFrames.
    """
    recent = rates[
        rates[period_col] >= pd.Period("2023Q4", freq="Q")
        if period_col == "quarter"
        else rates[period_col] >= "2023-10"
    ].copy()

    if period_col == "period":
        recent["season"] = recent[period_col].dt.month
    else:
        recent["season"] = recent[period_col].dt.quarter

    merged = recent.merge(baseline_stats, on=["age_group", "season"], how="left")

    # z_score: how many SDs of *historical rate variation* above the baseline mean.
    # This is a descriptive measure of how unusual the period is relative to history;
    # it does NOT test whether the mean is statistically different from baseline.
    merged["z_score"] = (merged[rate_col] - merged["baseline_mean"]) / merged["baseline_sd"]

    # z_score_nw: Newey-West autocorrelation-corrected descriptive z-score.
    # Uses baseline_nw_sd = √(NW long-run variance) as the denominator.
    # For positively autocorrelated series (typical), baseline_nw_sd > baseline_sd,
    # so z_score_nw is SMALLER (more conservative) than z_score. This corrects for
    # the fact that autocorrelated observations provide less independent information
    # than i.i.d. draws, so the effective spread of the process is wider.
    # NOTE: baseline_nw_se (SE of the historical mean) is also available in the merged
    # frame for mean-comparison tests, but is NOT used here — using SE of the mean as
    # the denominator for a single new observation yields inflated z-scores (SE << SD).
    merged["z_score_nw"] = (
        (merged[rate_col] - merged["baseline_mean"]) / merged["baseline_nw_sd"]
    )

    # Threshold = 1.96 (95% confidence) for both z-score variants.
    # Using 1 SD (the prior threshold) yields ~32% false-positive rate under normality.
    merged["above_baseline"] = merged["z_score"] > 1.96
    merged["below_baseline"] = merged["z_score"] < -1.96
    merged["above_baseline_nw"] = merged["z_score_nw"] > 1.96
    merged["below_baseline_nw"] = merged["z_score_nw"] < -1.96

    return merged
