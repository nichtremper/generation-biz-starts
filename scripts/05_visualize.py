"""
Step 5: Time-series plots of SE entry rates with 95% confidence intervals.

Reads:
  data/processed/rates_mom.parquet
  data/processed/rates_yoy.parquet

Saves to:
  figures/entry_rates_mom.png
  figures/entry_rates_yoy.png

CI method: normal approximation using unweighted n_at_risk as the effective
sample size. Does not correct for survey design effects; treat bands as
indicative, not formal.
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
    "35_and_under": "Age 20–35",
    "36_to_50":     "Age 36–50",
    "51_plus":      "Age 51–64",
}

Z95 = 1.96


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def ci_bounds(rate: pd.Series, n: pd.Series):
    """Return (lower, upper) 95% CI series for a binomial proportion."""
    se = np.sqrt(rate * (1 - rate) / n.clip(lower=1))
    return (rate - Z95 * se).clip(lower=0), rate + Z95 * se


def shade_background(ax, x_start, x_end):
    """Gray band for COVID era."""
    ax.axvspan(x_start, x_end, color="0.85", zorder=0, label="COVID era (2020–2022)")


def plot_mom(df: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(
        len(AGE_LABELS), 1, figsize=(13, 11), sharex=True, sharey=True,
        gridspec_kw={"hspace": 0.35},
    )
    fig.suptitle(
        "Self-Employment Entry Rate — Month-Over-Month (CPS)\n"
        "3-month rolling average  |  shaded band = 95% CI on monthly estimate",
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

    return fig


def plot_yoy(df: pd.DataFrame) -> plt.Figure:
    # Convert Period to timestamp for matplotlib
    df = df.copy()
    df["date"] = df["quarter"].dt.to_timestamp()

    fig, axes = plt.subplots(
        len(AGE_LABELS), 1, figsize=(13, 11), sharex=True, sharey=True,
        gridspec_kw={"hspace": 0.35},
    )
    fig.suptitle(
        "Self-Employment Entry Rate — Year-Over-Year (CPS, MISH 4→8)\n"
        "Quarterly  |  shaded band = 95% CI",
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


if __name__ == "__main__":
    main()
