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
"""

import pandas as pd

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
    """
    df = df.copy()

    # Combined SE (incorporated + unincorporated)
    df["se_t0"] = _is_se(df["CLASSWKR_t0"], SE_CODES)
    df["se_t1"] = _is_se(df["CLASSWKR_t1"], SE_CODES)

    # Incorporated only
    df["se_inc_t0"] = _is_se(df["CLASSWKR_t0"], SE_INCORPORATED)
    df["se_inc_t1"] = _is_se(df["CLASSWKR_t1"], SE_INCORPORATED)

    # Transition labels — combined
    df["new_entrant"] = ~df["se_t0"] & df["se_t1"]
    df["continuing"] = df["se_t0"] & df["se_t1"]
    df["exiter"] = df["se_t0"] & ~df["se_t1"]
    df["neither"] = ~df["se_t0"] & ~df["se_t1"]

    # Transition labels — incorporated only
    df["new_entrant_inc"] = ~df["se_inc_t0"] & df["se_inc_t1"]
    df["continuing_inc"] = df["se_inc_t0"] & df["se_inc_t1"]
    df["exiter_inc"] = df["se_inc_t0"] & ~df["se_inc_t1"]
    df["neither_inc"] = ~df["se_inc_t0"] & ~df["se_inc_t1"]

    # Denominator: employed non-SE at T0 (Kauffman convention)
    # Excludes unemployed, NILF, and children — only wage/salary workers at risk
    employed_t0 = df["EMPSTAT_t0"].isin(EMPLOYED_CODES)
    df["at_risk"] = employed_t0 & ~df["se_t0"]
    df["at_risk_inc"] = employed_t0 & ~df["se_inc_t0"]

    return df
