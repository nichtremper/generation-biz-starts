# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a data analysis project answering: **Are people 35 and younger starting businesses at higher rates than historical averages?** It uses IPUMS CPS monthly microdata to track transitions into self-employment, following the Kauffman Foundation's New Entrepreneur Rate methodology.

## Environment Setup

- **API Key**: `IPUMS_API_KEY` environment variable (or `.env` file — gitignored). Scripts prompt for it at runtime if not set.
- **Python packages**: `ipumspy`, `pandas`, `pyarrow`
- **Data directory**: `data/` is gitignored — never commit raw or processed data. Anyone cloning the repo must run `01_extract.py` to pull their own IPUMS extract.

## Pipeline Scripts (run in order)

```bash
python scripts/01_extract.py   # Pull CPS data from IPUMS API (async — may take minutes to hours)
python scripts/02_match.py     # Build MOM and YOY matched person pairs
python scripts/03_classify.py  # Code transitions for each matched pair
python scripts/04_analysis.py  # Compute entry rates, compare recent vs. historical
```

## Architecture

**Two parallel matching methods** run throughout the pipeline:

- **Method A — Month-Over-Month (MOM)**: Match persons at consecutive MISH values within a rotation stint (MISH 1→2, 2→3, 3→4, 13→14, 14→15, 15→16). Captures rapid/gig entry. High volatility. Output: `data/processed/matched_mom.parquet`
- **Method B — Year-Over-Year (YOY)**: Match MISH=4 to MISH=16 for the same person (same calendar month, one year later). Captures durable business formation. Lower volatility, ~15-month lag. Output: `data/processed/matched_yoy.parquet`

**Key logic modules** in `src/`:
- `match.py` — matching logic for both methods, with validation (age ±1, sex must match)
- `classify.py` — transition coding: new entrant / continuing / exiter / neither; both combined SE and incorporated-only tracks
- `rates.py` — entry rate computation using survey weights, rolling averages

**Entry rate formula**: `(# not-SE at T0 who are SE at T1) / (# not-SE at T0)`, weighted by `LNKFW1YWT` (YOY) or `WTFINL` from T0 (MOM).

## Key Variables

| Variable | Role |
|---|---|
| `CPSIDP` | Person ID for longitudinal matching |
| `MISH` | Month-in-sample (rotation position) — critical for matching |
| `CLASSWKR` | 13 = SE incorporated, 14 = SE unincorporated |
| `LNKFW1YWT` | Linked weight for YOY pairs |
| `WTFINL` | Base weight for MOM pairs |

## Analysis Parameters

- **Baseline period**: 2005–2019 (compute mean ± SD per quarter-of-year for seasonality control)
- **COVID era**: 2020–2022 — analyze separately, never fold into baseline
- **Recent period**: October 2023 – present
- **Primary age group**: ≤35; also 36–50 and 51+ for comparison
- **Flag**: quarters >1 SD above/below baseline mean

## Analytical Caveats

- After matching + age-filtering, expect only a few hundred weighted observations per quarter — report confidence intervals
- Unincorporated SE is highly sensitive to gig work; always report incorporated-only separately
- A divergence between MOM and YOY series (MOM spikes but YOY doesn't follow) signals failed/abandoned attempts rather than genuine formation
