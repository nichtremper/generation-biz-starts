# IPUMS CPS Entrepreneurship Analysis: Project Plan

## Research Question

Are people 35 and younger starting businesses in the last 18 months at higher rates than historical averages?

---

## Approach: Longitudinal Self-Employment Transition Tracking

Use CPS's rotation structure to identify **transitions into self-employment** for individuals matched across months, compute an **entry rate** (transitions ÷ eligible population) by age group, and compare the recent period to historical averages.

This method follows the **Kauffman Foundation's New Entrepreneur Rate** methodology, which is well-documented and peer-reviewed.

---

## Data Source & Access

- **Dataset**: IPUMS CPS Monthly Data (ipums.org/cps)
- **API Key**: Generate at ipums.org → Account Profile → API Keys
- **Store as environment variable**: `IPUMS_API_KEY`
- **Python package**: `ipumspy` (official IPUMS client)
  - Docs: https://ipums.github.io/ipumspy
- **Alternative (R)**: `ipumsr`

---

## Variables to Extract

| Variable | Purpose |
|---|---|
| `CPSIDP` | Unique person ID for longitudinal matching |
| `YEAR` | Year |
| `MONTH` | Month |
| `MISH` | Month-in-sample (rotation position — critical for matching) |
| `CLASSWKR` | Class of worker: self-employed incorporated (13) vs. unincorporated (14) vs. wage/salary |
| `EMPSTAT` | Employment status (employed, unemployed, NILF) |
| `AGE` | For generational/age-group filtering |
| `WTFINL` | Base survey weight |
| `LNKFW1YWT` | Linked year-over-year weight (use this if available) |
| `SEX` | Optional subgroup |
| `EDUC` | Optional subgroup |
| `RACE` | Optional subgroup |
| `IND` | Industry (if sector-level cuts are desired) |

---

## Matching Methods: Both Month-Over-Month and Year-Over-Year

CPS uses a **rotating panel**: households are interviewed for 4 months, out for 8, then back for 4. This structure supports two distinct matching strategies, each capturing something different. **Run both.**

---

### Method A: Month-Over-Month (Adjacent Match)

Match the same person at consecutive months within their 4-month stint.

- Pairs: MISH=1→2, MISH=2→3, MISH=3→4 (and same for the second stint: MISH=13→14, 14→15, 15→16)
- Match on `CPSIDP` across adjacent months
- ~1 month between observations

**What it captures**: Rapid entry events — someone who quit a job and launched something, a recent grad who went straight to self-employment, a layoff-to-freelance transition. Very sensitive to short-term gig and side-hustle moves.

**Noisiness to expect**:
- Higher raw transition counts (lots of people dip in and out month-to-month)
- More volatile series — expect large swings, especially around recessions and COVID
- Will pick up "trying self-employment" as much as "starting a business"

**Entry rate formula**:
```
MOM Entry Rate = (# who were not SE at month t, are SE at month t+1) / (# not SE at month t)
```

Aggregate to monthly series. Smooth with a 3-month rolling average if you want to visualize trends.

---

### Method B: Year-Over-Year (Kauffman Method)

Match the same person at MISH=4 and MISH=16 — the same calendar month, exactly one year later.

- MISH=4: End of first 4-month stint
- MISH=16: End of second 4-month stint, 12 months later
- Only one matched pair per person (vs. up to 3 for MOM)

**What it captures**: Durable business formation — someone who was still self-employed a full year after entry. Filters out people who tried it briefly and quit. Closer to "real" small business starts.

**Noisiness to expect**:
- Fewer observations per period (only MISH=4/16 pairs, not all rotation pairs)
- Smoother series, but slower to reflect real-time changes
- ~3-month publication lag + 12-month lookback = you're always seeing 15-month-old entry behavior at the leading edge

**Entry rate formula**:
```
YOY Entry Rate = (# who were not SE at MISH=4, are SE at MISH=16) / (# not SE at MISH=4)
```

Aggregate to quarterly series.

---

### Using Both Together

The two series tell complementary stories:

| | Month-Over-Month | Year-Over-Year |
|---|---|---|
| **Signal** | Who's trying self-employment | Who's sticking with it |
| **Lag** | Near real-time | ~15 months at leading edge |
| **Volatility** | High | Low |
| **Best for** | Detecting inflection points fast | Confirming durable trends |

A divergence between the two is itself analytically interesting — e.g., if MOM entry spikes but YOY doesn't follow, it suggests a lot of failed or abandoned attempts. If both move together, you're seeing genuine formation.

---

## Step-by-Step Pipeline

### Step 1: Pull Data via API

`01_extract.py` should look for the API key in the environment first. If it isn't found, prompt the user to enter it at runtime rather than failing silently or hardcoding it.

```python
import os
import getpass
from ipumspy import IpumsApiClient, CpsExtract

api_key = os.environ.get("IPUMS_API_KEY")
if not api_key:
    api_key = getpass.getpass("IPUMS_API_KEY not found in environment. Enter your API key: ")

client = IpumsApiClient(api_key=api_key)

extract = CpsExtract(
    samples=["cps2005_01m", ...],  # list all relevant monthly samples
    variables=["CPSIDP", "YEAR", "MONTH", "MISH", "CLASSWKR",
               "EMPSTAT", "AGE", "WTFINL", "LNKFW1YWT", "SEX", "EDUC", "RACE", "IND"]
)

client.submit_extract(extract)
client.wait_for_extract(extract)  # async — may take minutes to hours
client.download_extract(extract, download_dir="./data/raw")
```

