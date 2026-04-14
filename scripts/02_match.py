"""
Step 2: Build month-over-month and year-over-year matched person pairs.

Reads raw IPUMS extract from data/raw/, outputs:
  data/processed/matched_mom.parquet
  data/processed/matched_yoy.parquet
"""

from pathlib import Path

import pandas as pd
from ipumspy import readers

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.match import build_mom_pairs, build_yoy_pairs

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_raw() -> pd.DataFrame:
    """Load the IPUMS fixed-width extract from data/raw/."""
    ddi_files = list(RAW_DIR.glob("*.xml"))
    dat_files = list(RAW_DIR.glob("*.dat.gz")) + list(RAW_DIR.glob("*.dat"))

    if not ddi_files or not dat_files:
        raise FileNotFoundError(
            f"No IPUMS extract files found in {RAW_DIR}. Run 01_extract.py first."
        )

    ddi = readers.read_ipums_ddi(ddi_files[0])
    df = readers.read_microdata(ddi, dat_files[0])
    print(f"Loaded {len(df):,} raw person-month records.")
    return df


def main():
    df = load_raw()

    print("Building month-over-month pairs...")
    mom = build_mom_pairs(df)
    print(f"  MOM pairs: {len(mom):,} (dropped {len(df) - len(mom):,} from validation)")
    mom.to_parquet(PROCESSED_DIR / "matched_mom.parquet", index=False)
    print(f"  Saved: data/processed/matched_mom.parquet")

    print("Building year-over-year pairs...")
    yoy = build_yoy_pairs(df)
    print(f"  YOY pairs: {len(yoy):,}")
    yoy.to_parquet(PROCESSED_DIR / "matched_yoy.parquet", index=False)
    print(f"  Saved: data/processed/matched_yoy.parquet")


if __name__ == "__main__":
    main()
