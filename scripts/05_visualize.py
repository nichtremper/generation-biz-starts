"""
Step 5: Time-series plots of SE entry and persistence rates with 95% confidence intervals.
Also plots SE stock: weighted counts (millions) and share of employed / labor force.

Reads:
  data/processed/rates_mom.parquet
  data/processed/rates_yoy.parquet
  data/processed/persistence_mom.parquet
  data/processed/persistence_yoy.parquet
  data/processed/se_stock.parquet           (optional — skipped if absent)

Saves to:
  figures/entry_rates_mom.png
  figures/entry_rates_yoy.png
  figures/persistence_rates_mom.png
  figures/persistence_rates_yoy.png
  figures/se_stock_count.png
  figures/se_stock_share.png

CI method: normal approximation with a conservative design-effect correction
(DESIGN_EFFECT = 1.5) to account for CPS stratified cluster sampling. True
DEFF is typically 1.5–2.0 for SE variables; this is a scalar approximation
since PSU/stratum variables are not in the extract.
"""

from datetime import datetime
from pathlib import Path
import sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
FIGURES_DIR = Path(__file__).parent.parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

COVID_START = pd.Timestamp("2020-01-01")
COVID_END   = pd.Timestamp("2022-12-31")
RECENT_START = pd.Timestamp("2023-10-01")

AGE_LABELS = {
    "20_to_34": "Age 20–34",
    "35_to_44": "Age 35–44",
    "45_to_54": "Age 45–54",
    "55_to_64": "Age 55–64",
    "20_to_64": "Age 20–64 (all)",
}

Z95 = 1.96
# Conservative design-effect scalar for CPS clustered sampling (DEFF typically 1.5–2.0).
# Applied as se = sqrt(DEFF * p*(1-p)/n) since PSU/stratum variables are not extracted.
DESIGN_EFFECT = 1.5


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def ci_bounds(rate: pd.Series, n: pd.Series):
    """Return (lower, upper) 95% CI series for a binomial proportion.

    Applies DESIGN_EFFECT scalar to correct for CPS clustered sampling.
    """
    se = np.sqrt(DESIGN_EFFECT * rate * (1 - rate) / n.clip(lower=1))
    return (rate - Z95 * se).clip(lower=0), rate + Z95 * se


def shade_background(ax, x_start, x_end):
    """Gray band for COVID era."""
    ax.axvspan(x_start, x_end, color="0.85", zorder=0, label="COVID era (2020–2022)")


def plot_mom(df: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(
        len(AGE_LABELS), 1, figsize=(13, 17), sharex=True, sharey=True,
        gridspec_kw={"hspace": 0.35},
    )
    fig.suptitle(
        "Self-Employment Entry Rate — Month-Over-Month (CPS)\n"
        "3-month rolling average  |  shaded band = 95% CI (design-effect corrected, DEFF=1.5)",
        fontsize=11,
    )

    for ax, (group, label) in zip(axes, AGE_LABELS.items()):
        sub = df[df["age_group"] == group].sort_values("period").copy()
        lo, hi = ci_bounds(sub["entry_rate"], sub["n_at_risk"])

        shade_background(ax, COVID_START, COVID_END)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)

        # CI band (on raw monthly rate)
        ax.fill_between(sub["period"], lo * 100, hi * 100,
                        color="steelblue", alpha=0.15, zorder=1)

        # Raw monthly rate (very faint, gives texture)
        ax.plot(sub["period"], sub["entry_rate"] * 100,
                color="steelblue", linewidth=0.5, alpha=0.35, zorder=2)

        # 3-month rolling average — primary line
        ax.plot(sub["period"], sub["entry_rate_3mo"] * 100,
                color="steelblue", linewidth=1.8, zorder=3, label="Combined SE (3mo avg)")

        # Incorporated only — 3mo rolling
        ax.plot(sub["period"], sub["entry_rate_inc_3mo"] * 100,
                color="darkorange", linewidth=1.4, linestyle="--", zorder=3,
                label="Incorporated only (3mo avg)")

        ax.set_title(label, fontsize=9, loc="left", pad=3)
        ax.set_ylabel("Entry rate (%)", fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
        ax.tick_params(axis="both", labelsize=8)

    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[-1].tick_params(axis="x", labelsize=8)

    # Single shared legend at top
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, framealpha=0.9,
               bbox_to_anchor=(0.98, 0.97))

    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    return fig


