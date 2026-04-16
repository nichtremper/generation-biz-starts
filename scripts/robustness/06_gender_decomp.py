"""
Robustness Check 6: Gender Decomposition

Test whether the headline findings hold separately for men and women.
If the recent SE elevation is concentrated in one gender, the aggregate
signal may mask opposite-direction changes in the other.

Risk: Moderate. Halving the sample doubles SE on rates (~√2 wider CIs).
If findings diverge sharply by gender, the headline claim (young adults
are forming businesses at elevated rates) needs to be qualified.

Reads:
  data/processed/matched_mom.parquet
  data/processed/matched_yoy.parquet

Outputs:
  figures/robustness/06_gender_decomp.png
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

# SEX codes: 1 = male, 2 = female
SEX_LABELS = {1: "Male", 2: "Female"}
SEX_COLORS = {1: "#2a6496", 2: "#c0392b"}  # blue / crimson
AGE_FOCUS  = "20_to_34"
AGE_RANGE  = (20, 34)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def compute_yoy_by_sex(df, age_min, age_max):
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
    for sex_code in [1, 2]:
        for quarter, grp in subset[subset["SEX_t0"] == sex_code].groupby("quarter"):
            rate = _entry_rate(grp, "new_entrant", "at_risk", "weight")
            records.append({
                "quarter": quarter,
                "sex":     sex_code,
                "rate":    rate,
                "n_at_risk": int(grp["at_risk"].sum()),
            })
    return pd.DataFrame(records).sort_values(["sex", "quarter"])


def compute_mom_by_sex(df, age_min, age_max):
    df = df.copy()
    df["period"] = pd.to_datetime(
        df["YEAR_t0"].astype(str) + "-" + df["MONTH_t0"].astype(str).str.zfill(2)
    )
    subset = df[df["AGE_t0"].between(age_min, age_max)]

    records = []
    for sex_code in [1, 2]:
        for period, grp in subset[subset["SEX_t0"] == sex_code].groupby("period"):
            rate = _entry_rate(grp, "new_entrant", "at_risk", "WTFINL_t0")
            records.append({
                "period": period,
                "sex":    sex_code,
                "rate":   rate,
                "n_at_risk": int(grp["at_risk"].sum()),
            })
    df_out = pd.DataFrame(records).sort_values(["sex", "period"])
    # 3mo rolling per sex
    df_out["rate_3mo"] = (
        df_out.groupby("sex")["rate"]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
    )
    return df_out


def baseline_mean_by_quarter(rates, sex_code, year_lo=2005, year_hi=2019):
    sub = rates[
        (rates["sex"] == sex_code) &
        (rates["quarter"].dt.year.between(year_lo, year_hi))
    ].copy()
    sub["season"] = sub["quarter"].dt.quarter
    return sub.groupby("season")["rate"].mean()


def main():
    log("Reading MOM matched pairs...")
    mom = pd.read_parquet(PROCESSED_DIR / "matched_mom.parquet")
    log(f"  {len(mom):,} pairs.")

    log("Reading YOY matched pairs...")
    yoy = pd.read_parquet(PROCESSED_DIR / "matched_yoy.parquet")

    log(f"Computing MOM rates by sex (age {AGE_RANGE[0]}–{AGE_RANGE[1]})...")
    mom_rates = compute_mom_by_sex(mom, *AGE_RANGE)

    log(f"Computing YOY rates by sex (age {AGE_RANGE[0]}–{AGE_RANGE[1]})...")
    yoy_rates = compute_yoy_by_sex(yoy, *AGE_RANGE)

    # --- Plot ---
    fig, axes = plt.subplots(2, 2, figsize=(14, 9),
                             gridspec_kw={"hspace": 0.45, "wspace": 0.3})
    fig.suptitle(
        f"SE Entry Rate by Gender — Age {AGE_RANGE[0]}–{AGE_RANGE[1]}\n"
        "Left: MOM (3mo rolling)  |  Right: YOY quarterly",
        fontsize=10,
    )

    for row, sex_code in enumerate([1, 2]):
        label = SEX_LABELS[sex_code]
        color = SEX_COLORS[sex_code]

        # MOM panel
        ax = axes[row, 0]
        sub = mom_rates[mom_rates["sex"] == sex_code].sort_values("period")
        ax.axvspan(COVID_START, COVID_END, color="0.88", zorder=0)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)
        ax.plot(sub["period"], sub["rate_3mo"] * 100,
                color=color, linewidth=1.8, label=f"{label} (3mo avg)")
        ax.set_title(f"MOM — {label}", fontsize=9)
        ax.set_ylabel("Entry rate (%)", fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
        ax.legend(fontsize=7.5, framealpha=0.9)
        ax.tick_params(labelsize=8)
        ax.xaxis.set_major_locator(mdates.YearLocator(4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

        # YOY panel
        ax = axes[row, 1]
        sub_y = yoy_rates[yoy_rates["sex"] == sex_code].sort_values("quarter")
        dates = sub_y["quarter"].dt.to_timestamp()

        # Baseline reference
        bl_means = baseline_mean_by_quarter(yoy_rates, sex_code)
        sub_y2 = sub_y.copy()
        sub_y2["season"] = sub_y2["quarter"].dt.quarter
        sub_y2["bl_mean"] = sub_y2["season"].map(bl_means)

        ax.axvspan(COVID_START, COVID_END, color="0.88", zorder=0)
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)
        ax.plot(dates, sub_y2["rate"] * 100,
                color=color, linewidth=1.8, marker="o", markersize=3,
                label=f"{label}")
        ax.plot(dates, sub_y2["bl_mean"] * 100,
                color="#333333", linewidth=1.6, linestyle="--",
                label="2005–2019 seasonal mean")
        ax.set_title(f"YOY — {label}", fontsize=9)
        ax.set_ylabel("Entry rate (%)", fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
        ax.legend(fontsize=7.5, framealpha=0.9)
        ax.tick_params(labelsize=8)
        ax.xaxis.set_major_locator(mdates.YearLocator(4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    out = FIGURES_DIR / "06_gender_decomp.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    # Summary
    log("\nSummary — recent YOY entry rate vs. 2005–2019 mean by gender:")
    for sex_code in [1, 2]:
        label = SEX_LABELS[sex_code]
        sub = yoy_rates[yoy_rates["sex"] == sex_code].copy()
        recent = sub[sub["quarter"] >= pd.Period("2023Q4", freq="Q")]
        bl_means = baseline_mean_by_quarter(yoy_rates, sex_code)
        recent2 = recent.copy()
        recent2["season"] = recent2["quarter"].dt.quarter
        recent2["bl_mean"] = recent2["season"].map(bl_means)
        recent2["pct_above"] = (recent2["rate"] - recent2["bl_mean"]) / recent2["bl_mean"] * 100
        mean_rate = recent["rate"].mean() * 100
        mean_pct  = recent2["pct_above"].mean()
        print(f"  {label:8s}: mean={mean_rate:.3f}%  vs 2005–2019 mean: {mean_pct:+.1f}%")

    log("Done.")


if __name__ == "__main__":
    main()
