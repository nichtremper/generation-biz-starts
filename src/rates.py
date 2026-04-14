"""
Entry rate computation and aggregation for MOM and YOY matched pairs.
"""

import pandas as pd


AGE_GROUPS = {
    "35_and_under": (20, 35),
    "36_to_50": (36, 50),
    "51_plus": (51, 64),
}

# Baseline and analysis periods
BASELINE_YEARS = range(2005, 2020)
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


def compute_baseline_stats(rates: pd.DataFrame, period_col: str) -> pd.DataFrame:
    """
    Compute mean and SD of entry rates for the 2005-2019 baseline, controlling for seasonality.

    For MOM rates: groups by (age_group, month). For YOY rates: groups by (age_group, quarter-of-year).
    Returns a DataFrame with baseline_mean and baseline_sd for each seasonal bucket.
    """
    if period_col == "period":
        baseline = rates[rates[period_col].dt.year.isin(BASELINE_YEARS)].copy()
        baseline["season"] = baseline[period_col].dt.month
        group_cols = ["age_group", "season"]
    else:
        baseline = rates[rates[period_col].dt.year.isin(BASELINE_YEARS)].copy()
        baseline["season"] = baseline[period_col].dt.quarter
        group_cols = ["age_group", "season"]

    stats = (
        baseline.groupby(group_cols)["entry_rate"]
        .agg(baseline_mean="mean", baseline_sd="std")
        .reset_index()
    )
    return stats


def flag_recent_vs_baseline(
    rates: pd.DataFrame, baseline_stats: pd.DataFrame, period_col: str
) -> pd.DataFrame:
    """
    Join baseline stats onto recent-period rates and flag quarters >1 SD from baseline mean.
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
    merged["z_score"] = (merged["entry_rate"] - merged["baseline_mean"]) / merged["baseline_sd"]
    merged["above_baseline"] = merged["z_score"] > 1
    merged["below_baseline"] = merged["z_score"] < -1

    return merged
