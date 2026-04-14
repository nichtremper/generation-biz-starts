"""
Step 4: Compute entry rates and compare recent period to historical baseline.

Reads:
  data/processed/matched_mom.parquet
  data/processed/matched_yoy.parquet

Prints summary tables to stdout. Saves results to:
  data/processed/rates_mom.parquet
  data/processed/rates_yoy.parquet
  data/processed/recent_vs_baseline_mom.parquet
  data/processed/recent_vs_baseline_yoy.parquet
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rates import (
    compute_baseline_stats,
    compute_mom_rates,
    compute_yoy_rates,
    flag_recent_vs_baseline,
)

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    log("Reading matched MOM pairs...")
    mom = pd.read_parquet(PROCESSED_DIR / "matched_mom.parquet")
    log(f"  Loaded {len(mom):,} MOM pairs.")

    log("Reading matched YOY pairs...")
    yoy = pd.read_parquet(PROCESSED_DIR / "matched_yoy.parquet")
    log(f"  Loaded {len(yoy):,} YOY pairs.")

    # --- Month-over-month rates ---
    log("Computing MOM entry rates...")
    mom_rates = compute_mom_rates(mom)
    log("  Writing rates_mom.parquet...")
    mom_rates.to_parquet(PROCESSED_DIR / "rates_mom.parquet", index=False)

    log("  Computing MOM baseline stats...")
    mom_baseline = compute_baseline_stats(mom_rates, period_col="period")
    log("  Flagging recent MOM periods vs. baseline...")
    mom_recent = flag_recent_vs_baseline(mom_rates, mom_baseline, period_col="period")
    mom_recent.to_parquet(PROCESSED_DIR / "recent_vs_baseline_mom.parquet", index=False)

    print("\n--- MOM: Recent period vs. baseline (age 35 and under) ---")
    display_cols = ["period", "entry_rate_3mo", "entry_rate_inc_3mo", "baseline_mean", "z_score", "above_baseline"]
    subset = mom_recent[mom_recent["age_group"] == "35_and_under"][display_cols]
    print(subset.to_string(index=False))

    # --- Year-over-year rates ---
    log("\nComputing YOY entry rates...")
    yoy_rates = compute_yoy_rates(yoy)
    log("  Writing rates_yoy.parquet...")
    yoy_rates.to_parquet(PROCESSED_DIR / "rates_yoy.parquet", index=False)

    log("  Computing YOY baseline stats...")
    yoy_baseline = compute_baseline_stats(yoy_rates, period_col="quarter")
    log("  Flagging recent YOY periods vs. baseline...")
    yoy_recent = flag_recent_vs_baseline(yoy_rates, yoy_baseline, period_col="quarter")
    yoy_recent.to_parquet(PROCESSED_DIR / "recent_vs_baseline_yoy.parquet", index=False)

    print("\n--- YOY: Recent period vs. baseline (age 35 and under) ---")
    display_cols = ["quarter", "entry_rate", "entry_rate_inc", "baseline_mean", "z_score", "above_baseline"]
    subset = yoy_recent[yoy_recent["age_group"] == "35_and_under"][display_cols]
    print(subset.to_string(index=False))

    # --- MOM vs YOY divergence note ---
    log("Pipeline complete.")
    print("\n--- Divergence check ---")
    print("If MOM above_baseline=True but YOY above_baseline=False,")
    print("this signals attempted but abandoned self-employment, not durable formation.")


if __name__ == "__main__":
    main()
