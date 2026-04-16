"""
Robustness Check 3: Age Cutoff Sensitivity

The canonical "young adult" group is 20–34. This check tests alternative
upper bounds: 20–29, 20–34 (canonical), 20–39.

Also tests a lower-bound variant: 18–34 (includes 18–19 year olds who may
be starting businesses but are often excluded due to school enrollment).

Risk: Moderate. The 20–34 cut follows Kauffman exactly. Including 35–39
(professionals in prime career-building years) could dilute or amplify the
signal. The 20–29 cut isolates Gen Z vs. older millennials.

Reads:
  data/processed/matched_mom.parquet
  data/processed/matched_yoy.parquet

Outputs:
  figures/robustness/03_age_cutoff_sensitivity.png
"""

from datetime import datetime
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.rates import BASELINE_YEARS, _entry_rate

PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
FIGURES_DIR   = Path(__file__).parent.parent.parent / "figures" / "robustness"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

COVID_START  = pd.Timestamp("2020-01-01")
COVID_END    = pd.Timestamp("2022-12-31")
RECENT_START = pd.Timestamp("2023-10-01")

CUTOFFS = {
    "20–29": (20, 29),
    "20–34 (canonical)": (20, 34),
    "20–39": (20, 39),
    "18–34": (18, 34),
}
COLORS = ["#e67e22", "#2a6496", "#27ae60", "#c0392b"]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def compute_yoy_rates_for_group(df, age_min, age_max):
    df = df.copy()
    if "LNKFW1YWT_t1" in df.columns:
        df["weight"] = df["LNKFW1YWT_t1"].where(df["LNKFW1YWT_t1"] > 0, df["WTFINL_t0"])
    else:
        df["weight"] = df["WTFINL_t0"]

    df["quarter"] = pd.PeriodIndex(
        pd.to_datetime(
            df["YEAR_t1"].astype(str) + "-" + df["MONTH_t1"].astype(str).str.zfill(2)
        ), freq="Q",
    )

    subset = df[df["AGE_t0"].between(age_min, age_max)]
    records = []
    for quarter, grp in subset.groupby("quarter"):
        rate = _entry_rate(grp, "new_entrant", "at_risk", "weight")
        records.append({"quarter": quarter, "entry_rate": rate,
                        "n_at_risk": int(grp["at_risk"].sum())})
    return pd.DataFrame(records).sort_values("quarter")


def baseline_mean_by_quarter(df, year_lo=2005, year_hi=2019):
    bl = df[df["quarter"].dt.year.between(year_lo, year_hi)].copy()
    bl["season"] = bl["quarter"].dt.quarter
    return bl.groupby("season")["entry_rate"].mean()


def main():
    log("Reading YOY matched pairs (this may take a moment)...")
    yoy = pd.read_parquet(PROCESSED_DIR / "matched_yoy.parquet")
    log(f"  Loaded {len(yoy):,} pairs.")

    all_rates = {}
    for label, (age_min, age_max) in CUTOFFS.items():
        log(f"  Computing rates for {label}...")
        all_rates[label] = compute_yoy_rates_for_group(yoy, age_min, age_max)

    # --- Plot ---
    fig, axes = plt.subplots(2, 1, figsize=(13, 10), gridspec_kw={"hspace": 0.4})
    fig.suptitle(
        "YOY SE Entry Rate — Age Cutoff Sensitivity\n"
        "Top: raw rates  |  Bottom: each rate indexed to its own 2005–2019 mean = 100",
        fontsize=11,
    )

    # Panel 1: raw rates
    ax = axes[0]
    ax.axvspan(COVID_START, COVID_END, color="0.88", zorder=0)
    ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)
    for (label, rates), color in zip(all_rates.items(), COLORS):
        dates = rates["quarter"].dt.to_timestamp()
        ax.plot(dates, rates["entry_rate"] * 100,
                color=color, linewidth=1.6, marker="o", markersize=3,
                label=label)
    ax.set_ylabel("Entry rate (%)", fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
    ax.legend(fontsize=8, framealpha=0.9)
    ax.tick_params(labelsize=8)

    # Panel 2: indexed to own baseline mean
    ax = axes[1]
    ax.axvspan(COVID_START, COVID_END, color="0.88", zorder=0)
    ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)
    ax.axhline(100, color="0.5", linewidth=0.8, zorder=1)
    for (label, rates), color in zip(all_rates.items(), COLORS):
        bl_means = baseline_mean_by_quarter(rates)
        rates2 = rates.copy()
        rates2["season"] = rates2["quarter"].dt.quarter
        rates2["bl_mean"] = rates2["season"].map(bl_means)
        rates2["idx"] = rates2["entry_rate"] / rates2["bl_mean"] * 100
        dates = rates2["quarter"].dt.to_timestamp()
        ax.plot(dates, rates2["idx"],
                color=color, linewidth=1.6, marker="o", markersize=3,
                label=label)
    ax.set_ylabel("Index (own 2005–2019 mean = 100)", fontsize=8)
    ax.legend(fontsize=8, framealpha=0.9)
    ax.tick_params(labelsize=8)

    for ax in axes:
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    out = FIGURES_DIR / "03_age_cutoff_sensitivity.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    # Summary table
    log("\nSummary — recent period mean entry rate by age cutoff:")
    for label, rates in all_rates.items():
        recent = rates[rates["quarter"] >= pd.Period("2023Q4", freq="Q")]
        bl_means = baseline_mean_by_quarter(rates)
        recent2 = recent.copy()
        recent2["season"] = recent2["quarter"].dt.quarter
        recent2["bl_mean"] = recent2["season"].map(bl_means)
        recent2["pct_above"] = (recent2["entry_rate"] - recent2["bl_mean"]) / recent2["bl_mean"] * 100
        mean_rate = recent["entry_rate"].mean() * 100
        mean_pct = recent2["pct_above"].mean()
        print(f"  {label:25s}: mean={mean_rate:.3f}%  vs baseline: {mean_pct:+.1f}%")

    log("Done.")


if __name__ == "__main__":
    main()
