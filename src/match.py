"""
Matching logic for building MOM and YOY person-pair datasets from CPS microdata.
"""

import pandas as pd


# MISH pairs that represent valid consecutive month-over-month transitions
MOM_PAIRS = [(1, 2), (2, 3), (3, 4), (13, 14), (14, 15), (15, 16)]


def build_mom_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Match persons at consecutive MISH values within a rotation stint.

    Produces one row per valid adjacent pair (T0, T1). Validates that
    sex is identical and age differs by at most 1 across the pair.
    """
    records = []

    for mish_t0, mish_t1 in MOM_PAIRS:
        t0 = df[df["MISH"] == mish_t0].copy()
        t1 = df[df["MISH"] == mish_t1].copy()

        merged = t0.merge(t1, on="CPSIDP", suffixes=("_t0", "_t1"))

        # Validation: sex must match, age must be identical or +1
        valid = (merged["SEX_t0"] == merged["SEX_t1"]) & (
            merged["AGE_t1"] - merged["AGE_t0"]
        ).between(0, 1)
        merged = merged[valid].copy()
        merged["mish_pair"] = f"{mish_t0}_{mish_t1}"
        records.append(merged)

    return pd.concat(records, ignore_index=True)


def build_yoy_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Match persons at MISH=4 (T0) to MISH=16 (T1) — same calendar month, one year later.

    Produces one row per valid year-over-year pair. Validates that sex is identical
    and age differs by exactly 1. Expect ~10-15% attrition from movers and non-response.
    """
    t0 = df[df["MISH"] == 4].copy()
    t1 = df[df["MISH"] == 16].copy()

    merged = t0.merge(t1, on="CPSIDP", suffixes=("_t0", "_t1"))

    # Validation: sex must match, age must differ by exactly 1
    valid = (merged["SEX_t0"] == merged["SEX_t1"]) & (
        merged["AGE_t1"] - merged["AGE_t0"] == 1
    )
    return merged[valid].copy()
