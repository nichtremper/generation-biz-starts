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
    Validates:
      - CPSIDP != 0 (excludes non-linkable persons)
      - Sex is identical
      - Age differs by 0 or 1
      - T1 is exactly one calendar month after T0 (prevents cross-year spurious matches)
    """
    frames = []
    # Deduplicate: keep one record per (CPSIDP, YEAR, MONTH, MISH) to prevent
    # cross-joins if any CPSIDP appears more than once in a survey month.
    lf = lf.filter(pl.col("CPSIDP") != 0).unique(
        subset=["CPSIDP", "YEAR", "MONTH", "MISH"], keep="first"
    )

    for mish_t0, mish_t1 in MOM_PAIRS:
        t0 = lf.filter(pl.col("MISH") == mish_t0)
        t1 = lf.filter(pl.col("MISH") == mish_t1)

        joined = t0.join(t1, on="CPSIDP", how="inner", suffix="_t1").rename(
            {c: f"{c}_t0" for c in t0.collect_schema().names() if c != "CPSIDP"}
        )

        validated = joined.filter(
            (pl.col("SEX_t0") == pl.col("SEX_t1"))
            & (pl.col("AGE_t1") - pl.col("AGE_t0")).is_between(0, 1)
            # T1 must be exactly one calendar month after T0
            & (pl.col("MONTH_t1") == (pl.col("MONTH_t0") % 12) + 1)
            & (pl.col("YEAR_t1") == pl.col("YEAR_t0") + (pl.col("MONTH_t0") == 12).cast(pl.Int64))
        ).with_columns(pl.lit(f"{mish_t0}_{mish_t1}").alias("mish_pair"))

        frames.append(validated)

    return pl.concat(frames).collect()


def build_yoy_pairs(lf: pl.LazyFrame) -> pl.DataFrame:
    """
    Match persons at MISH=4 (T0) to MISH=8 (T1) — same calendar month, one year later.

    Validates:
      - CPSIDP != 0 (excludes non-linkable persons)
      - Sex is identical
      - Age differs by 0 or 1
      - T1 is the same calendar month exactly one year after T0
    Expect ~10-15% attrition from movers and non-response.
    """
    # Deduplicate before joining (same reason as MOM: prevent cross-joins).
    lf = lf.filter(pl.col("CPSIDP") != 0).unique(
        subset=["CPSIDP", "YEAR", "MONTH", "MISH"], keep="first"
    )

    t0 = lf.filter(pl.col("MISH") == 4)
    t1 = lf.filter(pl.col("MISH") == 8)

    joined = t0.join(t1, on="CPSIDP", how="inner", suffix="_t1").rename(
        {c: f"{c}_t0" for c in t0.collect_schema().names() if c != "CPSIDP"}
    )

    return joined.filter(
        (pl.col("SEX_t0") == pl.col("SEX_t1"))
        & (pl.col("AGE_t1") - pl.col("AGE_t0")).is_between(0, 1)
        # Same calendar month, exactly one year later
        & (pl.col("MONTH_t1") == pl.col("MONTH_t0"))
        & (pl.col("YEAR_t1") == pl.col("YEAR_t0") + 1)
    ).collect()