def plot_yoy(df: pd.DataFrame) -> plt.Figure:
    # Convert Period to timestamp for matplotlib
    df = df.copy()
    df["date"] = df["quarter"].dt.to_timestamp()

    fig, axes = plt.subplots(
        len(AGE_LABELS), 1, figsize=(13, 17), sharex=True, sharey=True,
        gridspec_kw={"hspace": 0.35},
    )
    fig.suptitle(
        "Self-Employment Entry Rate — Year-Over-Year (CPS, MISH 4→8)\n"
        "Quarterly  |  shaded band = 95% CI (design-effect corrected, DEFF=1.5)",
        fontsize=11,
    )

    for ax, (group, label) in zip(axes, AGE_LABELS.items()):
        sub = df[df["age_group"] == group].sort_values("date").copy()
        lo, hi = ci_bounds(sub["entry_rate"], sub["n_at_risk"])

        shade_background(ax, COVID_START, COVID_END)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)

        ax.fill_between(sub["date"], lo * 100, hi * 100,
                        color="steelblue", alpha=0.2, zorder=1)

        ax.plot(sub["date"], sub["entry_rate"] * 100,
                color="steelblue", linewidth=1.8, marker="o", markersize=3,
                zorder=3, label="Combined SE")

        ax.plot(sub["date"], sub["entry_rate_inc"] * 100,
                color="darkorange", linewidth=1.4, linestyle="--", marker="o", markersize=3,
                zorder=3, label="Incorporated only")

        ax.set_title(label, fontsize=9, loc="left", pad=3)
        ax.set_ylabel("Entry rate (%)", fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
        ax.tick_params(axis="both", labelsize=8)

    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[-1].tick_params(axis="x", labelsize=8)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, framealpha=0.9,
               bbox_to_anchor=(0.98, 0.97))

    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    return fig


def plot_persistence_mom(df: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(
        len(AGE_LABELS), 1, figsize=(13, 17), sharex=True, sharey=True,
        gridspec_kw={"hspace": 0.35},
    )
    fig.suptitle(
        "Self-Employment 1-Month Persistence Rate — Month-Over-Month (CPS)\n"
        "Fraction of SE workers remaining SE the following month  |  3-month rolling average",
        fontsize=11,
    )

    for ax, (group, label) in zip(axes, AGE_LABELS.items()):
        sub = df[df["age_group"] == group].sort_values("period").copy()
        lo, hi = ci_bounds(sub["persistence_rate"], sub["n_se"])

        shade_background(ax, COVID_START, COVID_END)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)

        ax.fill_between(sub["period"], lo * 100, hi * 100,
                        color="steelblue", alpha=0.15, zorder=1)
        ax.plot(sub["period"], sub["persistence_rate"] * 100,
                color="steelblue", linewidth=0.5, alpha=0.35, zorder=2)
        ax.plot(sub["period"], sub["persistence_rate_3mo"] * 100,
                color="steelblue", linewidth=1.8, zorder=3, label="Combined SE (3mo avg)")
        ax.plot(sub["period"], sub["persistence_rate_inc_3mo"] * 100,
                color="darkorange", linewidth=1.4, linestyle="--", zorder=3,
                label="Incorporated only (3mo avg)")

        ax.set_title(label, fontsize=9, loc="left", pad=3)
        ax.set_ylabel("Persistence rate (%)", fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0f}%"))
        ax.tick_params(axis="both", labelsize=8)

    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[-1].tick_params(axis="x", labelsize=8)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, framealpha=0.9,
               bbox_to_anchor=(0.98, 0.97))
    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    return fig


