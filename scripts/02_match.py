"""
Step 2: Build month-over-month and year-over-year matched person pairs.
Also computes the monthly SE stock (cross-sectional counts and shares).

Reads raw IPUMS extract from data/raw/, converts to chunked parquet on first run
(bounded memory — one chunk at a time), then uses Polars lazy frames for joins.
Outputs:
  data/processed/matched_mom.parquet
  data/processed/matched_yoy.parquet
  data/processed/se_stock.parquet
"""

from datetime import datetime
from pathlib import Path
import shutil
import sys

import polars as pl
from ipumspy import readers

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.match import build_mom_pairs, build_yoy_pairs

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
CHUNK_DIR = RAW_DIR / "chunks"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Rows per chunk — tune down if still hitting memory limits
CHUNK_SIZE = 500_000


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def convert_to_chunks() -> Path:
    """
    Parse the IPUMS fixed-width extract in chunks and write each to a separate
    parquet file in data/raw/chunks/. Only loads CHUNK_SIZE rows at a time.
    Returns the chunk directory path.
    """
    ddi_files = list(RAW_DIR.glob("*.xml"))
    dat_files = list(RAW_DIR.glob("*.dat.gz")) + list(RAW_DIR.glob("*.dat"))

    if not ddi_files or not dat_files:
        raise FileNotFoundError(
            f"No IPUMS extract files found in {RAW_DIR}. Run 01_extract.py first."
        )

    ddi = readers.read_ipums_ddi(ddi_files[0])
    log(f"  DDI read. Parsing in chunks of {CHUNK_SIZE:,} rows...")

    if CHUNK_DIR.exists():
        shutil.rmtree(CHUNK_DIR)
    CHUNK_DIR.mkdir()

    chunks = readers.read_microdata_chunked(ddi, dat_files[0], chunksize=CHUNK_SIZE)
    total_rows = 0

    for i, chunk in enumerate(chunks):
        df = pl.from_pandas(chunk)
        out_path = CHUNK_DIR / f"chunk_{i:04d}.parquet"
        df.write_parquet(out_path)
        total_rows += len(df)
        log(f"  Chunk {i:>3}: {len(df):,} rows written ({total_rows:,} total) -> {out_path.name}")

    log(f"  Conversion complete: {i + 1} chunks, {total_rows:,} total rows.")
    return CHUNK_DIR


def load_or_convert() -> pl.LazyFrame:
    """
    Return a Polars LazyFrame over the raw CPS data. Converts to chunked parquet
    on first run; subsequent runs scan existing chunks directly.
    """
    existing_chunks = sorted(CHUNK_DIR.glob("chunk_*.parquet")) if CHUNK_DIR.exists() else []

    if existing_chunks:
        log(f"Found {len(existing_chunks)} existing chunk files. Scanning lazily...")
        return pl.scan_parquet(str(CHUNK_DIR / "chunk_*.parquet"))

    log("No chunk cache found — converting fixed-width extract to parquet chunks (one-time cost)...")
    convert_to_chunks()
    return pl.scan_parquet(str(CHUNK_DIR / "chunk_*.parquet"))


