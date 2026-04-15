"""
Transition classification for matched CPS person pairs.

CLASSWKR codes:
  13 = Self-employed, incorporated
  14 = Self-employed, unincorporated
  All other values = not self-employed

EMPSTAT codes used for denominator:
  10 = At work
  12 = Has job, not at work last week
  (Matches Kauffman NER convention: employed civilians not in SE)

Kauffman comparability filters applied:
  - Hours worked filter: SE status at T1 requires UHRSWORKT_t1 >= 15 hrs/week.
    Where UHRSWORKT_t1 is NaN (samples where the variable wasn't collected),
    falls back to CLASSWKR alone.
  - Allocation exclusion (not implemented): IPUMS CPS does not expose
    allocation flags (QCLASSWK, QEMPSTAT, QUHRSWORKT) via the extract API.
    Kauffman drops observations where these were imputed; we cannot replicate
    this filter without the flags.
"""

import logging

import pandas as pd

log = logging.getLogger(__name__)

SE_CODES = {13, 14}
SE_INCORPORATED = {13}
EMPLOYED_CODES = {10, 12}


def _is_se(series: pd.Series, codes: set) -> pd.Series:
    return series.isin(codes)


def classify_transitions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add transition columns to a matched-pair DataFrame.

    Adds four boolean columns for combined SE and four for incorporated-only:
      - new_entrant:  not SE at T0, SE at T1
      - continuing:   SE at T0, SE at T1
      - exiter:       SE at T0, not SE at T1
      - neither:      not SE at T0, not SE at T1

    Also adds:
      - se_t0, se_t1: combined SE flag
      - se_inc_t0, se_inc_t1: incorporated-only SE flag
      - at_risk: employed non-SE at T0 — Kauffman-convention denominator
      - at_risk_inc: employed non-incorporated-SE at T0
      - new_entrant_inc_strict: not SE at all at T0, incorporated SE at T1 (pure new formation)
    """
    df = df.copy()

    # --- Combined SE (incorporated + unincorporated) ---
    df["se_t0"] = _is_se(df["CLASSWKR_t0"], SE_CODES)
    se_classwkr_t1 = _is_se(df["CLASSWKR_t1"], SE_CODES)

    # Kauffman hours filter: SE at T1 requires ≥15 usual hrs/week.
    # Where UHRSWORKT_t1 is NaN (sample gap), fall back to CLASSWKR alone.
    if "UHRSWORKT_t1" in df.columns:
        hours_ok = df["UHRSWORKT_t1"].ge(15) | df["UHRSWORKT_t1"].isna()
        df["se_t1"] = se_classwkr_t1 & hours_ok
    else:
        log.warning(
            "UHRSWORKT_t1 not found — hours worked filter (≥15 hrs/week) not applied."
        )
        df["se_t1"] = se_classwkr_t1

    # --- Incorporated only ---
    df["se_inc_t0"] = _is_se(df["CLASSWKR_t0"], SE_INCORPORATED)
    se_inc_classwkr_t1 = _is_se(df["CLASSWKR_t1"], SE_INCORPORATED)
    if "UHRSWORKT_t1" in df.columns:
        df["se_inc_t1"] = se_inc_classwkr_t1 & hours_ok
    else:
        df["se_inc_t1"] = se_inc_classwkr_t1

    # --- Transition labels — combined ---
    df["new_entrant"] = ~df["se_t0"] & df["se_t1"]
    df["continuing"] = df["se_t0"] & df["se_t1"]
    df["exiter"] = df["se_t0"] & ~df["se_t1"]
    df["neither"] = ~df["se_t0"] & ~df["se_t1"]

    # --- Transition labels — incorporated only ---
    # new_entrant_inc: transitioned to incorporated SE from any non-inc state
    #   (includes uninc→inc restructuring — use new_entrant_inc_strict for pure new formation)
    df["new_entrant_inc"] = ~df["se_inc_t0"] & df["se_inc_t1"]
    # new_entrant_inc_strict: was not SE at all at T0, is incorporated SE at T1
    #   (excludes uninc→inc switchers; cleaner "new incorporated business formation" measure)
    df["new_entrant_inc_strict"] = ~df["se_t0"] & df["se_inc_t1"]
    df["continuing_inc"] = df["se_inc_t0"] & df["se_inc_t1"]
    df["exiter_inc"] = df["se_inc_t0"] & ~df["se_inc_t1"]
    df["neither_inc"] = ~df["se_inc_t0"] & ~df["se_inc_t1"]

    # --- Denominator: employed non-SE at T0 (Kauffman convention) ---
    # Excludes unemployed, NILF, and children — only wage/salary workers at risk
    employed_t0 = df["EMPSTAT_t0"].isin(EMPLOYED_CODES)
    df["at_risk"] = employed_t0 & ~df["se_t0"]
    df["at_risk_inc"] = employed_t0 & ~df["se_inc_t0"]

    return df
