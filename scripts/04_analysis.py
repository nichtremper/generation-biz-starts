"""
Step 4: Compute entry and persistence rates, compare recent period to historical baseline.
Also computes baseline comparisons for SE stock (share of employed and labor force).

Reads:
  data/processed/matched_mom.parquet
  data/processed/matched_yoy.parquet
  data/processed/se_stock.parquet

Prints summary tables to stdout. Saves results to:
  data/processed/rates_mom.parquet
  data/processed/rates_yoy.parquet
  data/processed/recent_vs_baseline_mom.parquet
  data/processed/recent_vs_baseline_yoy.parquet
  data/processed/persistence_mom.parquet
  data/processed/persistence_yoy.parquet
  data/processed/recent_vs_baseline_persistence_mom.parquet
  data/processed/recent_vs_baseline_persistence_yoy.parquet
  data/processed/recent_vs_baseline_stock_employed.parquet
  data/processed/recent_vs_baseline_stock_lf.parquet
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rates import (
    BASELINE_YEARS_ROBUST,
    compute_baseline_stats,
    compute_mom_rates,
    compute_mom_persistence_rates,
    compute_mom_transition_rates,
    compute_quarterly_transition_rates,
    compute_yoy_rates,
    compute_yoy_persistence_rates,
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

    log("  Computing MOM baseline stats (2005–2019)...")
    mom_baseline = compute_baseline_stats(mom_rates, period_col="period")
    log("  Flagging recent MOM periods vs. baseline...")
    mom_recent = flag_recent_vs_baseline(mom_rates, mom_baseline, period_col="period")
    mom_recent.to_parquet(PROCESSED_DIR / "recent_vs_baseline_mom.parquet", index=False)

    log("  Computing MOM baseline stats — robustness check (2010–2019)...")
    mom_baseline_robust = compute_baseline_stats(
        mom_rates, period_col="period", baseline_years=BASELINE_YEARS_ROBUST
    )
    mom_recent_robust = flag_recent_vs_baseline(mom_rates, mom_baseline_robust, period_col="period")
    mom_recent_robust.to_parquet(PROCESSED_DIR / "recent_vs_baseline_mom_robust.parquet", index=False)

    print("\n--- MOM: Recent period vs. baseline (age 20–34) ---")
    display_cols = ["period", "entry_rate_3mo", "entry_rate_inc_3mo", "baseline_mean", "z_score", "above_baseline"]
    subset = mom_recent[mom_recent["age_group"] == "20_to_34"][display_cols]
    print(subset.to_string(index=False))

    # --- Year-over-year rates ---
    log("\nComputing YOY entry rates...")
    yoy_rates = compute_yoy_rates(yoy)
    log("  Writing rates_yoy.parquet...")
    yoy_rates.to_parquet(PROCESSED_DIR / "rates_yoy.parquet", index=False)

    log("  Computing YOY baseline stats (2005–2019)...")
    yoy_baseline = compute_baseline_stats(yoy_rates, period_col="quarter")
    log("  Flagging recent YOY periods vs. baseline...")
    yoy_recent = flag_recent_vs_baseline(yoy_rates, yoy_baseline, period_col="quarter")
    yoy_recent.to_parquet(PROCESSED_DIR / "recent_vs_baseline_yoy.parquet", index=False)

    log("  Computing YOY baseline stats — robustness check (2010–2019)...")
    yoy_baseline_robust = compute_baseline_stats(
        yoy_rates, period_col="quarter", baseline_years=BASELINE_YEARS_ROBUST
    )
    yoy_recent_robust = flag_recent_vs_baseline(yoy_rates, yoy_baseline_robust, period_col="quarter")
    yoy_recent_robust.to_parquet(PROCESSED_DIR / "recent_vs_baseline_yoy_robust.parquet", index=False)

    print("\n--- YOY: Recent period vs. baseline (age 20–34) ---")
    display_cols = ["quarter", "entry_rate", "entry_rate_inc", "baseline_mean", "z_score", "above_baseline"]
    subset = yoy_recent[yoy_recent["age_group"] == "20_to_34"][display_cols]
    print(subset.to_string(index=False))

    # --- MOM persistence rates ---
    log("Computing MOM persistence rates...")
    mom_persistence = compute_mom_persistence_rates(mom)
    mom_persistence.to_parquet(PROCESSED_DIR / "persistence_mom.parquet", index=False)

    mom_persist_baseline = compute_baseline_stats(
        mom_persistence, period_col="period", rate_col="persistence_rate"
    )
    mom_persist_recent = flag_recent_vs_baseline(
        mom_persistence, mom_persist_baseline, period_col="period", rate_col="persistence_rate"
    )
    mom_persist_recent.to_parquet(
        PROCESSED_DIR / "recent_vs_baseline_persistence_mom.parquet", index=False
    )

    # --- YOY persistence rates ---
    log("Computing YOY persistence rates...")
    yoy_persistence = compute_yoy_persistence_rates(yoy)
    yoy_persistence.to_parquet(PROCESSED_DIR / "persistence_yoy.parquet", index=False)

    yoy_persist_baseline = compute_baseline_stats(
        yoy_persistence, period_col="quarter", rate_col="persistence_rate"
    )
    yoy_persist_recent = flag_recent_vs_baseline(
        yoy_persistence, yoy_persist_baseline, period_col="quarter", rate_col="persistence_rate"
    )
    yoy_persist_recent.to_parquet(
        PROCESSED_DIR / "recent_vs_baseline_persistence_yoy.parquet", index=False
    )

    print("\n--- YOY Persistence: Recent period vs. baseline (age 20–64) ---")
    display_cols = ["quarter", "persistence_rate", "persistence_rate_inc", "baseline_mean", "z_score", "above_baseline"]
    subset = yoy_persist_recent[yoy_persist_recent["age_group"] == "20_to_64"][display_cols]
    print(subset.to_string(index=False))

    # --- MOM transition rates (unemployment→SE vs employment→SE) ---
    log("Computing MOM transition rates (monthly)...")
    mom_transition = compute_mom_transition_rates(mom)
    mom_transition.to_parquet(PROCESSED_DIR / "transition_rates_mom.parquet", index=False)
    log("  Saved: transition_rates_mom.parquet")

    log("Computing quarterly transition rates...")
    quarterly_transition = compute_quarterly_transition_rates(mom)
    quarterly_transition.to_parquet(PROCESSED_DIR / "transition_rates_quarterly.parquet", index=False)
    log("  Saved: transition_rates_quarterly.parquet")

    # --- SE stock baseline comparisons ---
    stock_path = PROCESSED_DIR / "se_stock.parquet"
    if stock_path.exists():
        log("Reading SE stock...")
        stock = pd.read_parquet(stock_path)
        stock["period"] = pd.to_datetime(
            stock["YEAR"].astype(str) + "-" + stock["MONTH"].astype(str).str.zfill(2)
        )

        for rate_col, label, out_name in [
            ("se_share_employed", "employed", "stock_employed"),
            ("se_share_lf",       "labor force", "stock_lf"),
        ]:
            log(f"  Computing stock baseline stats (denominator: {label})...")
            baseline = compute_baseline_stats(stock, period_col="period", rate_col=rate_col)
            recent = flag_recent_vs_baseline(stock, baseline, period_col="period", rate_col=rate_col)
            out_path = PROCESSED_DIR / f"recent_vs_baseline_{out_name}.parquet"
            recent.to_parquet(out_path, index=False)
            log(f"  Saved: {out_path.name}")

        print("\n--- SE Stock (share of employed, age 20–34) ---")
        disp_cols = ["period", "se_share_employed", "se_share_inc_employed", "wt_se", "wt_employed"]
        subset = stock[stock["age_group"] == "20_to_34"][disp_cols].sort_values("period").tail(12)
        print(subset.to_string(index=False))
    else:
        log("se_stock.parquet not found — skipping stock analysis. Run 02_match.py first.")

    # --- MOM vs YOY divergence note ---
    log("Pipeline complete.")
    print("\n--- Divergence check ---")
    print("If MOM above_baseline=True but YOY above_baseline=False,")
    print("this signals attempted but abandoned self-employment, not durable formation.")


if __name__ == "__main__":
    main()