def compute_se_stock(lf: pl.LazyFrame) -> pl.DataFrame:
    """
    Compute monthly SE stock (counts and shares) from the full cross-sectional CPS.

    A single lazy scan — filters, flags, and aggregates in one pass.

    Numerator:  EMPSTAT in [10, 12] AND CLASSWKR in [13, 14] (employed + SE).
                CLASSWKR is NIU for non-employed, so the EMPSTAT guard is required.
    Denominator (employed): EMPSTAT in [10, 12].
    Denominator (labor force): EMPSTAT in [10, 12, 20, 21, 22].

    No hours-worked filter is applied (stock = head count, not transition-based).

    Returns a pandas DataFrame with one row per (YEAR, MONTH, age_group) covering
    the four non-overlapping groups plus a 20_to_64 aggregate.
    """
    EMPLOYED = [10, 12]
    UNEMPLOYED = [20, 21, 22]
    SE_CODES = [13, 14]

    result = (
        lf
        .filter(pl.col("EMPSTAT").is_in(EMPLOYED + UNEMPLOYED))
        .filter(pl.col("AGE").is_between(20, 64))
        .with_columns([
            # SE flags — meaningful only for employed; False for unemployed (CLASSWKR=0)
            (pl.col("EMPSTAT").is_in(EMPLOYED) & pl.col("CLASSWKR").is_in(SE_CODES))
            .cast(pl.Float64).alias("is_se"),
            (pl.col("EMPSTAT").is_in(EMPLOYED) & (pl.col("CLASSWKR") == 13))
            .cast(pl.Float64).alias("is_se_inc"),
            # Employed flag (for employed-only denominator)
            pl.col("EMPSTAT").is_in(EMPLOYED).cast(pl.Float64).alias("is_employed"),
            # Age group (mutually exclusive 4-way split; 20-64 aggregate added below)
            pl.when(pl.col("AGE").is_between(20, 34)).then(pl.lit("20_to_34"))
            .when(pl.col("AGE").is_between(35, 44)).then(pl.lit("35_to_44"))
            .when(pl.col("AGE").is_between(45, 54)).then(pl.lit("45_to_54"))
            .otherwise(pl.lit("55_to_64")).alias("age_group"),
        ])
        .with_columns([
            (pl.col("WTFINL") * pl.col("is_se")).alias("wt_se"),
            (pl.col("WTFINL") * pl.col("is_se_inc")).alias("wt_se_inc"),
            (pl.col("WTFINL") * pl.col("is_employed")).alias("wt_employed"),
        ])
        .group_by(["YEAR", "MONTH", "age_group"])
        .agg([
            pl.col("wt_se").sum(),
            pl.col("wt_se_inc").sum(),
            pl.col("wt_employed").sum(),
            pl.col("WTFINL").sum().alias("wt_lf"),   # all LF (employed + unemployed)
            pl.len().alias("n_obs"),
        ])
        .collect()
    )

    # 20–64 aggregate: sum all four age groups
    total = (
        result
        .group_by(["YEAR", "MONTH"])
        .agg([
            pl.col("wt_se").sum(),
            pl.col("wt_se_inc").sum(),
            pl.col("wt_employed").sum(),
            pl.col("wt_lf").sum(),
            pl.col("n_obs").sum(),
        ])
        .with_columns(pl.lit("20_to_64").alias("age_group"))
        .select(result.columns)  # enforce matching column order before concat
    )

    result = pl.concat([result, total]).with_columns([
        (pl.col("wt_se") / pl.col("wt_employed")).alias("se_share_employed"),
        (pl.col("wt_se_inc") / pl.col("wt_employed")).alias("se_share_inc_employed"),
        (pl.col("wt_se") / pl.col("wt_lf")).alias("se_share_lf"),
        (pl.col("wt_se_inc") / pl.col("wt_lf")).alias("se_share_inc_lf"),
    ])

    return result.to_pandas()


def main():
    lf = load_or_convert()

    log("Building month-over-month pairs (6 MISH joins)...")
    mom = build_mom_pairs(lf)
    log(f"  MOM pairs: {len(mom):,}. Writing parquet...")
    mom.write_parquet(PROCESSED_DIR / "matched_mom.parquet")
    log("  Saved: data/processed/matched_mom.parquet")

    log("Building year-over-year pairs (MISH 4 → 16 join)...")
    yoy = build_yoy_pairs(lf)
    log(f"  YOY pairs: {len(yoy):,}. Writing parquet...")
    yoy.write_parquet(PROCESSED_DIR / "matched_yoy.parquet")
    log("  Saved: data/processed/matched_yoy.parquet")

    log("Computing SE stock (cross-sectional counts and shares)...")
    stock = compute_se_stock(lf)
    log(f"  Stock rows: {len(stock):,}. Writing parquet...")
    stock.to_parquet(PROCESSED_DIR / "se_stock.parquet", index=False)
    log("  Saved: data/processed/se_stock.parquet")


if __name__ == "__main__":
    main()
