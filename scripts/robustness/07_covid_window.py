"""
Robustness Check 7: COVID Exclusion Window Sensitivity

The canonical baseline excludes 2020–2022 from the reference period. But
the "right" COVID window is debatable:
  A. 2020–2021 — exclude only the acute phase; 2022 is "recovery"
  B. 2020–2022 (canonical) — full three-year exclusion
  C. 2020–2023 — include 2022–2023 as part of the disruption

This affects z-score tests: if recent elevated rates were also elevated in
2022–2023 (which a broader COVID window includes), excluding 2022–2023 from
baseline means fewer baseline quarters that "look like" the recent period,
making recent z-scores appear more extreme.

Also tests: what does the recent period look like relative to a baseline that
DOES include COVID years (i.e., no exclusion at all)?

Risk: Moderate. Findings about "above baseline" depend on which years are
excluded. COVID exclusion is standard practice but the endpoint is judgment.

Reads:
  data/processed/rates_yoy.parquet

Outputs:
  figures/robustness/07_covid_window.png
"""

from datetime import datetime
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
FIGURES_DIR   = Path(__file__).parent.parent.parent / "figures" / "robustness"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

AGE_FOCUS    = "20_to_34"
RECENT_START = pd.Period("2023Q4", freq="Q")

# (label, baseline_years_lo, baseline_years_hi, covid_exclude_lo, covid_exclude_hi)
WINDOWS = {
    "No COVID exclusion\n(2005–2019 + 2020–present)": (2005, 2025, None,  None),
    "Exclude 2020–2021":                               (2005, 2019, 2020, 2021),
    "Exclude 2020–2022 (canonical)":                   (2005, 2019, 2020, 2022),
    "Exclude 2020–2023":                               (2005, 2019, 2020, 2023),
}
COLORS = ["#c0392b", "#e67e22", "#2a6496", "#27ae60"]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def compute_zscores(rates, bl_lo, bl_hi, excl_lo, excl_hi):
    """
    For each (age_group, quarter), compute z-score relative to the baseline
    defined by [bl_lo, bl_hi] minus the excluded range [excl_lo, excl_hi].
    """
    df = rates.copy()
    df["season"] = df["quarter"].dt.quarter
    df["year"]   = df["quarter"].dt.year

    # Build baseline mask
    bl_mask = df["year"].between(bl_lo, bl_hi)
    if excl_lo is not None:
        bl_mask &= ~df["year"].between(excl_lo, excl_hi)

    bl_stats = (
        df[bl_mask]
        .groupby(["age_group", "season"])["entry_rate"]
        .agg(bl_mean="mean", bl_sd="std")
        .reset_index()
    )
    df = df.merge(bl_stats, on=["age_group", "season"], how="left")
    df["z"] = (df["entry_rate"] - df["bl_mean"]) / df["bl_sd"].replace(0, np.nan)
    return df


def main():
    log("Reading YOY rates...")
    rates = pd.read_parquet(PROCESSED_DIR / "rates_yoy.parquet")
    rates["date"] = rates["quarter"].dt.to_timestamp()

    sub_all = {}
    for label, (bl_lo, bl_hi, ex_lo, ex_hi) in WINDOWS.items():
        sub_all[label] = compute_zscores(
            rates[rates["age_group"] == AGE_FOCUS],
            bl_lo, bl_hi, ex_lo, ex_hi,
        )

    # --- Figure ---
    fig, axes = plt.subplots(2, 1, figsize=(13, 10), gridspec_kw={"hspace": 0.45})
    fig.suptitle(
        f"COVID Exclusion Window Sensitivity — {AGE_FOCUS} YOY Entry Rate\n"
        "Top: z-scores under each window  |  Bottom: z-scores in recent period (2023Q4+)",
        fontsize=10,
    )

    # Panel 1: z-score time series
    ax = axes[0]
    ax.axhline(0,  color="0.5", linewidth=0.8, zorder=1)
    ax.axhline(1,  color="0.5", linewidth=0.8, linestyle=":", zorder=1)
    ax.axhline(-1, color="0.5", linewidth=0.8, linestyle=":", zorder=1)
    ax.axvline(pd.Timestamp("2023-10-01"), color="0.4", linewidth=0.8,
               linestyle=":", zorder=2)

    for (label, df), color in zip(sub_all.items(), COLORS):
        df_sorted = df.sort_values("date")
        ax.plot(df_sorted["date"], df_sorted["z"],
                color=color, linewidth=1.4, marker="o", markersize=2.5,
                label=label.replace("\n", " "), alpha=0.85)

    ax.set_ylabel("Z-score (vs. seasonal mean)", fontsize=8)
    ax.legend(fontsize=7.5, framealpha=0.9, loc="upper left")
    ax.tick_params(labelsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # Panel 2: recent z-scores as grouped bars
    ax = axes[1]
    recent_quarters = sorted(
        sub_all["Exclude 2020–2022 (canonical)"]
        .loc[sub_all["Exclude 2020–2022 (canonical)"]["quarter"] >= RECENT_START, "quarter"]
        .unique()
    )
    x = np.arange(len(recent_quarters))
    width = 0.18

    for i, ((label, df), color) in enumerate(zip(sub_all.items(), COLORS)):
        zvals = []
        for q in recent_quarters:
            row = df[df["quarter"] == q]
            zvals.append(row["z"].values[0] if len(row) > 0 else np.nan)
        ax.bar(x + i * width, zvals, width, color=color, alpha=0.85,
               label=label.replace("\n", " "))

    ax.axhline(1,  color="0.4", linewidth=0.8, linestyle=":", zorder=3)
    ax.axhline(-1, color="0.4", linewidth=0.8, linestyle=":", zorder=3)
    ax.axhline(0,  color="0.5", linewidth=0.8, zorder=3)
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels([str(q) for q in recent_quarters],
                       rotation=45, ha="right", fontsize=7.5)
    ax.set_ylabel("Z-score (vs. seasonal mean)", fontsize=8)
    ax.legend(fontsize=7.5, framealpha=0.9)
    ax.tick_params(labelsize=8)

    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    out = FIGURES_DIR / "07_covid_window.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    # Summary
    log("\nSummary — mean z-score in recent period (2023Q4+) by exclusion window:")
    for label, df in sub_all.items():
        recent = df[df["quarter"] >= RECENT_START]
        mean_z = recent["z"].mean()
        n_above = (recent["z"] > 1).sum()
        print(f"  {label.replace(chr(10), ' '):45s}  mean_z={mean_z:+.2f}  "
              f"quarters_above_1SD={n_above}/{len(recent)}")

    log("Done.")


if __name__ == "__main__":
    main()