def plot_persistence_yoy(df: pd.DataFrame) -> plt.Figure:
    df = df.copy()
    df["date"] = df["quarter"].dt.to_timestamp()

    fig, axes = plt.subplots(
        len(AGE_LABELS), 1, figsize=(13, 17), sharex=True, sharey=True,
        gridspec_kw={"hspace": 0.35},
    )
    fig.suptitle(
        "Self-Employment 12-Month Persistence Rate — Year-Over-Year (CPS, MISH 4→8)\n"
        "Fraction of SE workers at MISH=4 still SE at MISH=8 (~1 year later)  |  Quarterly",
        fontsize=11,
    )

    for ax, (group, label) in zip(axes, AGE_LABELS.items()):
        sub = df[df["age_group"] == group].sort_values("date").copy()
        lo, hi = ci_bounds(sub["persistence_rate"], sub["n_se"])

        shade_background(ax, COVID_START, COVID_END)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)

        ax.fill_between(sub["date"], lo * 100, hi * 100,
                        color="steelblue", alpha=0.2, zorder=1)
        ax.plot(sub["date"], sub["persistence_rate"] * 100,
                color="steelblue", linewidth=1.8, marker="o", markersize=3,
                zorder=3, label="Combined SE")
        ax.plot(sub["date"], sub["persistence_rate_inc"] * 100,
                color="darkorange", linewidth=1.4, linestyle="--", marker="o", markersize=3,
                zorder=3, label="Incorporated only")

        ax.set_title(label, fontsize=9, loc="left", pad=3)
        ax.set_ylabel("Persistence rate (%)", fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0f}%"))
        ax.tick_params(axis="both", labelsize=8)

    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[-1].tick_params(axis="x", labelsize=8)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, framealpha=0.9,
               bbox_to_anchor=(0.98, 0.97))
    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    return fig


def _compute_annual_stock(df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse monthly stock to annual averages.

    Excludes months where share or count is NaN or zero (the March data gap
    produces zero-weighted rows in some years). Each metric is averaged over
    the available months; n_months records how many months contributed.
    """
    share_cols = [
        "se_share_employed", "se_share_inc_employed",
        "se_share_lf",       "se_share_inc_lf",
    ]
    count_cols = ["wt_se", "wt_se_inc", "wt_employed", "wt_lf"]

    records = []
    for (year, group), grp in df.groupby(["YEAR", "age_group"]):
        row = {"YEAR": year, "age_group": group}
        for col in share_cols + count_cols:
            vals = grp[col].replace(0, float("nan")).dropna()
            row[col]            = vals.mean() if len(vals) > 0 else float("nan")
            row[f"{col}_months"] = int(len(vals))
        records.append(row)

    return pd.DataFrame(records).sort_values(["age_group", "YEAR"])


def _prep_stock(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a datetime `period` column and 3-month rolling averages per age group.
    Called once by both stock plot functions.
    """
    df = df.copy()
    df["period"] = pd.to_datetime(
        df["YEAR"].astype(str) + "-" + df["MONTH"].astype(str).str.zfill(2)
    )
    df = df.sort_values(["age_group", "period"])

    for col in ["se_share_employed", "se_share_inc_employed", "se_share_lf", "se_share_inc_lf",
                "wt_se", "wt_se_inc"]:
        if col in df.columns:
            df[f"{col}_3mo"] = (
                df.groupby("age_group")[col]
                .transform(lambda s: s.rolling(3, min_periods=1).mean())
            )
    return df


def plot_se_stock_count(df: pd.DataFrame) -> plt.Figure:
    """
    Time-series of weighted SE count (millions) by age group.
    Solid line = combined SE; dashed = incorporated only.
    """
    fig, axes = plt.subplots(
        len(AGE_LABELS), 1, figsize=(13, 17), sharex=True,
        gridspec_kw={"hspace": 0.35},
    )
    fig.suptitle(
        "Self-Employed Workers — Weighted Count (CPS)\n"
        "Millions  |  3-month rolling average  |  combined and incorporated-only",
        fontsize=11,
    )

    for ax, (group, label) in zip(axes, AGE_LABELS.items()):
        sub = df[df["age_group"] == group].sort_values("period").copy()

        shade_background(ax, COVID_START, COVID_END)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)

        # Raw monthly (faint texture)
        ax.plot(sub["period"], sub["wt_se"] / 1e6,
                color="steelblue", linewidth=0.5, alpha=0.35, zorder=2)

        # 3-month rolling — combined SE
        ax.plot(sub["period"], sub["wt_se_3mo"] / 1e6,
                color="steelblue", linewidth=1.8, zorder=3, label="Combined SE (3mo avg)")

        # 3-month rolling — incorporated only
        ax.plot(sub["period"], sub["wt_se_inc_3mo"] / 1e6,
                color="darkorange", linewidth=1.4, linestyle="--", zorder=3,
                label="Incorporated only (3mo avg)")

        ax.set_title(label, fontsize=9, loc="left", pad=3)
        ax.set_ylabel("Workers (millions)", fontsize=8)
        ax.tick_params(axis="both", labelsize=8)

    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[-1].tick_params(axis="x", labelsize=8)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, framealpha=0.9,
               bbox_to_anchor=(0.98, 0.97))
    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    return fig


