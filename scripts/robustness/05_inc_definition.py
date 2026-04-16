"""
Robustness Check 5: Incorporated SE Definition — Broad vs. Strict

The canonical "incorporated SE entry rate" uses new_entrant_inc:
  ~se_inc_t0 & se_inc_t1  — was not incorporated SE at T0, is at T1

This includes unincorporated→incorporated restructurings (existing SE owner
formalizes their business). These are NOT new businesses; they are legal
status changes. The strict definition excludes them:
  new_entrant_inc_strict = ~se_t0 & se_inc_t1  — was not SE at all at T0

Risk: High for the incorporated entry rate specifically. If restructurings
are a large fraction of incorporated "new entrants" — especially post-COVID
(when many sole proprietors incorporated for liability/tax reasons) — the
canonical rate overstates true new incorporated business formation.

Reads:
  data/processed/matched_mom.parquet
  data/processed/matched_yoy.parquet

Outputs:
  figures/robustness/05_inc_definition.png
"""

from datetime import datetime
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.rates import AGE_GROUPS, _entry_rate

PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
FIGURES_DIR   = Path(__file__).parent.parent.parent / "figures" / "robustness"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

COVID_START  = pd.Timestamp("2020-01-01")
COVID_END    = pd.Timestamp("2022-12-31")
RECENT_START = pd.Timestamp("2023-10-01")
AGE_FOCUS    = ["20_to_34", "20_to_64"]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def compute_rates(df, period_col, weight_col):
    """Return broad and strict incorporated entry rates per (period, age_group)."""
    records = []
    for group, (age_min, age_max) in AGE_GROUPS.items():
        subset = df[df["AGE_t0"].between(age_min, age_max)]
        for period, grp in subset.groupby(period_col):
            broad  = _entry_rate(grp, "new_entrant_inc",        "at_risk_inc", weight_col)
            strict = _entry_rate(grp, "new_entrant_inc_strict",  "at_risk",    weight_col)
            n_restructure = grp[
                grp["se_t0"] & ~grp["se_inc_t0"] & grp["se_inc_t1"]
            ][weight_col].sum()  # uninc→inc transitions
            n_denom_inc = grp[weight_col][grp["at_risk_inc"]].sum()
            records.append({
                period_col:     period,
                "age_group":    group,
                "rate_broad":   broad,
                "rate_strict":  strict,
                "restructure_rate": n_restructure / n_denom_inc if n_denom_inc > 0 else np.nan,
            })
    return pd.DataFrame(records)


def main():
    log("Reading MOM matched pairs...")
    mom = pd.read_parquet(PROCESSED_DIR / "matched_mom.parquet")
    log(f"  {len(mom):,} pairs.")

    log("Reading YOY matched pairs...")
    yoy = pd.read_parquet(PROCESSED_DIR / "matched_yoy.parquet")
    if "LNKFW1YWT_t1" in yoy.columns:
        yoy["weight"] = yoy["LNKFW1YWT_t1"].where(yoy["LNKFW1YWT_t1"] > 0, yoy["WTFINL_t0"])
    else:
        yoy["weight"] = yoy["WTFINL_t0"]

    mom["period"] = pd.to_datetime(
        mom["YEAR_t0"].astype(str) + "-" + mom["MONTH_t0"].astype(str).str.zfill(2)
    )
    yoy["quarter"] = pd.PeriodIndex(
        pd.to_datetime(
            yoy["YEAR_t1"].astype(str) + "-" + yoy["MONTH_t1"].astype(str).str.zfill(2)
        ), freq="Q",
    )

    log("Computing MOM rates (broad vs strict)...")
    mom_rates = compute_rates(mom, "period", "WTFINL_t0")
    # 3mo rolling
    for col in ["rate_broad", "rate_strict", "restructure_rate"]:
        mom_rates[f"{col}_3mo"] = (
            mom_rates.groupby("age_group")[col]
            .transform(lambda s: s.rolling(3, min_periods=1).mean())
        )

    log("Computing YOY rates (broad vs strict)...")
    yoy_rates = compute_rates(yoy, "quarter", "weight")

    # --- Plot ---
    fig, axes = plt.subplots(len(AGE_FOCUS), 2, figsize=(14, 8),
                             gridspec_kw={"hspace": 0.45, "wspace": 0.3})
    fig.suptitle(
        "Incorporated SE Entry Rate: Broad vs. Strict Definition\n"
        "Broad = ~inc_SE_t0 → inc_SE_t1 (includes uninc→inc restructuring)\n"
        "Strict = ~SE_t0 at all → inc_SE_t1 (pure new formation only)",
        fontsize=10,
    )

    for row, group in enumerate(AGE_FOCUS):
        # MOM
        ax = axes[row, 0]
        sub = mom_rates[mom_rates["age_group"] == group].sort_values("period")
        ax.axvspan(COVID_START, COVID_END, color="0.88", zorder=0)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)
        ax.plot(sub["period"], sub["rate_broad_3mo"] * 100,
                color="#2a6496", linewidth=1.8, label="Broad (canonical)")
        ax.plot(sub["period"], sub["rate_strict_3mo"] * 100,
                color="#c0392b", linewidth=1.4, linestyle="--",
                label="Strict (pure new)")
        ax.fill_between(sub["period"],
                        sub["rate_strict_3mo"] * 100,
                        sub["rate_broad_3mo"] * 100,
                        alpha=0.12, color="#e67e22",
                        label="Gap (restructurings)")
        ax.set_title(f"MOM — {group.replace('_', '–')}", fontsize=9)
        ax.set_ylabel("Rate (%)", fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
        ax.legend(fontsize=7.5, framealpha=0.9)
        ax.tick_params(labelsize=8)
        ax.xaxis.set_major_locator(mdates.YearLocator(4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

        # YOY
        ax = axes[row, 1]
        sub_y = yoy_rates[yoy_rates["age_group"] == group].sort_values("quarter")
        dates = sub_y["quarter"].dt.to_timestamp()
        ax.axvspan(COVID_START, COVID_END, color="0.88", zorder=0)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)
        ax.plot(dates, sub_y["rate_broad"] * 100,
                color="#2a6496", linewidth=1.8, marker="o", markersize=3,
                label="Broad (canonical)")
        ax.plot(dates, sub_y["rate_strict"] * 100,
                color="#c0392b", linewidth=1.4, linestyle="--", marker="o", markersize=3,
                label="Strict (pure new)")
        ax.fill_between(dates,
                        sub_y["rate_strict"] * 100,
                        sub_y["rate_broad"] * 100,
                        alpha=0.12, color="#e67e22",
                        label="Gap (restructurings)")
        ax.set_title(f"YOY — {group.replace('_', '–')}", fontsize=9)
        ax.set_ylabel("Rate (%)", fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
        ax.legend(fontsize=7.5, framealpha=0.9)
        ax.tick_params(labelsize=8)
        ax.xaxis.set_major_locator(mdates.YearLocator(4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    out = FIGURES_DIR / "05_inc_definition.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    # Summary: size of restructuring component
    log("\nSummary — restructuring share of 'broad' incorporated new entrants (20–34, recent):")
    recent_mom = mom_rates[
        (mom_rates["age_group"] == "20_to_34") &
        (mom_rates["period"] >= "2023-10")
    ]
    print(f"  Mean restructure rate: {recent_mom['restructure_rate'].mean()*100:.4f}%")
    print(f"  As % of broad rate: "
          f"{recent_mom['restructure_rate'].mean() / recent_mom['rate_broad'].mean() * 100:.1f}%")

    log("Done.")


if __name__ == "__main__":
    main()
