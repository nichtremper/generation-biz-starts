"""
Owner's own-occupation AI-exposure (Eloundou beta) for 25-29 owners, ~2015 vs ~2025 (CPS).

The one CPS cut that touches the gusto report's actual measure. For each 25-29 self-employed owner
we take their OWN occupation (OCC2010, IPUMS's time-harmonized 2010-census-occupation code), bridge
it to SOC via the Census "2010 Occupation Code List" crosswalk (2010 Census Code -> 2010 SOC), and
attach the Eloundou human_rating_beta (O*NET-SOC collapsed to 6-digit SOC). We report the
WTFINL-weighted mean owner-occupation beta per period.

This is the OWNER'S OWN role only (CPS can't see the owner's employees), so it speaks to the
"what the owner themselves does" dimension, not the firm's whole workforce.

OCC2010 is harmonized to the 2010 census basis for BOTH windows, so one crosswalk covers both years
(time-consistent, same logic as IND1990 for industry). The Eloundou O*NET-SOC is ~2018/2019-SOC
based, so the join to 2010-SOC isn't perfect; the printed match rate flags any drift.

Crosswalk: data/crosswalk/2010-occ-codes-with-crosswalk-from-2002-2011.xls (US Census Bureau).
Beta source: gusto repo's data/exposure/occ_level.csv (read-only; NOT copied here).
Writes one aggregate CSV to data/processed/. Run: venv/bin/python scripts/owner_occ_exposure.py
"""

import re
import warnings
from pathlib import Path

import pandas as pd

import industry_25_29_analysis as A  # reuse load_extract(), PERIODS, SE_INC/SE_ALL, wshare, OUT_DIR

warnings.simplefilter("ignore")
ELOUNDOU = Path("/Users/nicholas.tremper/git/gusto-insights/ai_owner_demographics/"
                "data/exposure/occ_level.csv")
XWALK = Path(__file__).parent.parent / "data" / "crosswalk" / "2010-occ-codes-with-crosswalk-from-2002-2011.xls"
SOC_RE = re.compile(r"^\d\d-\d{4}$")


def soc_beta_tables() -> tuple:
    """Two Eloundou beta lookups from O*NET-SOC ('11-1011.00'):
      detailed: 6-digit SOC '11-1011' -> mean beta
      stem:     broad-group stem '11-101' -> mean beta (covers crosswalk SOCs coded to a broad
                group ending in 0, e.g. '37-3010', which won't match a detailed key)."""
    occ = pd.read_csv(ELOUNDOU)
    occ["soc6"] = occ["O*NET-SOC Code"].astype(str).str[:7]    # 'XX-XXXX'
    occ["stem"] = occ["O*NET-SOC Code"].astype(str).str[:6]    # 'XX-XXX' (broad group)
    detailed = occ.groupby("soc6")["human_rating_beta"].mean().to_dict()
    stem = occ.groupby("stem")["human_rating_beta"].mean().to_dict()
    return detailed, stem


def beta_for(soc, detailed: dict, stem: dict):
    """Detailed 6-digit match first; else fall back to the broad-group (stem) average."""
    if not isinstance(soc, str):
        return None
    if soc in detailed:
        return detailed[soc]
    return stem.get(soc[:6])


def census2010_to_soc() -> dict:
    """Census 2010 occupation code (int) -> 2010 SOC ('XX-XXXX'). Keeps only detail rows (a single
    4-digit census code mapping to a single SOC); skips the interspersed major-group range rows."""
    raw = pd.read_excel(XWALK, sheet_name="2010OccCodeList", header=4, engine="xlrd")
    raw.columns = [str(c).strip() for c in raw.columns]
    code_col = next(c for c in raw.columns if "Census Code" in c)
    soc_col = next(c for c in raw.columns if "SOC" in c)
    out = {}
    for _, r in raw[[code_col, soc_col]].dropna().iterrows():
        soc = str(r[soc_col]).strip()
        try:
            code = int(str(r[code_col]).strip())          # "0010" -> 10; "0010-0950" -> ValueError (skip)
        except ValueError:
            continue
        if SOC_RE.match(soc):                              # single SOC only; skip "11-0000 - 13-0000"
            out[code] = soc
    return out


def main():
    detailed, stem = soc_beta_tables()
    xwalk = census2010_to_soc()
    print(f"crosswalk: {len(xwalk)} detail census-2010 codes -> SOC | Eloundou: "
          f"{len(detailed)} detailed + {len(stem)} broad-group betas")

    df = A.load_extract()
    for c in ["AGE", "YEAR", "CLASSWKR", "OCC2010", "WTFINL"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["YEAR"].isin(A.PERIODS.keys())]
    young = df[(df["AGE"] >= 25) & (df["AGE"] <= 29)].copy()
    young["period"] = young["YEAR"].map(A.PERIODS)
    young["soc"] = young["OCC2010"].map(xwalk)
    young["occ_beta"] = young["soc"].map(lambda s: beta_for(s, detailed, stem))

    rows = []
    for owner_def, codes in [("incorporated_SE", A.SE_INC), ("all_SE", A.SE_ALL)]:
        owners = young[young["CLASSWKR"].isin(codes)]
        for period in ["2015 (2014-16)", "2025 (2024-26)"]:
            d = owners[owners["period"] == period]
            matched = d[d["occ_beta"].notna()]
            w = pd.to_numeric(matched["WTFINL"], errors="coerce").fillna(0)
            mean_beta = float((w * matched["occ_beta"]).sum() / w.sum()) if w.sum() else float("nan")
            rows.append(dict(owner_def=owner_def, period=period, mean_owner_occ_beta=mean_beta,
                             soc_match_rate=A.wshare(d, d["occ_beta"].notna()),
                             n_unweighted=len(d), n_matched=len(matched)))
    out = pd.DataFrame(rows)
    out.to_csv(A.OUT_DIR / "owner_25_29_occ_exposure_by_period.csv", index=False)

    print("\n=== 25-29 owners' OWN-occupation AI-exposure (Eloundou beta), 2015 vs 2025 ===")
    for od in ["incorporated_SE", "all_SE"]:
        sub = out[out["owner_def"] == od].set_index("period")
        a = sub.loc["2015 (2014-16)"]; b = sub.loc["2025 (2024-26)"]
        print(f"  [{od:15}] 2015 beta {a['mean_owner_occ_beta']:.3f} -> 2025 {b['mean_owner_occ_beta']:.3f}  "
              f"(match {a['soc_match_rate']:.0%}/{b['soc_match_rate']:.0%}; n {a['n_unweighted']:,}/{b['n_unweighted']:,})")
    print(f"\nWrote {A.OUT_DIR / 'owner_25_29_occ_exposure_by_period.csv'}")


if __name__ == "__main__":
    main()