def plot_se_stock_share(df: pd.DataFrame) -> plt.Figure:
    """
    Time-series of SE share by age group.
    Two denominators: employed (EMPSTAT in [10,12]) and labor force (adds unemployed).
    Solid lines = combined SE; dashed = incorporated only.
    Two horizontal reference bands: 2005–2019 mean and 2016–2019 (immediate pre-COVID) mean,
    both computed from combined SE / employed.
    """
    # Pre-compute per-group baseline means for reference lines (combined SE / employed only)
    full_baseline_means = {}    # 2005–2019
    pre_covid_means = {}        # 2016–2019

    for group in AGE_LABELS:
        grp_df = df[df["age_group"] == group]
        mask_full = grp_df["period"].dt.year.isin(range(2005, 2020))
        mask_pre  = grp_df["period"].dt.year.isin(range(2016, 2020))
        full_baseline_means[group] = grp_df.loc[mask_full, "se_share_employed"].mean()
        pre_covid_means[group]     = grp_df.loc[mask_pre,  "se_share_employed"].mean()

    fig, axes = plt.subplots(
        len(AGE_LABELS), 1, figsize=(13, 17), sharex=True,
        gridspec_kw={"hspace": 0.35},
    )
    fig.suptitle(
        "Self-Employed Share of Workers — by Denominator (CPS)\n"
        "3-month rolling average  |  solid = employed base  |  dotted = labor force base\n"
        "dashed horizontals: 2005–2019 mean (gray) and 2016–2019 pre-COVID mean (olive)",
        fontsize=10,
    )

    for ax, (group, label) in zip(axes, AGE_LABELS.items()):
        sub = df[df["age_group"] == group].sort_values("period").copy()

        shade_background(ax, COVID_START, COVID_END)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)

        # Reference lines — combined SE / employed only, to avoid clutter
        full_mean = full_baseline_means[group]
        pre_mean  = pre_covid_means[group]
        if not np.isnan(full_mean):
            ax.axhline(full_mean * 100, color="#333333", linewidth=2.0, linestyle="--",
                       zorder=1, label="2005–2019 mean")
        if not np.isnan(pre_mean):
            ax.axhline(pre_mean * 100, color="crimson", linewidth=2.0, linestyle="--",
                       zorder=1, label="2016–2019 mean (pre-COVID)")

        # Combined SE — employed denominator (solid)
        ax.plot(sub["period"], sub["se_share_employed_3mo"] * 100,
                color="steelblue", linewidth=1.8, zorder=3,
                label="Combined SE / employed")

        # Combined SE — LF denominator (dotted)
        ax.plot(sub["period"], sub["se_share_lf_3mo"] * 100,
                color="steelblue", linewidth=1.2, linestyle=":", zorder=3,
                label="Combined SE / labor force")

        # Incorporated SE — employed denominator (dashed orange)
        ax.plot(sub["period"], sub["se_share_inc_employed_3mo"] * 100,
                color="darkorange", linewidth=1.4, linestyle="--", zorder=3,
                label="Incorporated SE / employed")

        # Incorporated SE — LF denominator (dot-dash orange)
        ax.plot(sub["period"], sub["se_share_inc_lf_3mo"] * 100,
                color="darkorange", linewidth=1.0, linestyle="-.", zorder=3,
                label="Incorporated SE / labor force")

        ax.set_title(label, fontsize=9, loc="left", pad=3)
        ax.set_ylabel("SE share (%)", fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1f}%"))
        ax.tick_params(axis="both", labelsize=8)

    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[-1].tick_params(axis="x", labelsize=8)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, framealpha=0.9,
               bbox_to_anchor=(0.98, 0.97))
    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    return fig


