"""
Robustness Check 1: Baseline Period Sensitivity

The canonical baseline is 2005–2019. This check compares four baseline windows:
  A. 2005–2019 (canonical) — full pre-COVID history
  B. 2010–2019 — excludes Great Recession and recovery distortion
  C. 2015–2019 — tight pre-COVID window only
  D. 2016–2019 — immediate pre-COVID (matches reference line in main charts)

Risk: High. Findings about "above baseline" depend on which baseline is used.
The 2005-2019 baseline includes post-dot-com decline years that pull the mean up,
making the recent period look less exceptional. A tighter baseline (2016-2019)
makes the post-COVID recovery look more pronounced.

Reads:
  data/processed/rates_yoy.parquet
  data/processed/se_stock.parquet

Outputs:
  figures/robustness/01_baseline_sensitivity_yoy.png
  figures/robustness/01_baseline_sensitivity_stock.png
"""

from datetime import datetime
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.rates import BASELINE_YEARS

PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
FIGURES_DIR   = Path(__file__).parent.parent.parent / "figures" / "robustness"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

COVID_START  = pd.Timestamp("2020-01-01")
COVID_END    = pd.Timestamp("2022-12-31")
RECENT_START = pd.Timestamp("2023-10-01")

BASELINES = {
    "2005–2019 (canonical)": (2005, 2019, "#2a6496"),
    "2010–2019":              (2010, 2019, "#e67e22"),
    "2015–2019":              (2015, 2019, "#27ae60"),
    "2016–2019 (pre-COVID)":  (2016, 2019, "#c0392b"),
}

AGE_GROUPS = ["20_to_34", "35_to_44", "45_to_54", "55_to_64", "20_to_64"]
AGE_LABELS = {
    "20_to_34": "Age 20–34",
    "35_to_44": "Age 35–44",
    "45_to_54": "Age 45–54",
    "55_to_64": "Age 55–64",
    "20_to_64": "Age 20–64 (all)",
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _baseline_mean(rates, period_col, rate_col, year_lo, year_hi):
    """Return per-(age_group, season) mean for a given year window."""
    if period_col == "period":
        bl = rates[rates[period_col].dt.year.between(year_lo, year_hi)].copy()
        bl["season"] = bl[period_col].dt.month
    else:
        bl = rates[rates[period_col].dt.year.between(year_lo, year_hi)].copy()
        bl["season"] = bl[period_col].dt.quarter
    return bl.groupby(["age_group", "season"])[rate_col].mean().reset_index(
        name="baseline_mean"
    )


def plot_yoy_baseline_sensitivity(df):
    df = df.copy()
    df["date"] = df["quarter"].dt.to_timestamp()

    fig, axes = plt.subplots(len(AGE_GROUPS), 1, figsize=(13, 17), sharex=True,
                             gridspec_kw={"hspace": 0.40})
    fig.suptitle(
        "YOY SE Entry Rate — Baseline Period Sensitivity (age 20–34 focus)\n"
        "Horizontal lines = seasonal mean under each baseline window",
        fontsize=11,
    )

    for ax, group in zip(axes, AGE_GROUPS):
        sub = df[df["age_group"] == group].sort_values("date").copy()
        sub["season"] = sub["quarter"].dt.quarter

        ax.axvspan(COVID_START, COVID_END, color="0.88", zorder=0)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)

        ax.plot(sub["date"], sub["entry_rate"] * 100,
                color="steelblue", linewidth=1.6, marker="o", markersize=3,
                zorder=3, label="Entry rate")

        for label, (yr_lo, yr_hi, color) in BASELINES.items():
            bl = _baseline_mean(df, "quarter", "entry_rate", yr_lo, yr_hi)
            sub_bl = sub.merge(bl, on=["age_group", "season"], how="left")
            # Plot as step-function through time
            ax.plot(sub_bl["date"], sub_bl["baseline_mean"] * 100,
                    color=color, linewidth=1.2, linestyle="--", zorder=2,
                    alpha=0.85, label=f"Mean {label}")

        ax.set_title(AGE_LABELS[group], fontsize=9, loc="left", pad=3)
        ax.set_ylabel("Entry rate (%)", fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
        ax.tick_params(axis="both", labelsize=8)

    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=7.5, framealpha=0.9,
               bbox_to_anchor=(0.98, 0.97))
    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")
    return fig


def plot_stock_baseline_sensitivity(df):
    df = df.copy()
    df["period"] = pd.to_datetime(
        df["YEAR"].astype(str) + "-" + df["MONTH"].astype(str).str.zfill(2)
    )

    fig, axes = plt.subplots(len(AGE_GROUPS), 1, figsize=(13, 17), sharex=True,
                             gridspec_kw={"hspace": 0.40})
    fig.suptitle(
        "SE Stock Share — Baseline Period Sensitivity\n"
        "Horizontal lines = monthly mean under each baseline window",
        fontsize=11,
    )

    for ax, group in zip(axes, AGE_GROUPS):
        sub = df[df["age_group"] == group].sort_values("period").copy()
        sub["season"] = sub["period"].dt.month
        sub_clean = sub[sub["se_share_employed"] > 0]

        ax.axvspan(COVID_START, COVID_END, color="0.88", zorder=0)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)

        ax.plot(sub_clean["period"], sub_clean["se_share_employed"] * 100,
                color="steelblue", linewidth=1.4, alpha=0.6, zorder=3,
                label="SE share / employed")

        for label, (yr_lo, yr_hi, color) in BASELINES.items():
            bl = _baseline_mean(df, "period", "se_share_employed", yr_lo, yr_hi)
            sub_bl = sub.merge(bl, on=["age_group", "season"], how="left")
            sub_bl = sub_bl[sub_bl["se_share_employed"] > 0]
            ax.plot(sub_bl["period"], sub_bl["baseline_mean"] * 100,
                    color=color, linewidth=1.2, linestyle="--", zorder=2,
                    alpha=0.85, label=f"Mean {label}")

        ax.set_title(AGE_LABELS[group], fontsize=9, loc="left", pad=3)
        ax.set_ylabel("SE share (%)", fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1f}%"))
        ax.tick_params(axis="both", labelsize=8)

    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=7.5, framealpha=0.9,
               bbox_to_anchor=(0.98, 0.97))
    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")
    return fig


def main():
    log("Reading YOY rates...")
    yoy = pd.read_parquet(PROCESSED_DIR / "rates_yoy.parquet")

    log("Plotting YOY baseline sensitivity...")
    fig = plot_yoy_baseline_sensitivity(yoy)
    out = FIGURES_DIR / "01_baseline_sensitivity_yoy.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    log("Reading SE stock...")
    stock = pd.read_parquet(PROCESSED_DIR / "se_stock.parquet")

    log("Plotting stock baseline sensitivity...")
    fig = plot_stock_baseline_sensitivity(stock)
    out = FIGURES_DIR / "01_baseline_sensitivity_stock.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    # Print summary table for 20-34
    log("\nSummary — 20–34 YOY entry rate means by baseline window:")
    yoy_34 = yoy[yoy["age_group"] == "20_to_34"].copy()
    yoy_34["season"] = yoy_34["quarter"].dt.quarter
    for label, (yr_lo, yr_hi, _) in BASELINES.items():
        bl = _baseline_mean(yoy, "quarter", "entry_rate", yr_lo, yr_hi)
        mean_val = bl[bl["age_group"] == "20_to_34"]["baseline_mean"].mean()
        print(f"  {label:30s}: {mean_val*100:.3f}%")

    log("Done.")


if __name__ == "__main__":
    main()
