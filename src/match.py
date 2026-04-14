"""
Matching logic for building MOM and YOY person-pair datasets from CPS microdata.
Uses Polars lazy frames for parallel, out-of-core join operations.
"""

import polars as pl

# MISH pairs that represent valid consecutive month-over-month transitions.
# IPUMS CPS codes the rotation as 1-8: first stint = 1-4, second stint = 5-8.
MOM_PAIRS = [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (7, 8)]


def build_mom_pairs(lf: pl.LazyFrame) -> pl.DataFrame:
    """
    Match persons at consecutive MISH values within a rotation stint.

    Runs all 6 MISH pairs as lazy joins, collects once at the end.
    Validates that sex is identical and age differs by at most 1.
    """
    frames = []

    for mish_t0, mish_t1 in MOM_PAIRS:
        t0 = lf.filter(pl.col("MISH") == mish_t0)
        t1 = lf.filter(pl.col("MISH") == mish_t1)

        joined = t0.join(t1, on="CPSIDP", how="inner", suffix="_t1").rename(
            {c: f"{c}_t0" for c in t0.collect_schema().names() if c != "CPSIDP"}
        )

        validated = joined.filter(
            (pl.col("SEX_t0") == pl.col("SEX_t1"))
            & (pl.col("AGE_t1") - pl.col("AGE_t0")).is_between(0, 1)
        ).with_columns(pl.lit(f"{mish_t0}_{mish_t1}").alias("mish_pair"))

        frames.append(validated)

    return pl.concat(frames).collect()


def build_yoy_pairs(lf: pl.LazyFrame) -> pl.DataFrame:
    """
    Match persons at MISH=4 (T0) to MISH=16 (T1) — same calendar month, one year later.

    Validates that sex is identical and age differs by exactly 1.
    Expect ~10-15% attrition from movers and non-response.
    """
    t0 = lf.filter(pl.col("MISH") == 4)
    t1 = lf.filter(pl.col("MISH") == 8)  # IPUMS codes second stint as 5-8, not 13-16

    joined = t0.join(t1, on="CPSIDP", how="inner", suffix="_t1").rename(
        {c: f"{c}_t0" for c in t0.collect_schema().names() if c != "CPSIDP"}
    )

    return joined.filter(
        (pl.col("SEX_t0") == pl.col("SEX_t1"))
        & (pl.col("AGE_t1") - pl.col("AGE_t0") == 1)
    ).collect()
