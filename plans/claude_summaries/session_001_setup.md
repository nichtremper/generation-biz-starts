# Session 1 — Project Setup & Pipeline Build
Date: 2026-04-13

## What we did

### Repository initialization
- Created `CLAUDE.md` at the repo root documenting the project goal, pipeline steps, architecture, key variables, and analytical caveats for future Claude sessions.
- Updated the global `~/.claude/CLAUDE.md` to broaden the working directory restriction from a single stale path to `/Users/nichtremper/git` (covering all projects).

### Environment
- Created `.venv` (Python virtual environment).
- Created `requirements.txt` with: `ipumspy`, `pandas`, `pyarrow`, `python-dotenv`.
- Added `data/` to `.gitignore` so raw and processed IPUMS extracts are never committed.

### Source modules (`src/`)
- `match.py` — builds MOM (month-over-month) and YOY (year-over-year) matched person pairs from CPS microdata. MOM pairs consecutive MISH values within a rotation stint; YOY pairs MISH=4 to MISH=16 one year later. Both validate on age (±1) and sex (exact match).
- `classify.py` — codes each matched pair as new entrant / continuing / exiter / neither, for both combined SE (CLASSWKR 13 or 14) and incorporated-only (CLASSWKR 13) tracks.
- `rates.py` — computes weighted entry rates (MOM monthly with 3-month rolling average; YOY quarterly), baseline stats (mean ± SD per seasonal bucket, 2005–2019), and flags recent quarters >1 SD above/below baseline.

### Pipeline scripts (`scripts/`)
- `01_extract.py` — resolves valid IPUMS sample IDs by querying the API (`get_all_sample_info`), then submits a single batch extract and downloads to `data/raw/`. Fixed a bug where sample IDs were hardcoded with an `_m` suffix; correct suffixes are `_s` (basic monthly) or `_b` (supplement), varying by month.
- `02_match.py` — loads raw IPUMS extract and outputs `data/processed/matched_mom.parquet` and `data/processed/matched_yoy.parquet`.
- `03_classify.py` — adds transition columns to both parquet files in place.
- `04_analysis.py` — computes entry rates, compares recent period to baseline, prints summary tables, and saves rate parquets to `data/processed/`.

## Where things stand
`01_extract.py` is currently running. The extract has been submitted to IPUMS (Extract ID: 1) and is being compiled on their servers. Once the download completes, run steps 2–4 in sequence.

## Key decisions made
- Sample coverage: baseline 2005–2019, COVID era 2020–2022 (kept separate, never folded into baseline), recent Oct 2023–present.
- Weight strategy: `WTFINL` for MOM, `LNKFW1YWT` (with fallback to `WTFINL`) for YOY.
- Always produce two SE tracks in parallel: combined (inc + uninc) and incorporated-only. Divergence between them signals gig vs. real business formation.