Sample coverage:
- **Historical baseline**: 2005–2019
- **COVID era** (flag separately, do not include in baseline): 2020–2022
- **Recent period**: October 2023 – most recent available month

### Step 2: Build Matched Pairs (Both Methods)

**Method A — Month-Over-Month pairs:**
1. Load raw CPS data
2. For each person-month, create a "next month" record by shifting MISH forward by 1 within the same rotation stint (MISH 1→2, 2→3, 3→4, 13→14, 14→15, 15→16)
3. Merge on `CPSIDP` + consecutive MISH
4. Validate: age should be identical or +1, sex must match — drop discrepancies
5. Output: `matched_mom.parquet`

**Method B — Year-Over-Year pairs:**
1. Separate records where `MISH == 4` (T0) and `MISH == 16` (T1)
2. Merge on `CPSIDP`
3. Validate: age should differ by exactly 1, sex must match — drop discrepancies
4. Expect ~10–15% attrition from movers and non-response
5. Output: `matched_yoy.parquet`

### Step 3: Classify Transitions

Apply the same classification logic to both matched datasets:

| Label | CLASSWKR at T0 | CLASSWKR at T1 |
|---|---|---|
| **New entrant** | Not self-employed | Self-employed |
| Continuing | Self-employed | Self-employed |
| Exiter | Self-employed | Not self-employed |
| Neither | Not self-employed | Not self-employed |

**Self-employed definition:**
- `CLASSWKR == 13`: Self-employed, incorporated (stronger "real business" signal)
- `CLASSWKR == 14`: Self-employed, unincorporated (includes gig/freelance)
- Run both combined and incorporated-only as separate columns — divergence between them is meaningful

### Step 4: Compute Entry Rates

**For MOM**: compute monthly entry rates, then apply a 3-month rolling average for visualization.

**For YOY**: compute quarterly entry rates (anchored at T1 date).

Formula for both:
```
Entry Rate = (# new entrants in age group) / (# at risk in age group)
```

Where **at risk** = persons who were NOT self-employed at T0.

Apply survey weights (`LNKFW1YWT` for YOY if available, `WTFINL` from T0 for MOM).

**Age groups:**
- 35 and under (primary focus)
- 36–50
- 51+
- Optional: birth-year cohort cuts for generational framing (Millennials: born 1981–1996; Gen Z: born 1997+)

### Step 5: Compare Recent vs. Historical

- **Baseline**: Quarterly entry rates, 2005–2019
  - Compute mean and standard deviation per quarter-of-year (to control for seasonality)
- **COVID era**: 2020–2022 — report separately, do not fold into baseline
- **Recent period**: October 2023 – present
  - Compare each quarter to the baseline distribution
  - Flag quarters that are >1 SD above/below baseline mean

---

## Key Analytical Caveats

**Sample size**: After matching, age-filtering to ≤35, and capturing only transitions, expect a few hundred weighted observations per quarter. Implications:
- Quarterly aggregation is more reliable than monthly
- Confidence intervals will be wide — report them
- Sub-group cuts (by industry, sex, race) will get thin quickly

**Incorporated vs. unincorporated**: Unincorporated self-employment is highly sensitive to gig work (Uber, DoorDash, freelance). For traditional small business formation, look at incorporated self-employment or report both tracks separately.

**COVID distortion**: 2020–2022 saw massive swings in self-employment from gig surges, PPP effects, and pandemic exits. Exclude from baseline; treat as its own analytical period if relevant.

**Age vs. generation**: A fixed ≤35 cutoff is simpler. A generational cohort approach (track Millennials and Gen Z by birth year) is richer but adds complexity.

---

## Directory Structure (Suggested)

```
project/
├── PLAN.md                  ← this file
├── .gitignore               ← must include /data and .env
├── .env                     ← IPUMS_API_KEY (gitignored)
├── data/                    ← gitignored — never pushed to git
│   ├── raw/                 ← downloaded IPUMS extracts
│   └── processed/
│       ├── matched_mom.parquet   ← month-over-month pairs
│       └── matched_yoy.parquet   ← year-over-year pairs
├── scripts/
│   ├── 01_extract.py        ← API pull
│   ├── 02_match.py          ← build both MOM and YOY matched pairs
│   ├── 03_classify.py       ← transition coding (applied to both)
│   └── 04_analysis.py       ← entry rates, comparisons, MOM vs YOY divergence
└── src/
    ├── match.py             ← matching logic for both methods
    ├── classify.py          ← transition classification
    └── rates.py             ← entry rate computation and rolling averages
```

**`.gitignore` must include at minimum:**
```
data/
.env
```

No raw or processed data files should ever be committed. If someone clones the repo, they run `01_extract.py` to pull their own copy of the data from IPUMS.

---

## Reference

- Kauffman Indicators of Entrepreneurship: https://indicators.kauffman.org
- Kauffman methodology paper describes the exact CPS variable approach this project replicates
- IPUMS CPS variable documentation: https://cps.ipums.org/cps-action/variables/group
- ipumspy docs: https://ipums.github.io/ipums