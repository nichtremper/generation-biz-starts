"""
Robustness Check 10: CPS Redesign Structural Break (January 2014)

The CPS underwent a major questionnaire redesign in January 2014, which
affected how self-employment is classified. BLS documented ~0.3pp increase
in SE rates that is attributable to the redesign, not real change.

If the structural break raises measured SE rates, then:
  - Baseline means computed over 2005–2019 are pulled up by post-2014 levels
  - Comparisons of the recent period to this mixed baseline are conservative
    (the baseline appears higher than true pre-redesign rates)
  - Conversely, comparisons to 2005–2013 only would show the recent period
    as even more elevated

This check:
  1. Tests for a structural break at Jan 2014 in both the YOY entry rate
     and the SE stock share using a Chow-style t-test on means.
  2. Computes separate baselines for pre-2014 (2005–2013) and post-2014
     (2014–2019) periods.
  3. Shows how the recent period compares to each.

Risk: Moderate-High. If the 2014 redesign inflated measured SE by ~0.3pp,
the "all-time high" SE stock claims in the report may not be apples-to-apples
with pre-2014 levels. The flow entry rates are likely less affected (they
measure transitions, not levels), but the stock share comparisons are at risk.

Reads:
  data/processed/rates_yoy.parquet
  data/processed/se_stock.parquet

Outputs:
  figures/robustness/10_cps_redesign.png
"""

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
FIGURES_DIR   = Path(__file__).parent.parent.parent / "figures" / "robustness"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

REDESIGN_DATE  = pd.Timestamp("2014-01-01")
COVID_START    = pd.Timestamp("2020-01-01")
COVID_END      = pd.Timestamp("2022-12-31")
RECENT_START   = pd.Timestamp("2023-10-01")
AGE_FOCUS_YOY  = "20_to_34"
AGE_FOCUS_STCK = "20_to_34"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def welch_t_test(a, b):
    """Two-sample Welch t-test. Returns t-stat, approx p-value (two-sided)."""
    na, nb = len(a), len(b)
    if na < 3 or nb < 3:
        return np.nan, np.nan
    va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
    se = np.sqrt(va / na + vb / nb)
    t  = (np.mean(a) - np.mean(b)) / max(se, 1e-15)
    # Welch-Satterthwaite df
    df = (va/na + vb/nb)**2 / (
        (va/na)**2 / (na - 1) + (vb/nb)**2 / (nb - 1)
    )
    # Approximate p-value using normal distribution (valid for large df)
    from scipy.special import btdtr  # noqa: F401
    # Fall back to normal approximation to avoid scipy dependency
    # z-score approximation good for df > 30
    p = 2 * (1 - _normal_cdf(abs(t)))
    return t, p


def _normal_cdf(z):
    """Approximation of standard normal CDF using Horner's method."""
    # Abramowitz & Stegun 26.2.16 approximation
    t_val = 1.0 / (1.0 + 0.2316419 * abs(z))
    poly  = t_val * (0.319381530 + t_val * (
            -0.356563782 + t_val * (
             1.781477937 + t_val * (
            -1.821255978 + t_val * 1.330274429))))
    p_upper = poly * np.exp(-0.5 * z**2) / np.sqrt(2 * np.pi)
    return 1.0 - p_upper if z >= 0 else p_upper