def plot_se_unemp_scatter(stock: pd.DataFrame) -> plt.Figure:
    """
    Scatter of monthly SE share (employed denominator) vs unemployment rate by age group.
    Points colored by era: baseline (2005–2019), COVID (2020–2022), recent (2023-10+).
    OLS fit computed on baseline only; line extended across full x-range so post-COVID
    deviation from the historical relationship is visible.
    """
    df = stock.copy()
    df["period"] = pd.to_datetime(
        df["YEAR"].astype(str) + "-" + df["MONTH"].astype(str).str.zfill(2)
    )
    df["unemp_rate"] = (df["wt_lf"] - df["wt_employed"]) / df["wt_lf"]

    def _era(row):
        if row["period"] >= RECENT_START:
            return "recent"
        if row["period"] >= COVID_START:
            return "COVID"
        return "baseline"

    df["era"] = df.apply(_era, axis=1)

    ERA_STYLE = {
        "baseline": dict(color="steelblue", alpha=0.35, s=12, zorder=3, label="2005–2019"),
        "COVID":    dict(color="0.55",      alpha=0.55, s=14, zorder=4, label="COVID 2020–2022"),
        "recent":   dict(color="crimson",   alpha=0.85, s=18, zorder=5, label="Recent (Oct 2023+)"),
    }

    fig, axes = plt.subplots(
        len(AGE_LABELS), 1, figsize=(10, 17),
        gridspec_kw={"hspace": 0.45},
    )
    fig.suptitle(
        "SE Share vs Unemployment Rate — Monthly (CPS)\n"
        "OLS fit on 2005–2019 baseline; COVID and recent points overlaid",
        fontsize=11,
    )

    for ax, (group, label) in zip(axes, AGE_LABELS.items()):
        sub = df[
            (df["age_group"] == group)
            & df["unemp_rate"].notna() & (df["unemp_rate"] > 0)
            & df["se_share_employed"].notna() & (df["se_share_employed"] > 0)
        ].copy()

        for era_name, style in ERA_STYLE.items():
            era_sub = sub[sub["era"] == era_name]
            ax.scatter(era_sub["unemp_rate"] * 100, era_sub["se_share_employed"] * 100,
                       **style)

        # OLS on baseline only, line extended to full x range
        base = sub[sub["era"] == "baseline"]
        if len(base) > 2:
            x = base["unemp_rate"].values * 100
            y = base["se_share_employed"].values * 100
            m, b = np.polyfit(x, y, 1)
            x_line = np.linspace(sub["unemp_rate"].min() * 100,
                                  sub["unemp_rate"].max() * 100, 200)
            ax.plot(x_line, m * x_line + b, color="steelblue", linewidth=1.5,
                    zorder=6, label=f"OLS baseline  β={m:.2f}")
            r = np.corrcoef(x, y)[0, 1]
            ax.text(0.97, 0.05, f"r = {r:.2f}", transform=ax.transAxes,
                    fontsize=8, ha="right", color="steelblue")

        ax.set_title(label, fontsize=9, loc="left", pad=3)
        ax.set_xlabel("Unemployment rate (%)", fontsize=8)
        ax.set_ylabel("SE share (%)", fontsize=8)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}%"))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}%"))
        ax.tick_params(axis="both", labelsize=8)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, framealpha=0.9,
               bbox_to_anchor=(0.98, 0.97))
    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    return fig


