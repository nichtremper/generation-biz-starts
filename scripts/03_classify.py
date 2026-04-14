"""
Step 3: Classify self-employment transitions in matched pairs.

Reads:
  data/processed/matched_mom.parquet
  data/processed/matched_yoy.parquet

Outputs (in-place update to same files with added columns):
  data/processed/matched_mom.parquet
  data/processed/matched_yoy.parquet
"""

from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.classify import classify_transitions

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"


def main():
    for filename in ["matched_mom.parquet", "matched_yoy.parquet"]:
        path = PROCESSED_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"{path} not found. Run 02_match.py first.")

        df = pd.read_parquet(path)
        print(f"Classifying transitions in {filename} ({len(df):,} pairs)...")

        df = classify_transitions(df)

        entrant_count = df["new_entrant"].sum()
        entrant_inc_count = df["new_entrant_inc"].sum()
        print(f"  New entrants (combined SE):       {entrant_count:,}")
        print(f"  New entrants (incorporated only): {entrant_inc_count:,}")

        df.to_parquet(path, index=False)
        print(f"  Saved: data/processed/{filename}\n")


if __name__ == "__main__":
    main()
