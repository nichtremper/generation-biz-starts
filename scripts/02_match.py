"""
Step 2: Build month-over-month and year-over-year matched person pairs.

Reads raw IPUMS extract from data/raw/, converts to chunked parquet on first run
(bounded memory — one chunk at a time), then uses Polars lazy frames for joins.
Outputs:
  data/processed/matched_mom.parquet
  data/processed/matched_yoy.parquet
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


if __name__ == "__main__":
    main()