def plot_transition_index(df: pd.DataFrame) -> plt.Figure:
    """
    Unemployment→SE and employment→SE transition rates, both indexed to
    their 2005–2019 mean = 100. 3-month rolling averages.

    A post-COVID spike in the unemp→SE index but not the emp→SE index
    signals necessity entrepreneurship; convergence suggests broad SE entry.
    """
    df = df.copy()

    # Index each rate to its 2005–2019 mean per age group
    # Use smoothed columns if present (monthly), otherwise raw (quarterly)
    unemp_col = "unemp_to_se_3mo" if "unemp_to_se_3mo" in df.columns else "unemp_to_se"
    emp_col   = "emp_to_se_3mo"   if "emp_to_se_3mo"   in df.columns else "emp_to_se"

    for group in df["age_group"].unique():
        mask = df["age_group"] == group
        base = mask & df["period"].dt.year.isin(range(2005, 2020))
        for col in [unemp_col, emp_col]:
            base_mean = df.loc[base, col].mean()
            df.loc[mask, f"{col}_idx"] = (
                df.loc[mask, col] / base_mean * 100 if base_mean > 0 else float("nan")
            )

    fig, axes = plt.subplots(
        len(AGE_LABELS), 1, figsize=(13, 17), sharex=True,
        gridspec_kw={"hspace": 0.35},
    )
    fig.suptitle(
        "SE Entry Pathways — Indexed Transition Rates (CPS, MOM pairs aggregated quarterly)\n"
        "2005–2019 mean = 100  |  Crimson = unemployment→SE  |  Steelblue = employment→SE",
        fontsize=10,
    )

    for ax, (group, label) in zip(axes, AGE_LABELS.items()):
        sub = df[df["age_group"] == group].sort_values("period").copy()

        shade_background(ax, COVID_START, COVID_END)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)
        ax.axhline(100, color="0.5", linewidth=0.8, linestyle="-", zorder=1,
                   label="Baseline mean (= 100)")

        ax.plot(sub["period"], sub[f"{emp_col}_idx"],
                color="steelblue", linewidth=1.8, marker="o", markersize=3, zorder=3,
                label="Employment → SE")
        ax.plot(sub["period"], sub[f"{unemp_col}_idx"],
                color="crimson", linewidth=1.8, marker="o", markersize=3, zorder=3,
                label="Unemployment → SE")

        ax.set_title(label, fontsize=9, loc="left", pad=3)
        ax.set_ylabel("Index (2005–2019 = 100)", fontsize=8)
        ax.tick_params(axis="both", labelsize=8)

    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[-1].tick_params(axis="x", labelsize=8)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, framealpha=0.9,
               bbox_to_anchor=(0.98, 0.97))
    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    return fig


