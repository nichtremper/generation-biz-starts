"""
Robustness Check 8: March Data Gap

Some CPS years have zero or near-zero SE observations for March (likely because
the ASEC supplement displaces the basic monthly sample in some years). Annual
stock averages exclude March=0 or NaN months. This check asks: does treating
March as missing (interpolation) vs. simply excluding it change the annual
averages meaningfully?

Method:
  A. Canonical: exclude March months where se_share_employed = 0 or NaN
  B. Linear interpolation: replace those March values with the midpoint of
     Feb and Apr of the same year
  C. Carry-forward: fill March with the February value

Risk: Low-moderate. Annual averages smooth over single-month gaps.
The effect is largest when March SE levels deviate significantly from
adjacent months (unlikely but possible in recessions or post-COVID).

Reads:
  data/processed/se_stock.parquet

Outputs:
  figures/robustness/08_march_gap.png
"""

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
FIGURES_DIR   = Path(__file__).parent.parent.parent / "figures" / "robustness"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

AGE_FOCUS    = "20_to_34"
COVID_START  = pd.Timestamp("2020-01-01")
COVID_END    = pd.Timestamp("2022-12-31")
RECENT_START = pd.Timestamp("2023-10-01")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def prep_monthly(df, age_group):
    sub = df[df["age_group"] == age_group].copy()
    sub["period"] = pd.to_datetime(
        sub["YEAR"].astype(str) + "-" + sub["MONTH"].astype(str).str.zfill(2)
    )
    sub = sub.sort_values("period").set_index("period")
    sub["share_raw"] = sub["se_share_employed"]
    # Mark March zeros/NaN as gap
    sub["is_march_gap"] = (sub.index.month == 3) & (sub["share_raw"].fillna(0) == 0)
    return sub


def annual_mean_exclude(df):
    """Canonical: exclude months where share_raw == 0 or NaN."""
    df2 = df[df["share_raw"] > 0].copy()
    df2["year"] = df2.index.year
    return df2.groupby("year")["share_raw"].mean()


def annual_mean_interpolate(df):
    """Interpolate March gap months linearly from Feb/Apr."""
    df2 = df.copy()
    df2.loc[df2["is_march_gap"], "share_raw"] = np.nan
    df2["share_interp"] = df2["share_raw"].interpolate(method="time")
    df2["year"] = df2.index.year
    return df2.groupby("year")["share_interp"].mean()


def annual_mean_carry_forward(df):
    """Fill March gap with previous February value."""
    df2 = df.copy()
    df2.loc[df2["is_march_gap"], "share_raw"] = np.nan
    df2["share_cf"] = df2["share_raw"].fillna(method="ffill")
    df2["year"] = df2.index.year
    return df2.groupby("year")["share_cf"].mean()


def main():
    log("Reading SE stock...")
    stock = pd.read_parquet(PROCESSED_DIR / "se_stock.parquet")

    log(f"Processing age group: {AGE_FOCUS}...")
    sub = prep_monthly(stock, AGE_FOCUS)

    n_gaps = sub["is_march_gap"].sum()
    gap_years = sub[sub["is_march_gap"]].index.year.tolist()
    log(f"  Found {n_gaps} March gap months in years: {gap_years}")

    ann_excl   = annual_mean_exclude(sub)
    ann_interp = annual_mean_interpolate(sub)
    ann_cf     = annual_mean_carry_forward(sub)

    # Align years
    years = sorted(set(ann_excl.index) & set(ann_interp.index) & set(ann_cf.index))
    excl   = ann_excl.reindex(years)
    interp = ann_interp.reindex(years)
    cf     = ann_cf.reindex(years)

    diff_interp = (interp - excl) * 100
    diff_cf     = (cf - excl) * 100

    # --- Plot ---
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={"hspace": 0.45})
    fig.suptitle(
        f"March Data Gap Sensitivity — {AGE_FOCUS} SE Share (Annual)\n"
        "Top: annual SE share under three March treatments  |  Bottom: difference from canonical",
        fontsize=10,
    )

    ax = axes[0]
    ax.axvspan(COVID_START.year, COVID_END.year + 1, color="0.88", zorder=0, alpha=0.5)
    ax.plot(years, excl   * 100, "o-", color="#2a6496", linewidth=1.8, markersize=4,
            label="Canonical (exclude March gaps)")
    ax.plot(years, interp * 100, "s--", color="#e67e22", linewidth=1.4, markersize=4,
            label="Linear interpolation")
    ax.plot(years, cf     * 100, "^:", color="#27ae60", linewidth=1.4, markersize=4,
            label="Carry-forward (Feb → Mar)")
    # Mark gap years
    for yr in gap_years:
        if yr in years:
            ax.axvline(yr, color="0.6", linewidth=0.7, linestyle="--", zorder=0)
    ax.set_ylabel("Annual SE share / employed (%)", fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
    ax.legend(fontsize=8, framealpha=0.9)
    ax.tick_params(labelsize=8)

    ax = axes[1]
    ax.axhline(0, color="0.5", linewidth=0.8)
    ax.bar([y - 0.2 for y in years], diff_interp, 0.35, color="#e67e22", alpha=0.8,
           label="Interpolation − canonical")
    ax.bar([y + 0.2 for y in years], diff_cf, 0.35, color="#27ae60", alpha=0.8,
           label="Carry-forward − canonical")
    ax.set_ylabel("Difference from canonical (pp)", fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.3f}pp"))
    ax.legend(fontsize=8, framealpha=0.9)
    ax.tick_params(labelsize=8)
    ax.set_xlabel("Year", fontsize=8)

    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    out = FIGURES_DIR / "08_march_gap.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    # Summary
    log(f"\nSummary — max absolute difference from canonical (pp):")
    print(f"  Interpolation: {diff_interp.abs().max():.4f} pp")
    print(f"  Carry-forward: {diff_cf.abs().max():.4f} pp")
    log("Done.")


if __name__ == "__main__":
    main()
