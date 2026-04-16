"""
Robustness Check 2: Design Effect (DEFF) Sensitivity

The canonical CI uses DEFF = 1.5. CPS documentation suggests DEFF typically
ranges from 1.5 to 2.0 for employment variables; SE status likely runs higher.
A scalar DEFF is a rough approximation — true DEFF varies by year, geography,
and variable. This check tests DEFF ∈ {1.0, 1.5, 2.0, 2.5}.

Risk: Moderate. CIs widen proportionally to sqrt(DEFF). Going from 1.5 to 2.5
widens CIs by ~29%. The headline findings (trends, stock levels, transition
pathways) are unaffected; only the precision claims change.

Reads:
  data/processed/rates_yoy.parquet
  data/processed/se_stock.parquet

Outputs:
  figures/robustness/02_deff_sensitivity.png
"""

from datetime import datetime
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
FIGURES_DIR   = Path(__file__).parent.parent.parent / "figures" / "robustness"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

DEFFS   = [1.0, 1.5, 2.0, 2.5]
COLORS  = ["#27ae60", "#2a6496", "#e67e22", "#c0392b"]
Z95     = 1.96
RECENT_START = pd.Period("2023Q4", freq="Q")

AGE_FOCUS = "20_to_34"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def ci_half_width(rate, n, deff):
    se = np.sqrt(deff * rate * (1 - rate) / np.maximum(n, 1))
    return Z95 * se


def main():
    log("Reading YOY rates...")
    yoy = pd.read_parquet(PROCESSED_DIR / "rates_yoy.parquet")
    yoy["date"] = yoy["quarter"].dt.to_timestamp()

    sub = yoy[yoy["age_group"] == AGE_FOCUS].sort_values("quarter").copy()
    recent = sub[sub["quarter"] >= RECENT_START].copy()

    # --- Figure: CI width across DEFF values for recent quarters ---
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        f"Design Effect Sensitivity — {AGE_FOCUS} YOY Entry Rate\n"
        f"Left: full series CI bands under each DEFF | Right: recent quarters CI half-width",
        fontsize=10,
    )

    ax = axes[0]
    ax.set_title("Full series — CI bands by DEFF", fontsize=9)
    ax.plot(sub["date"], sub["entry_rate"] * 100,
            color="black", linewidth=1.8, zorder=5, label="Entry rate")

    for deff, color in zip(DEFFS, COLORS):
        hw = ci_half_width(sub["entry_rate"], sub["n_at_risk"], deff)
        lo = (sub["entry_rate"] - hw).clip(lower=0) * 100
        hi = (sub["entry_rate"] + hw) * 100
        ax.fill_between(sub["date"], lo, hi, alpha=0.18, color=color,
                        label=f"DEFF={deff}")

    ax.set_ylabel("Entry rate (%)", fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7.5, framealpha=0.9)

    ax = axes[1]
    ax.set_title("Recent quarters — 95% CI half-width by DEFF", fontsize=9)
    x = np.arange(len(recent))
    width = 0.18
    for i, (deff, color) in enumerate(zip(DEFFS, COLORS)):
        hw = ci_half_width(recent["entry_rate"], recent["n_at_risk"], deff) * 100
        ax.bar(x + i * width, hw, width, color=color, alpha=0.85,
               label=f"DEFF={deff}")

    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(
        [str(q) for q in recent["quarter"].values], rotation=45, ha="right", fontsize=7.5
    )
    ax.set_ylabel("95% CI half-width (pp)", fontsize=8)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7.5, framealpha=0.9)

    plt.tight_layout()
    out = FIGURES_DIR / "02_deff_sensitivity.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    # Summary table
    log("\nSummary — CI half-width (pp) for most recent quarter under each DEFF:")
    last = recent.iloc[-1]
    print(f"  Quarter: {last['quarter']}  |  Entry rate: {last['entry_rate']*100:.3f}%"
          f"  |  n_at_risk: {last['n_at_risk']:,}")
    for deff in DEFFS:
        hw = ci_half_width(last["entry_rate"], last["n_at_risk"], deff) * 100
        print(f"  DEFF={deff}: ±{hw:.4f} pp  "
              f"[{(last['entry_rate'] - hw/100)*100:.3f}%, {(last['entry_rate'] + hw/100)*100:.3f}%]")

    log("Done.")


if __name__ == "__main__":
    main()