def main():
    log("Reading YOY rates...")
    yoy = pd.read_parquet(PROCESSED_DIR / "rates_yoy.parquet")
    yoy["date"] = yoy["quarter"].dt.to_timestamp()

    log("Reading SE stock...")
    stock = pd.read_parquet(PROCESSED_DIR / "se_stock.parquet")
    stock["period"] = pd.to_datetime(
        stock["YEAR"].astype(str) + "-" + stock["MONTH"].astype(str).str.zfill(2)
    )

    # --- YOY entry rate breakpoint analysis ---
    yoy34 = yoy[yoy["age_group"] == AGE_FOCUS_YOY].sort_values("date").copy()
    pre14_yoy  = yoy34[(yoy34["date"] < REDESIGN_DATE) &
                        yoy34["date"].dt.year.between(2005, 2013)]["entry_rate"]
    post14_yoy = yoy34[(yoy34["date"] >= REDESIGN_DATE) &
                        yoy34["date"].dt.year.between(2014, 2019)]["entry_rate"]
    t_yoy, p_yoy = welch_t_test(pre14_yoy.values, post14_yoy.values)

    # --- SE stock breakpoint analysis ---
    stk34 = stock[
        (stock["age_group"] == AGE_FOCUS_STCK) &
        (stock["se_share_employed"] > 0)
    ].copy()
    pre14_stk  = stk34[(stk34["period"] < REDESIGN_DATE) &
                        stk34["period"].dt.year.between(2005, 2013)]["se_share_employed"]
    post14_stk = stk34[(stk34["period"] >= REDESIGN_DATE) &
                        stk34["period"].dt.year.between(2014, 2019)]["se_share_employed"]
    t_stk, p_stk = welch_t_test(pre14_stk.values, post14_stk.values)

    log(f"  YOY t-test (pre/post 2014): t={t_yoy:.2f}, p={p_yoy:.3f}")
    log(f"  Stock t-test (pre/post 2014): t={t_stk:.2f}, p={p_stk:.3f}")

    # --- Figure ---
    fig, axes = plt.subplots(2, 2, figsize=(14, 9),
                             gridspec_kw={"hspace": 0.45, "wspace": 0.3})
    fig.suptitle(
        "CPS 2014 Redesign Structural Break — SE Entry Rate and Stock Share\n"
        "Left: time series with pre/post-2014 baseline means  |  "
        "Right: recent period vs. two baseline windows",
        fontsize=10,
    )

    # Panel [0,0]: YOY entry rate time series
    ax = axes[0, 0]
    ax.axvspan(COVID_START, COVID_END, color="0.88", zorder=0)
    ax.axvline(REDESIGN_DATE, color="purple", linewidth=1.2, linestyle="--",
               zorder=3, label="2014 redesign")
    ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)
    ax.plot(yoy34["date"], yoy34["entry_rate"] * 100,
            color="#2a6496", linewidth=1.6, marker="o", markersize=2.5,
            label=f"{AGE_FOCUS_YOY} entry rate")

    # Pre/post baseline mean lines
    ax.axhline(pre14_yoy.mean() * 100, color="#c0392b", linewidth=1.5, linestyle="--",
               label=f"2005–2013 mean={pre14_yoy.mean()*100:.3f}%")
    ax.axhline(post14_yoy.mean() * 100, color="#e67e22", linewidth=1.5, linestyle="--",
               label=f"2014–2019 mean={post14_yoy.mean()*100:.3f}%")
    ax.set_title(f"YOY Entry Rate — {AGE_FOCUS_YOY}", fontsize=9)
    ax.set_ylabel("Entry rate (%)", fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
    ax.legend(fontsize=7.5, framealpha=0.9)
    ax.tick_params(labelsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator(4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.text(0.02, 0.04,
            f"Welch t={t_yoy:.2f}, p={p_yoy:.3f}\n"
            f"(2005–2013 vs. 2014–2019)",
            transform=ax.transAxes, fontsize=7.5, color="0.4", va="bottom")

    # Panel [1,0]: SE stock time series
    ax = axes[1, 0]
    stk_valid = stk34[stk34["se_share_employed"] > 0]
    ax.axvspan(COVID_START, COVID_END, color="0.88", zorder=0)
    ax.axvline(REDESIGN_DATE, color="purple", linewidth=1.2, linestyle="--",
               zorder=3, label="2014 redesign")
    ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)
    ax.plot(stk_valid["period"], stk_valid["se_share_employed"] * 100,
            color="#2a6496", linewidth=1.2, alpha=0.7, label=f"{AGE_FOCUS_STCK} SE share")
    ax.axhline(pre14_stk.mean() * 100, color="#c0392b", linewidth=1.5, linestyle="--",
               label=f"2005–2013 mean={pre14_stk.mean()*100:.2f}%")
    ax.axhline(post14_stk.mean() * 100, color="#e67e22", linewidth=1.5, linestyle="--",
               label=f"2014–2019 mean={post14_stk.mean()*100:.2f}%")
    ax.set_title(f"SE Stock Share — {AGE_FOCUS_STCK}", fontsize=9)
    ax.set_ylabel("SE share / employed (%)", fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1f}%"))
    ax.legend(fontsize=7.5, framealpha=0.9)
    ax.tick_params(labelsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator(4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.text(0.02, 0.04,
            f"Welch t={t_stk:.2f}, p={p_stk:.3f}\n"
            f"(2005–2013 vs. 2014–2019)",
            transform=ax.transAxes, fontsize=7.5, color="0.4", va="bottom")

    # Panel [0,1]: Recent YOY rate vs. two baselines
    ax = axes[0, 1]
    recent_yoy = yoy34[yoy34["date"] >= RECENT_START]
    full_mean  = yoy34[yoy34["date"].dt.year.between(2005, 2019)]["entry_rate"].mean()
    pre_mean   = pre14_yoy.mean()
    post_mean  = post14_yoy.mean()

    x = np.arange(len(recent_yoy))
    ax.bar(x, recent_yoy["entry_rate"].values * 100, color="#2a6496", alpha=0.7,
           label="Recent quarters")
    ax.axhline(full_mean  * 100, color="#333333",  linewidth=1.5, linestyle="--",
               label=f"2005–2019 mean={full_mean*100:.3f}%")
    ax.axhline(pre_mean   * 100, color="#c0392b",  linewidth=1.5, linestyle="--",
               label=f"2005–2013 mean={pre_mean*100:.3f}% (pre-redesign)")
    ax.axhline(post_mean  * 100, color="#e67e22",  linewidth=1.5, linestyle="--",
               label=f"2014–2019 mean={post_mean*100:.3f}% (post-redesign)")
    ax.set_xticks(x)
    ax.set_xticklabels(
        [str(q) for q in recent_yoy["quarter"].values], rotation=45, ha="right", fontsize=7.5
    )
    ax.set_title("Recent vs. Baseline Windows (YOY)", fontsize=9)
    ax.set_ylabel("Entry rate (%)", fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
    ax.legend(fontsize=7.5, framealpha=0.9)
    ax.tick_params(labelsize=8)

    # Panel [1,1]: Recent stock vs. two baselines
    ax = axes[1, 1]
    recent_stk = stk34[
        stk34["period"] >= RECENT_START
    ].groupby(stk34["period"].dt.to_period("Q"))["se_share_employed"].mean()
    full_stk_mean = stk34[
        stk34["period"].dt.year.between(2005, 2019)
    ]["se_share_employed"].mean()
    pre_stk_mean  = pre14_stk.mean()
    post_stk_mean = post14_stk.mean()

    x2 = np.arange(len(recent_stk))
    ax.bar(x2, recent_stk.values * 100, color="#2a6496", alpha=0.7,
           label="Recent quarters (avg)")
    ax.axhline(full_stk_mean  * 100, color="#333333", linewidth=1.5, linestyle="--",
               label=f"2005–2019={full_stk_mean*100:.2f}%")
    ax.axhline(pre_stk_mean   * 100, color="#c0392b", linewidth=1.5, linestyle="--",
               label=f"2005–2013={pre_stk_mean*100:.2f}% (pre-redesign)")
    ax.axhline(post_stk_mean  * 100, color="#e67e22", linewidth=1.5, linestyle="--",
               label=f"2014–2019={post_stk_mean*100:.2f}% (post-redesign)")
    ax.set_xticks(x2)
    ax.set_xticklabels(
        [str(q) for q in recent_stk.index], rotation=45, ha="right", fontsize=7.5
    )
    ax.set_title("Recent vs. Baseline Windows (Stock Share)", fontsize=9)
    ax.set_ylabel("SE share / employed (%)", fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1f}%"))
    ax.legend(fontsize=7.5, framealpha=0.9)
    ax.tick_params(labelsize=8)

    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    out = FIGURES_DIR / "10_cps_redesign.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out}")
    plt.close(fig)

    # Summary
    log("\nSummary — pre vs. post 2014 redesign means:")
    print(f"  YOY entry rate (20–34): pre={pre14_yoy.mean()*100:.3f}%  "
          f"post={post14_yoy.mean()*100:.3f}%  "
          f"diff={+(post14_yoy.mean()-pre14_yoy.mean())*100:+.3f}pp  "
          f"t={t_yoy:.2f}  p={p_yoy:.3f}")
    print(f"  SE stock share (20–34): pre={pre14_stk.mean()*100:.2f}%  "
          f"post={post14_stk.mean()*100:.2f}%  "
          f"diff={+(post14_stk.mean()-pre14_stk.mean())*100:+.3f}pp  "
          f"t={t_stk:.2f}  p={p_stk:.3f}")
    log("Done.")


if __name__ == "__main__":
    main()