def plot_se_stock_annual_count(df: pd.DataFrame) -> plt.Figure:
    """
    Annual-average SE worker count (millions) by age group.
    One marker per year; solid = combined SE, dashed = incorporated only.
    """
    fig, axes = plt.subplots(
        len(AGE_LABELS), 1, figsize=(13, 17), sharex=True,
        gridspec_kw={"hspace": 0.35},
    )
    fig.suptitle(
        "Self-Employed Workers — Annual Average Count (CPS)\n"
        "Millions  |  mean of monthly counts, NaN/zero months excluded",
        fontsize=11,
    )

    years = sorted(df["YEAR"].unique())

    for ax, (group, label) in zip(axes, AGE_LABELS.items()):
        sub = df[df["age_group"] == group].sort_values("YEAR").copy()

        # COVID shading and recent-period marker by year
        ax.axvspan(2020, 2022 + 11/12, color="0.85", zorder=0, label="COVID era (2020–2022)")
        ax.axvline(2023 + 9/12, color="0.4", linewidth=0.8, linestyle=":", zorder=2)

        ax.plot(sub["YEAR"], sub["wt_se"] / 1e6,
                color="steelblue", linewidth=1.8, marker="o", markersize=4,
                zorder=3, label="Combined SE")
        ax.plot(sub["YEAR"], sub["wt_se_inc"] / 1e6,
                color="darkorange", linewidth=1.4, linestyle="--", marker="o", markersize=3,
                zorder=3, label="Incorporated only")

        ax.set_title(label, fontsize=9, loc="left", pad=3)
        ax.set_ylabel("Workers (millions)", fontsize=8)
        ax.tick_params(axis="both", labelsize=8)

    axes[-1].set_xticks([y for y in years if y % 2 == 0])
    axes[-1].set_xticklabels([str(y) for y in years if y % 2 == 0], fontsize=8)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, framealpha=0.9,
               bbox_to_anchor=(0.98, 0.97))
    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    return fig


def plot_se_stock_annual_share(df: pd.DataFrame) -> plt.Figure:
    """
    Annual-average SE share by age group, with two reference lines:
      - 2005–2019 mean (gray dashed)
      - 2016–2019 pre-COVID mean (olive dashed)
    Shows combined SE and incorporated-only, employed denominator only
    (cleaner for annual view; LF denominator visible in monthly chart).
    """
    full_baseline_means = {}
    pre_covid_means = {}
    for group in AGE_LABELS:
        grp_df = df[df["age_group"] == group]
        full_baseline_means[group] = (
            grp_df.loc[grp_df["YEAR"].isin(range(2005, 2020)), "se_share_employed"].mean()
        )
        pre_covid_means[group] = (
            grp_df.loc[grp_df["YEAR"].isin(range(2016, 2020)), "se_share_employed"].mean()
        )

    fig, axes = plt.subplots(
        len(AGE_LABELS), 1, figsize=(13, 17), sharex=True,
        gridspec_kw={"hspace": 0.35},
    )
    fig.suptitle(
        "Self-Employed Share of Employed Workers — Annual Average (CPS)\n"
        "Mean of monthly values  |  NaN/zero months excluded\n"
        "dashed horizontals: 2005–2019 mean (gray) and 2016–2019 pre-COVID mean (olive)",
        fontsize=10,
    )

    years = sorted(df["YEAR"].unique())

    for ax, (group, label) in zip(axes, AGE_LABELS.items()):
        sub = df[df["age_group"] == group].sort_values("YEAR").copy()

        ax.axvspan(2020, 2022 + 11/12, color="0.85", zorder=0, label="COVID era (2020–2022)")
        ax.axvline(2023 + 9/12, color="0.4", linewidth=0.8, linestyle=":", zorder=2)

        full_mean = full_baseline_means[group]
        pre_mean  = pre_covid_means[group]
        if not np.isnan(full_mean):
            ax.axhline(full_mean * 100, color="#333333", linewidth=2.0, linestyle="--",
                       zorder=1, label="2005–2019 mean")
        if not np.isnan(pre_mean):
            ax.axhline(pre_mean * 100, color="crimson", linewidth=2.0, linestyle="--",
                       zorder=1, label="2016–2019 mean (pre-COVID)")

        ax.plot(sub["YEAR"], sub["se_share_employed"] * 100,
                color="steelblue", linewidth=1.8, marker="o", markersize=4,
                zorder=3, label="Combined SE / employed")
        ax.plot(sub["YEAR"], sub["se_share_inc_employed"] * 100,
                color="darkorange", linewidth=1.4, linestyle="--", marker="o", markersize=3,
                zorder=3, label="Incorporated SE / employed")

        ax.set_title(label, fontsize=9, loc="left", pad=3)
        ax.set_ylabel("SE share (%)", fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1f}%"))
        ax.tick_params(axis="both", labelsize=8)

    axes[-1].set_xticks([y for y in years if y % 2 == 0])
    axes[-1].set_xticklabels([str(y) for y in years if y % 2 == 0], fontsize=8)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, framealpha=0.9,
               bbox_to_anchor=(0.98, 0.97))
    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    return fig


