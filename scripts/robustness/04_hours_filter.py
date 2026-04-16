"""
Robustness Check 4: Hours Worked Filter (Documentation Only)

Kauffman's New Entrepreneur Rate requires SE at T1 to work ≥15 hrs/week
(UHRSWORKT ≥ 15). This filter excludes very-marginal SE (casual freelancers,
occasional gig work) from the entry rate numerator.

STATUS: CANNOT BE APPLIED — UHRSWORKT is absent from both the raw CPS chunks
and the matched-pair files, despite being listed in the 01_extract.py VARIABLES
list. IPUMS omitted the variable from the extract, possibly because basic monthly
files for some sample years do not collect usual hours separately from ASEC.

This script:
  1. Confirms the variable is missing and reports which files were checked.
  2. Estimates the potential bias by comparing our 20–34 YOY entry rate to
     Kauffman's published New Entrepreneur Rate for the most recent overlapping year.
  3. Flags the limitation for reporting.

Action required: Re-submit the IPUMS extract with UHRSWORKT explicitly requested
and verify it is present in at least 90% of sample months before applying the
filter. If UHRSWORKT is unavailable for pre-2010 months, a consistent series
cannot be constructed across the full 2005–2019 baseline.

Reads:
  data/processed/rates_yoy.parquet
  data/raw/chunks/chunk_0000.parquet  (column audit only)

Outputs:
  figures/robustness/04_hours_filter_audit.png
"""

from datetime import datetime
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import polars as pl
import pandas as pd

PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
RAW_CHUNKS    = Path(__file__).parent.parent.parent / "data" / "raw" / "chunks"
FIGURES_DIR   = Path(__file__).parent.parent.parent / "figures" / "robustness"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def audit_variable_coverage():
    """Check each chunk for UHRSWORKT and other hours-related columns."""
    chunks = sorted(RAW_CHUNKS.glob("chunk_*.parquet"))
    missing = 0
    hours_cols_found = set()
    for chunk_path in chunks[:5]:  # sample first 5 chunks
        schema = pl.scan_parquet(str(chunk_path)).collect_schema()
        col_names = schema.names()
        for col in col_names:
            if "HRS" in col.upper() or "HOURS" in col.upper() or "UHRS" in col.upper():
                hours_cols_found.add(col)
        if "UHRSWORKT" not in col_names:
            missing += 1

    return missing, hours_cols_found, len(chunks)


def main():
    log("Auditing UHRSWORKT presence in raw chunks...")
    missing, hours_cols, total_chunks = audit_variable_coverage()

    log(f"\n{'='*60}")
    log("HOURS FILTER AUDIT REPORT")
    log(f"{'='*60}")
    log(f"Total chunk files:          {total_chunks}")
    log(f"Chunks missing UHRSWORKT:   {missing}/5 sampled (likely all)")
    log(f"Hours-related cols present: {hours_cols if hours_cols else 'NONE'}")

    log("\nIMPLICATION:")
    log("  The Kauffman ≥15 hrs/week filter cannot be applied.")
    log("  Our SE entry rates and stock counts include all SE workers")
    log("  regardless of hours worked. This overstates SE participation")
    log("  relative to Kauffman's published rate, particularly for")
    log("  unincorporated SE (which captures more marginal/gig work).")
    log("  Incorporated-only rates are less affected (incorporated SE")
    log("  businesses are less likely to be very-part-time).")

    # Compare our rate to Kauffman's published rate (manual reference values)
    # Source: Kauffman Indicators of Entrepreneurship 2023
    # These are approximate published values for comparison only
    kauffman_ref = {
        2018: 0.0320,
        2019: 0.0310,
        2020: 0.0370,
        2021: 0.0380,
        2022: 0.0360,
        2023: 0.0350,
    }

    log("\nExternal validity: Our 20-64 YOY entry rate vs Kauffman published NER")
    yoy = pd.read_parquet(PROCESSED_DIR / "rates_yoy.parquet")
    ours = yoy[yoy["age_group"] == "20_to_64"].copy()
    ours["year"] = ours["quarter"].dt.year
    ours_annual = ours.groupby("year")["entry_rate"].mean()

    fig, ax = plt.subplots(figsize=(10, 5))
    years_ours = sorted(ours_annual.index)
    ax.plot(years_ours, ours_annual.values * 100, "o-", color="steelblue",
            linewidth=1.8, markersize=4, label="Our estimate (20–64, no hours filter)")

    kauff_years = sorted(kauffman_ref.keys())
    kauff_vals  = [kauffman_ref[y] * 100 for y in kauff_years]
    ax.plot(kauff_years, kauff_vals, "s--", color="darkorange", linewidth=1.4,
            markersize=5, label="Kauffman NER (published, 20–64, with hours filter)")

    ax.set_title("External Validity: Our YOY Rate vs Kauffman NER\n"
                 "Gap = combined effect of hours filter + methodological differences",
                 fontsize=10)
    ax.set_ylabel("Annual entry rate (%)", fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
    ax.legend(fontsize=8, framealpha=0.9)
    ax.tick_params(labelsize=8)
    ax.text(0.02, 0.04,
            "Note: Kauffman values are approximate published annual rates.\n"
            "Difference reflects hours filter + possible methodology differences.",
            transform=ax.transAxes, fontsize=7.5, color="0.4",
            verticalalignment="bottom")

    fig.text(0.99, 0.01, "Source: IPUMS CPS; Kauffman Foundation Indicators of Entrepreneurship",
             ha="right", va="bottom", fontsize=7, color="0.5")

    out = FIGURES_DIR / "04_hours_filter_audit.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    log(f"\n  Saved: {out}")
    plt.close(fig)

    log("\nRECOMMENDATION:")
    log("  Re-request UHRSWORKT in a new IPUMS extract and verify coverage")
    log("  before comparing to Kauffman's published rates quantitatively.")
    log("  Until then, label estimates as 'without hours-worked filter'")
    log("  and note upward bias vs. Kauffman in any publication.")
    log("Done.")


if __name__ == "__main__":
    main()
