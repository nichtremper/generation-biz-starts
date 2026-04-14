# Session 1 — Project Setup & Pipeline Build
Dates: 2026-04-13 / 2026-04-14

## What we did

### Repository initialization
- Created `CLAUDE.md` at the repo root documenting the project goal, pipeline steps, architecture, key variables, and analytical caveats for future Claude sessions.
- Updated the global `~/.claude/CLAUDE.md` to broaden the working directory restriction from a single stale path to `/Users/nichtremper/git` (covering all projects). Later also added `~/.config/` to that restriction.

### Environment
- Created `.venv` (Python virtual environment).
- Created `requirements.txt` with: `ipumspy`, `pandas`, `pyarrow`, `polars`, `python-dotenv`.
- Added `data/` to `.gitignore` so raw and processed IPUMS extracts are never committed.

### Source modules (`src/`)
- `match.py` — builds MOM (month-over-month) and YOY (year-over-year) matched person pairs from CPS microdata using Polars lazy frames. MOM pairs consecutive MISH values within a rotation stint; YOY pairs MISH=4 to MISH=16 one year later. Both validate on age (±1) and sex (exact match).
- `classify.py` — codes each matched pair as new entrant / continuing / exiter / neither, for both combined SE (CLASSWKR 13 or 14) and incorporated-only (CLASSWKR 13) tracks.
- `rates.py` — computes weighted entry rates (MOM monthly with 3-month rolling average; YOY quarterly), baseline stats (mean ± SD per seasonal bucket, 2005–2019), and flags recent quarters >1 SD above/below baseline.

### Pipeline scripts (`scripts/`)
- `01_extract.py` — resolves valid IPUMS sample IDs by querying the API (`get_all_sample_info`), then submits a single batch extract and downloads to `data/raw/`. Fixed a bug where sample IDs were hardcoded with an `_m` suffix; correct suffixes are `_s` (basic monthly) or `_b` (supplement), varying by month. All print statements use `[HH:MM:SS]` timestamps.
- `02_match.py` — converts raw IPUMS fixed-width extract to chunked parquet files (`data/raw/chunks/`) in memory-safe 500k-row increments, then uses Polars lazy joins to build matched pairs. Outputs `data/processed/matched_mom.parquet` and `data/processed/matched_yoy.parquet`. Skips conversion on re-runs if chunks already exist.
- `03_classify.py` — adds transition columns to both parquet files in place. Timestamped.
- `04_analysis.py` — computes entry rates, compares recent period to baseline, prints summary tables, saves rate parquets to `data/processed/`. Timestamped.

### Performance refactor (`02_match.py`)
- Original approach loaded the entire fixed-width file into pandas (~40GB RAM spike on MacBook).
- Switched to chunked reading via `read_microdata(..., chunksize=500_000)` — pandas holds one chunk at a time, converts to Polars, writes to parquet, then drops it.
- Polars `scan_parquet("chunks/*.parquet")` lazy-scans all chunks for joins without loading everything into memory.
- `CHUNK_SIZE = 500_000` is tunable at the top of the script if memory is still tight.

## Where things stand
- `01_extract.py` completed successfully. Extract ID: 1. Raw files are in `data/raw/`.
- `02_match.py` is ready to run with the memory-safe chunked approach.
- Steps 3 and 4 are written and waiting.

## Next steps
```bash
source .venv/bin/activate
pip install -r requirements.txt   # picks up polars
python scripts/02_match.py
python scripts/03_classify.py
python scripts/04_analysis.py
```

## Key decisions made
- Sample coverage: baseline 2005–2019, COVID era 2020–2022 (kept separate, never folded into baseline), recent Oct 2023–present.
- Weight strategy: `WTFINL` for MOM, `LNKFW1YWT` (with fallback to `WTFINL`) for YOY.
- Always produce two SE tracks in parallel: combined (inc + uninc) and incorporated-only. Divergence between them signals gig vs. real business formation.
- All scripts use a `log()` helper with `[HH:MM:SS]` timestamps and `flush=True` on every progress print.
