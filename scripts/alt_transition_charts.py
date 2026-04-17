"""
Two 2x2 panel charts comparing self-employment entry pathways across age groups.

Chart 1 (transition_pathway_unemp.png):
    Unemployment→SE raw transition rate, one panel per age group (20-34, 35-44, 45-54, 55-64).
    Shared y-axis. Shaded band = 2005-2019 mean ± 1 SD.

Chart 2 (transition_pathway_emp.png):
    Employment→SE raw transition rate, same layout and shared y-axis.

Shared y-axis across both charts makes the absolute levels directly comparable.

Reads: data/processed/transition_rates_quarterly.parquet
Saves: figures/transition_pathway_unemp.png
       figures/transition_pathway_emp.png
"""

from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.lines as mlines
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
FIGURES_DIR   = Path(__file__).parent.parent / "figures"

COVID_START  = pd.Timestamp("2020-01-01")
COVID_END    = pd.Timestamp("2022-12-31")
RECENT_START = pd.Timestamp("2023-10-01")

# Drop the aggregate group — 2x2 needs exactly 4 panels
AGE_GROUPS = [
    ("20_to_34", "Age 20–34"),
    ("35_to_44", "Age 35–44"),
    ("45_to_54", "Age 45–54"),
    ("55_to_64", "Age 55–64"),
]


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _baseline_stats(df: pd.DataFrame, col: str) -> dict:
    """Per age-group mean and SD over 2005-2019."""
    stats = {}
    for group, _ in AGE_GROUPS:
        mask = (df["age_group"] == group) & df["period"].dt.year.isin(range(2005, 2020))
        stats[group] = {
            "mean": df.loc[mask, col].mean(),
            "sd":   df.loc[mask, col].std(),
        }
    return stats


def plot_pathway(df: pd.DataFrame, col: str, color: str, title: str) -> plt.Figure:
    """
    2x2 panel chart for a single transition series (col).
    Shared y-axis so absolute levels are comparable across age groups.
    """
    stats = _baseline_stats(df, col)

    fig, axes = plt.subplots(
        2, 2, figsize=(13, 10), sharex=True, sharey=True,
        gridspec_kw={"hspace": 0.35, "wspace": 0.08},
    )
    fig.suptitle(title, fontsize=11)

    for ax, (group, label) in zip(axes.flat, AGE_GROUPS):
        sub = df[df["age_group"] == group].sort_values("period")
        mn  = stats[group]["mean"]
        sd  = stats[group]["sd"]

        # COVID shading
        ax.axvspan(COVID_START, COVID_END, color="0.88", zorder=0)
        # Recent period marker
        ax.axvline(RECENT_START, color="0.4", linewidth=0.8, linestyle=":", zorder=2)
        # Historical band
        ax.axhspan((mn - sd) * 100, (mn + sd) * 100, color=color, alpha=0.15, zorder=1)
        # Historical mean
        ax.axhline(mn * 100, color=color, linewidth=0.8, linestyle="--", alpha=0.6, zorder=2)
        # Series
        ax.plot(sub["period"], sub[col] * 100,
                color=color, linewidth=1.6, marker="o", markersize=2.5, zorder=3)

        ax.set_title(label, fontsize=9, loc="left", pad=3)
        ax.tick_params(axis="both", labelsize=8)

        ax.xaxis.set_major_locator(mdates.YearLocator(4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # y-axis label on left column only
    for ax in axes[:, 0]:
        ax.set_ylabel("Transition rate (%)", fontsize=8)

    # Shared legend
    legend_elements = [
        mlines.Line2D([0], [0], color=color, linewidth=1.6, marker="o", markersize=3,
                      label="Quarterly rate"),
        mpatches.Patch(facecolor=color, alpha=0.25, label="2005–2019 mean ± 1 SD"),
        mlines.Line2D([0], [0], color=color, linewidth=0.8, linestyle="--", alpha=0.7,
                      label="2005–2019 mean"),
        mpatches.Patch(facecolor="0.88", label="COVID era (2020–2022)"),
        mlines.Line2D([0], [0], color="0.4", linewidth=0.8, linestyle=":",
                      label="Recent period start (Oct 2023)"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=3, fontsize=8,
               framealpha=0.9, bbox_to_anchor=(0.5, -0.04))
    fig.text(0.99, 0.01, "Source: IPUMS CPS, University of Minnesota",
             ha="right", va="bottom", fontsize=7, color="0.5")

    return fig


def main():
    path = PROCESSED_DIR / "transition_rates_quarterly.parquet"
    if not path.exists():
        log(f"ERROR: {path} not found. Run 04_analysis.py first.")
        return

    log("Reading transition_rates_quarterly.parquet...")
    df = pd.read_parquet(path)
    df["period"] = df["quarter"].dt.to_timestamp()
    log(f"  {len(df):,} rows, {df['age_group'].nunique()} age groups, "
        f"{df['period'].min().date()} to {df['period'].max().date()}")

    unemp_col = "unemp_to_se_3mo" if "unemp_to_se_3mo" in df.columns else "unemp_to_se"
    emp_col   = "emp_to_se_3mo"   if "emp_to_se_3mo"   in df.columns else "emp_to_se"

    log("Generating Chart 1: unemployment to self-employment...")
    fig1 = plot_pathway(
        df, unemp_col, color="crimson",
        title="Unemployment to Self-Employment Transition Rate by Age Group\n"
              "Raw quarterly rate (%)  |  CPS month-over-month pairs",
    )
    out1 = FIGURES_DIR / "transition_pathway_unemp.png"
    fig1.savefig(out1, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out1}")
    plt.close(fig1)

    log("Generating Chart 2: employment to self-employment...")
    fig2 = plot_pathway(
        df, emp_col, color="steelblue",
        title="Employment to Self-Employment Transition Rate by Age Group\n"
              "Raw quarterly rate (%)  |  CPS month-over-month pairs",
    )
    out2 = FIGURES_DIR / "transition_pathway_emp.png"
    fig2.savefig(out2, dpi=150, bbox_inches="tight")
    log(f"  Saved: {out2}")
    plt.close(fig2)

    log("Done.")


if __name__ == "__main__":
    main()
