"""
Targeted CPS extract for the Gen-Z-owners-by-industry question (gusto ai_owner_demographics).

Question: do 25-29-year-old business OWNERS pick the same industries in ~2025 (early Gen Z) as
they did in ~2015 (young Millennials)? A clean cohort contrast at a fixed life stage, a decade
apart, on a point-in-time survey (no firm-vintage/stock bias). This is the EXTERNAL benchmark for
the gusto report's age-vs-cohort question.

Pulls ONLY the two endpoint windows (pooled to fatten the thin young-owner cell):
  - 2014, 2015, 2016  (25-29 here = born ~1986-90, young Millennials; pre-AI, pre-COVID)
  - 2024, 2025, 2026  (25-29 here = born ~1996-2000, early Gen Z)
Basic monthly samples, all available months in those years.

Reads IPUMS_API_KEY from keyring (service 'ipums', username 'api_key'); falls back to env.
Downloads raw extract to data/raw/. Microdata is NOT redistributed (IPUMS terms) — only the
aggregated industry shares get carried into the gusto repo.

Run: venv/bin/python scripts/industry_25_29_extract.py [--resume-id N]
"""

import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import keyring
from ipumspy import IpumsApiClient, MicrodataExtract
from ipumspy.api.exceptions import IpumsApiException

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Two pooled endpoint windows, centered on 2015 and 2025.
TARGET_MONTHS = (
    [(y, m) for y in (2014, 2015, 2016) for m in range(1, 13)]
    + [(y, m) for y in (2024, 2025, 2026) for m in range(1, 13)]
)

# CLASSWKR (13=inc SE, 14=uninc SE) + AGE define the owner cell; IND1990 is the time-consistent
# industry (primary), IND the contemporaneous backup; OCC for the optional owner-occupation
# exposure follow-up; WTFINL the population weight; EMPSTAT/UHRSWORKT for optional filters.
VARIABLES = ["CPSIDP", "YEAR", "MONTH", "AGE", "CLASSWKR", "IND1990", "IND",
             "OCC2010", "OCC", "WTFINL", "EMPSTAT", "UHRSWORKT"]


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def get_api_key() -> str:
    """Read from keyring (so the secret never lives in code/env/transcript); fall back to env."""
    return keyring.get_password("ipums", "api_key") or os.environ.get("IPUMS_API_KEY")


def resolve_samples(client, target_months):
    """Pick the basic-monthly (_s) sample per (year, month), falling back to supplement (_b)."""
    available = client.get_all_sample_info("cps")
    selected = []
    for year, month in target_months:
        prefix = f"cps{year}_{month:02d}"
        if f"{prefix}s" in available:
            selected.append(f"{prefix}s")
        elif f"{prefix}b" in available:
            selected.append(f"{prefix}b")
        else:
            log(f"  no sample for {year}-{month:02d} (not yet released) — skipping.")
    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-id", type=int, default=None,
                        help="Resume waiting on an already-submitted extract by ID.")
    args = parser.parse_args()

    client = IpumsApiClient(api_key=get_api_key())

    if args.resume_id:
        log(f"Resuming extract ID {args.resume_id} ...")
        extract = client.get_extract(args.resume_id, collection="cps")
    else:
        log("Resolving available basic-monthly samples for 2014-16 + 2024-26 ...")
        samples = resolve_samples(client, TARGET_MONTHS)
        log(f"  {len(samples)} samples resolved (of {len(TARGET_MONTHS)} targets).")
        extract = MicrodataExtract(
            collection="cps",
            description="ai_owner_demographics: 25-29 owners by industry, 2014-16 vs 2024-26",
            samples=samples,
            variables=VARIABLES,
        )
        client.submit_extract(extract)
        log(f"Submitted. Extract ID: {extract.extract_id} "
            f"(re-run with --resume-id {extract.extract_id} if polling drops)")

    log("Waiting for extract to complete ...")
    while True:
        try:
            client.wait_for_extract(extract)
            break
        except IpumsApiException as e:
            if "timed out" in str(e).lower() or "connection aborted" in str(e).lower():
                log("Polling timed out — retrying in 30s ...")
                time.sleep(30)
            else:
                raise
    log("Extract ready. Downloading ...")
    client.download_extract(extract, download_dir=str(RAW_DIR))
    log(f"Done. Files in {RAW_DIR}")


if __name__ == "__main__":
    main()