def main():
    log("Reading MOM rates...")
    mom = pd.read_parquet(PROCESSED_DIR / "rates_mom.parquet")
    log(f"  {len(mom):,} rows across {mom['age_group'].nunique()} age groups.")
    fig = plot_mom(mom)
    out = FIGURES_DIR / "entry_rates_mom.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    log("Reading YOY rates...")
    yoy = pd.read_parquet(PROCESSED_DIR / "rates_yoy.parquet")
    log(f"  {len(yoy):,} rows across {yoy['age_group'].nunique()} age groups.")
    fig = plot_yoy(yoy)
    out = FIGURES_DIR / "entry_rates_yoy.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    log("Reading MOM persistence rates...")
    mom_p = pd.read_parquet(PROCESSED_DIR / "persistence_mom.parquet")
    log(f"  {len(mom_p):,} rows across {mom_p['age_group'].nunique()} age groups.")
    fig = plot_persistence_mom(mom_p)
    out = FIGURES_DIR / "persistence_rates_mom.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    log("Reading YOY persistence rates...")
    yoy_p = pd.read_parquet(PROCESSED_DIR / "persistence_yoy.parquet")
    log(f"  {len(yoy_p):,} rows across {yoy_p['age_group'].nunique()} age groups.")
    fig = plot_persistence_yoy(yoy_p)
    out = FIGURES_DIR / "persistence_rates_yoy.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    stock_path = PROCESSED_DIR / "se_stock.parquet"
    if stock_path.exists():
        log("Reading SE stock...")
        stock_raw = pd.read_parquet(stock_path)
        stock = _prep_stock(stock_raw)
        log(f"  {len(stock):,} rows across {stock['age_group'].nunique()} age groups.")

        fig = plot_se_stock_count(stock)
        out = FIGURES_DIR / "se_stock_count.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        log(f"  Saved: {out}")
        plt.close(fig)

        fig = plot_se_stock_share(stock)
        out = FIGURES_DIR / "se_stock_share.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        log(f"  Saved: {out}")
        plt.close(fig)

        log("Plotting SE share vs unemployment scatter...")
        fig = plot_se_unemp_scatter(stock_raw)
        out = FIGURES_DIR / "se_unemp_scatter.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        log(f"  Saved: {out}")
        plt.close(fig)

        log("Computing annual stock averages...")
        annual = _compute_annual_stock(stock_raw)
        log(f"  {len(annual):,} year × age-group rows.")

        fig = plot_se_stock_annual_count(annual)
        out = FIGURES_DIR / "se_stock_annual_count.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        log(f"  Saved: {out}")
        plt.close(fig)

        fig = plot_se_stock_annual_share(annual)
        out = FIGURES_DIR / "se_stock_annual_share.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        log(f"  Saved: {out}")
        plt.close(fig)
    else:
        log("se_stock.parquet not found — skipping stock plots. Run 02_match.py first.")

    transition_path = PROCESSED_DIR / "transition_rates_quarterly.parquet"
    if transition_path.exists():
        log("Reading quarterly transition rates...")
        trans = pd.read_parquet(transition_path)
        trans["period"] = trans["quarter"].dt.to_timestamp()
        log(f"  {len(trans):,} rows across {trans['age_group'].nunique()} age groups.")
        fig = plot_transition_index(trans)
        out = FIGURES_DIR / "transition_index_quarterly.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        log(f"  Saved: {out}")
        plt.close(fig)
    else:
        log("transition_rates_quarterly.parquet not found — skipping. Run 04_analysis.py first.")


if __name__ == "__main__":
    main()
