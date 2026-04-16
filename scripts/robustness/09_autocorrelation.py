"""
Robustness Check 9: Autocorrelation-Corrected Inference

The canonical z-scores treat historical entry rates as i.i.d. observations.
But time-series data (quarterly rates) exhibit positive autocorrelation —
which inflates test statistics when we compare recent quarters to a baseline
mean. A Newey-West HAC correction accounts for this.

Method:
  1. Estimate AR(1) coefficient ρ̂ for baseline entry rates (2005–2019).
  2. Compute Newey-West variance correction:
       Var_NW = Var_OLS × (1 + 2 × Σ_{k=1}^{L} (1−k/(L+1)) × ρ̂ᵏ)
     where L = floor(T^(1/3)) (Newey-West bandwidth).
  3. Recompute z-scores using the NW-corrected SD.
  4. Compare which "above baseline" flags survive the correction.

Risk: High. Positive autocorrelation in quarterly rates means the naive
z-score overstates precision. A correction of 1.2–1.5× the SD is typical
for highly persistent series. Claims that recent quarters are "significantly
above baseline" may weaken.

Reads:
  data/processed/rates_yoy.parquet

Outputs:
  figures/robustness/09_autocorrelation.png
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

AGE_GROUPS   = ["20_to_34", "20_to_64"]
BASELINE_LO  = 2005
BASELINE_HI  = 2019
RECENT_START = pd.Period("2023Q4", freq="Q")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def newey_west_var(series, bandwidth=None):
    """
    Newey-West heteroskedasticity and autocorrelation-consistent variance
    estimate for the mean of `series`.

    Var_NW = (1/T²) × [T × S_0 + 2 × Σ_{k=1}^{L} (1-k/(L+1)) × T × S_k]
    where S_k = (1/T) Σ e_t × e_{t-k},  e_t = x_t - x̄

    Equivalent to Var_NW(mean) = Var_OLS(mean) × NW_factor
    where NW_factor accounts for autocorrelation.
    """
    x = np.asarray(series, dtype=float)
    x = x[~np.isnan(x)]
    T = len(x)
    if T < 4:
        return np.var(x, ddof=1) / T  # fall back

    if bandwidth is None:
        bandwidth = int(np.floor(T ** (1 / 3)))

    e = x - x.mean()
    s0 = np.dot(e, e) / T
    nw_sum = s0
    for k in range(1, bandwidth + 1):
        sk = np.dot(e[k:], e[:-k]) / T
        weight = 1.0 - k / (bandwidth + 1)
        nw_sum += 2 * weight * sk

    # Var(mean) = nw_sum / T
    return nw_sum / T


def compute_zscores_naive_and_nw(rates, age_group):
    df = rates[rates["age_group"] == age_group].copy()
    df["year"]   = df["quarter"].dt.year
    df["season"] = df["quarter"].dt.quarter

    bl = df[df["year"].between(BASELINE_LO, BASELINE_HI)]

    records = []
    for season in [1, 2, 3, 4]:
        bl_season = bl[bl["season"] == season]["entry_rate"]
        if len(bl_season) < 4:
            continue

        T = len(bl_season)
        bl_mean = bl_season.mean()
        bl_var_naive = bl_season.var(ddof=1) / T  # Var(mean), iid assumption
        bl_var_nw    = newey_west_var(bl_season)

        # AR1 for reporting
        x = bl_season.values
        if len(x) > 2:
            rho = np.corrcoef(x[:-1], x[1:])[0, 1]
        else:
            rho = np.nan

        # Full series
        season_df = df[df["season"] == season].sort_values("quarter")
        for _, row in season_df.iterrows():
            z_naive = (row["entry_rate"] - bl_mean) / np.sqrt(max(bl_var_naive, 1e-12))
            z_nw    = (row["entry_rate"] - bl_mean) / np.sqrt(max(bl_var_nw,    1e-12))
            records.append({
                "quarter":   row["quarter"],
                "year":      row["year"],
                "season":    season,
                "entry_rate": row["entry_rate"],
                "bl_mean":   bl_mean,
                "z_naive":   z_naive,
                "z_nw":      z_nw,
                "nw_factor": np.sqrt(bl_var_nw / max(bl_var_naive, 1e-12)),
                "rho":       rho,
            })

    return pd.DataFrame(records).sort_values("quarter")


def main():
    log("Reading YOY rates...")
    rates = pd.read_parquet(PROCESSED_DIR / "rates_yoy.parquet")

    fig, axes = plt.subplots(len(AGE_GROUPS), 2, figsize=(14, 9),
                             gridspec_kw={"hspace": 0.45, "wspace": 0.32})
    fig.suptitle(
        "Autocorrelation-Corrected Z-scores — YOY SE Entry Rate\n"
        "Left: z-score series (naive vs. Newey-West)  |  "
        "Right: NW correction factor = NW SD / naive SD",
        fontsize=10,
    )

    for row, group in enumerate(AGE_GROUPS):
        log(f"  Computing for {group}...")
        df = compute_zscores_naive_and_nw(rates, group)

        # AR1 summary (avg across seasons)
        mean_rho = df["rho"].mean()
        mean_nw  = df["nw_factor"].mean()
        log(f"    Mean AR(1) ρ̂ = {mean_rho:.3f}  |  "
            f"Mean NW inflation factor = {mean_nw:.3f}×")

        dates = df["quarter"].dt.to_timestamp()

        # Left: z-score series
        ax = axes[row, 0]
        ax.axhline(0,  color="0.5", linewidth=0.8, zorder=1)
        ax.axhline(1,  color="0.6", linewidth=0.7, linestyle=":", zorder=1)
        ax.axhline(-1, color="0.6", linewidth=0.7, linestyle=":", zorder=1)
        ax.axvline(pd.Timestamp("2023-10-01"), color="0.4", linewidth=0.8,
                   linestyle=":", zorder=2)
        ax.plot(dates, df["z_naive"],
                color="#2a6496", linewidth=1.6, marker="o", markersize=2.5,
                label="Naive z (iid)")
        ax.plot(dates, df["z_nw"],
                color="#c0392b", linewidth=1.6, linestyle="--", marker="o", markersize=2.5,
                label=f"Newey-West z  (mean ρ̂={mean_rho:.2f})")
        ax.set_title(f"{group} — z-scores", fontsize=9)
        ax.set_ylabel("Z-score", fontsize=8)
        ax.legend(fontsize=7.5, framealpha=0.9)
        ax.tick_params(labelsize=8)
        ax.xaxis.set_major_locator(mdates.YearLocator(4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

        # Right: NW factor over time (per-quarter)
        ax = axes[row, 1]
        ax.axhline(1.0, color="0.5", linewidth=0.8, zorder=1)
        ax.axvline(pd.Timestamp("2023-10-01"), color="0.4", linewidth=0.8,
                   linestyle=":", zorder=2)
        ax.plot(dates, df["nw_factor"],
                color="#e67e22", linewidth=1.6, marker="o", markersize=2.5)
        ax.fill_between(dates, 1.0, df["nw_factor"], alpha=0.15, color="#e67e22")
        ax.set_title(f"{group} — NW correction factor", fontsize=9)
        ax.set_ylabel("Factor (NW SD / naive SD)", fontsize=8)
        ax.tick_params(labelsize=8)
        ax.xaxis.set_major_locator(mdates.YearLocator(4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    out = FIGURES_DIR / "09_autocorrelation.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    # Summary: recent period
    log("\nSummary — recent period (2023Q4+) z-scores by group:")
    for group in AGE_GROUPS:
        df = compute_zscores_naive_and_nw(rates, group)
        recent = df[df["quarter"] >= RECENT_START]
        n_above_naive = (recent["z_naive"] > 1).sum()
        n_above_nw    = (recent["z_nw"]    > 1).sum()
        mean_nw = recent["nw_factor"].mean()
        print(f"  {group:12s}: naive above_1SD={n_above_naive}/{len(recent)}  "
              f"NW above_1SD={n_above_nw}/{len(recent)}  "
              f"mean_NW_factor={mean_nw:.2f}×")

    log("Done.")


if __name__ == "__main__":
    main()
