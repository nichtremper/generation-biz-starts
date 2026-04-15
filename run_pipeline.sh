#!/usr/bin/env bash
set -euo pipefail

log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

usage() {
    echo "Usage: $0 [--from-step N]"
    echo ""
    echo "  --from-step N   Start from step N (1–5). Default: 1."
    echo "                  Step 1 (extract) submits a new IPUMS request and can"
    echo "                  take minutes to hours. Skip it with --from-step 2 if"
    echo "                  raw data already exists in data/raw/."
    exit 1
}

FROM_STEP=1

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-step)
            FROM_STEP="${2:?--from-step requires a value}"
            shift 2
            ;;
        -h|--help) usage ;;
        *) echo "Unknown argument: $1"; usage ;;
    esac
done

if ! [[ "$FROM_STEP" =~ ^[1-5]$ ]]; then
    echo "Error: --from-step must be 1–5, got: $FROM_STEP"
    exit 1
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

log "=== Generation Business Starts Pipeline (starting at step $FROM_STEP) ==="

run_step() {
    local n="$1" label="$2" script="$3"
    if [[ "$n" -ge "$FROM_STEP" ]]; then
        log "Step $n/5: $label"
        python "$script"
    else
        log "Step $n/5: $label — skipped (--from-step $FROM_STEP)"
    fi
}

run_step 1 "Extracting CPS data from IPUMS..."   scripts/01_extract.py
run_step 2 "Building matched person pairs..."     scripts/02_match.py
run_step 3 "Classifying transitions..."           scripts/03_classify.py
run_step 4 "Computing entry rates and baseline comparison..." scripts/04_analysis.py
run_step 5 "Generating visualizations..."         scripts/05_visualize.py

log "=== Pipeline complete ==="
