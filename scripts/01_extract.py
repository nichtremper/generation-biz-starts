"""
Step 1: Pull CPS monthly microdata from IPUMS API.

Reads IPUMS_API_KEY from the environment. Prompts at runtime if not set.
Downloads raw extract to data/raw/.
"""

import getpass
import os
from pathlib import Path

from ipumspy import IpumsApiClient, MicrodataExtract, readers

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Target year/month combinations
BASELINE_YEARS = range(2005, 2020)
COVID_YEARS = range(2020, 2023)
RECENT = (
    [(2023, m) for m in range(10, 13)]
    + [(2024, m) for m in range(1, 13)]
    + [(2025, m) for m in range(1, 13)]
)
TARGET_MONTHS = (
    [(y, m) for y in BASELINE_YEARS for m in range(1, 13)]
    + [(y, m) for y in COVID_YEARS for m in range(1, 13)]
    + RECENT
)


def resolve_samples(client: "IpumsApiClient", target_months: list) -> list:
    """
    Query the IPUMS API for available CPS samples and select the best match
    per target (year, month). Prefers _s (basic monthly) over _b (supplement).
    Warns if a target month has no available sample.
    """
    available = client.get_all_sample_info("cps")

    selected = []
    for year, month in target_months:
        prefix = f"cps{year}_{month:02d}"
        s_id = f"{prefix}s"
        b_id = f"{prefix}b"
        if s_id in available:
            selected.append(s_id)
        elif b_id in available:
            selected.append(b_id)
        else:
            print(f"  WARNING: no sample found for {year}-{month:02d}, skipping.")

    return selected

VARIABLES = [
    "CPSIDP",
    "YEAR",
    "MONTH",
    "MISH",
    "CLASSWKR",
    "EMPSTAT",
    "AGE",
    "WTFINL",
    "LNKFW1YWT",
    "SEX",
    "EDUC",
    "RACE",
    "IND",
]


def main():
    api_key = os.environ.get("IPUMS_API_KEY")
    if not api_key:
        api_key = getpass.getpass(
            "IPUMS_API_KEY not found in environment. Enter your API key: "
        )

    client = IpumsApiClient(api_key=api_key)

    print("Resolving available CPS sample IDs from IPUMS...")
    samples = resolve_samples(client, TARGET_MONTHS)
    print(f"  {len(samples)} samples resolved (of {len(TARGET_MONTHS)} targets).")

    extract = MicrodataExtract(
        collection="cps",
        description="Generation biz starts analysis — full sample pull",
        samples=samples,
        variables=VARIABLES,
    )

    print(f"Submitting extract with {len(samples)} samples...")
    client.submit_extract(extract)
    print(f"Extract submitted. ID: {extract.extract_id}")
    print("Waiting for extract to complete (this may take minutes to hours)...")

    client.wait_for_extract(extract)
    print("Extract ready. Downloading...")

    client.download_extract(extract, download_dir=str(RAW_DIR))
    print(f"Download complete. Files saved to: {RAW_DIR}")


if __name__ == "__main__":
    main()
