"""
Entry rate and persistence rate computation for MOM and YOY matched pairs.
"""

import logging
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
            rate_inc = _entry_rate(grp, "new_entrant_inc", "at_risk_inc", "WTFINL_t0")
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
            rate_inc = _entry_rate(grp, "new_entrant_inc", "at_risk_inc", "weight")
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
    merged["z_score"] = (merged[rate_col] - merged["baseline_mean"]) / merged["baseline_sd"]
    merged["above_baseline"] = merged["z_score"] > 1
    merged["below_baseline"] = merged["z_score"] < -1

    return merged
