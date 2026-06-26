"""
Analysis: industry mix of 25-29-year-old business OWNERS, ~2015 vs ~2025 (CPS).

Reads the targeted extract (industry_25_29_extract.py output in data/raw/), keeps owners aged 25-29,
and tabulates their WTFINL-weighted industry distribution for the two pooled endpoint windows
(2014-16 -> "2015", 2024-26 -> "2025"). Two owner definitions: incorporated SE (CLASSWKR 13,
closest to employer owners) as primary, all SE (13+14) as a wider-N companion.

Industry = contemporaneous IND mapped to NAICS sectors (the census industry codes are NAICS-based;
sector-level ranges are stable enough across the 2012->2017->2022 NAICS census revisions). This
aligns CPS sectors with the gusto report's NAICS-2 sectors. IND1990 (time-harmonized) is carried
for a robustness cross-check.

Writes ONE aggregate CSV (sector x period x owner_def, shares + unweighted n) to data/processed/.
That aggregate is the only thing that crosses into the gusto repo. CPS microdata stays here.

Run: venv/bin/python scripts/industry_25_29_analysis.py
"""

from pathlib import Path

import pandas as pd
from ipumspy import readers

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
OUT_DIR = Path(__file__).parent.parent / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SE_INC = {13}        # incorporated self-employed (CLASSWKR) -- closest to employer owners
SE_ALL = {13, 14}    # incorporated + unincorporated
PERIODS = {2014: "2015 (2014-16)", 2015: "2015 (2014-16)", 2016: "2015 (2014-16)",
           2024: "2025 (2024-26)", 2025: "2025 (2024-26)", 2026: "2025 (2024-26)"}

# Census industry code (NAICS-based, as IPUMS CPS `IND`) -> NAICS-2 sector. Ranges are the standard
# Census-industry -> NAICS sector boundaries; stable at the sector level across the 2012/2017/2022
# revisions. (lo, hi, label) inclusive on the 4-digit census code.
IND_NAICS_RANGES = [
    (170, 290, "Agriculture"), (370, 490, "Mining/Oil&Gas"), (570, 690, "Utilities"),
    (770, 770, "Construction"), (1070, 3990, "Manufacturing"), (4070, 4590, "Wholesale"),
    (4670, 5790, "Retail"), (6070, 6390, "Transport/Warehouse"), (6470, 6780, "Information"),
    (6870, 6992, "Finance/Insurance"), (7070, 7190, "Real Estate"),  # 7070 = RE in the 2013 census vintage (2014-16)
    (7270, 7490, "Professional/Tech"), (7570, 7570, "Mgmt of Companies"),
    (7580, 7790, "Admin/Support/Waste"), (7860, 7890, "Education"),
    (7970, 8470, "Health Care"), (8560, 8590, "Arts/Entertainment"),
    (8660, 8690, "Accommodation/Food"), (8770, 9290, "Other Services"),
    (9370, 9590, "Public Admin"),
]


def naics_sector(ind_code) -> str:
    try:
        c = int(ind_code)
    except (TypeError, ValueError):
        return "Unknown"
    if c == 0:
        return "Unknown"  # IND 0 = NIU / not in universe
    for lo, hi, label in IND_NAICS_RANGES:
        if lo <= c <= hi:
            return label
    return "Other/Unclassified"


# IND1990 (1990 Census industry classification, time-harmonized by IPUMS) -> coarse sector.
# This scheme groups differently from NAICS (eating/drinking sits under Retail; health+education
# under Professional & Related), so it's a COARSER robustness check, not a sector-for-sector match.
# Its value: immune to the NAICS census-code revision between 2015 and 2025.
IND1990_RANGES = [
    (10, 32, "Agriculture/Forestry/Fishing"), (40, 50, "Mining"), (60, 60, "Construction"),
    (100, 392, "Manufacturing"), (400, 472, "Transp/Comm/Utilities"), (500, 571, "Wholesale"),
    (580, 691, "Retail (incl. food)"), (700, 712, "Finance/Insurance/Real Estate"),
    (721, 760, "Business & Repair svc"), (761, 791, "Personal svc"),
    (800, 810, "Entertainment & Rec"), (812, 893, "Professional/Health/Education"),
    (900, 932, "Public Admin"),
]


def sector1990(code) -> str:
    try:
        c = int(code)
    except (TypeError, ValueError):
        return "Unknown"
    if c == 0:
        return "Unknown"
    for lo, hi, label in IND1990_RANGES:
        if lo <= c <= hi:
            return label
    return "Other/Unclassified"


def load_extract() -> pd.DataFrame:
    """Read the most recent DDI + data file pair from data/raw/."""
    ddis = sorted(RAW_DIR.glob("*.xml"), key=lambda p: p.stat().st_mtime)
    if not ddis:
        raise FileNotFoundError(f"No DDI .xml in {RAW_DIR}. Run the extract first.")
    ddi_path = ddis[-1]
    ddi = readers.read_ipums_ddi(str(ddi_path))
    df = readers.read_microdata(ddi, RAW_DIR / ddi.file_description.filename)
    df.columns = [c.upper() for c in df.columns]
    return df


def wshare(d: pd.DataFrame, mask: pd.Series, wt="WTFINL") -> float:
    w = pd.to_numeric(d[wt], errors="coerce").fillna(0)
    return float((w * mask.astype(float)).sum() / w.sum()) if w.sum() else float("nan")


def main():
    df = load_extract()
    for c in ["AGE", "YEAR", "CLASSWKR", "IND", "IND1990", "WTFINL"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["YEAR"].isin(PERIODS.keys())]
    young = df[(df["AGE"] >= 25) & (df["AGE"] <= 29)].copy()
    young["period"] = young["YEAR"].map(PERIODS)
    young["sector"] = young["IND"].map(naics_sector)
    young["sector1990"] = young["IND1990"].map(sector1990)

    rows = []
    for owner_def, codes in [("incorporated_SE", SE_INC), ("all_SE", SE_ALL)]:
        owners = young[young["CLASSWKR"].isin(codes)]
        for period in ["2015 (2014-16)", "2025 (2024-26)"]:
            d = owners[owners["period"] == period]
            d = d[d["sector"] != "Unknown"]  # drop NIU (no industry, e.g., never-worked)
            for sector in sorted(d["sector"].unique()):
                rows.append(dict(owner_def=owner_def, period=period, sector=sector,
                                 share=wshare(d, d["sector"] == sector),
                                 n_unweighted=int((d["sector"] == sector).sum())))
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "owner_25_29_industry_by_period.csv", index=False)

    # console summary: incorporated-SE, the two periods side by side, biggest sectors first
    print("=== 25-29 INCORPORATED self-employed: industry mix, 2015 vs 2025 (WTFINL-weighted) ===")
    inc = out[out["owner_def"] == "incorporated_SE"]
    piv = inc.pivot_table(index="sector", columns="period", values="share").fillna(0)
    npiv = inc.pivot_table(index="sector", columns="period", values="n_unweighted").fillna(0)
    piv = piv.reindex(piv.mean(axis=1).sort_values(ascending=False).index)
    for sec in piv.index:
        a = piv.loc[sec, "2015 (2014-16)"]; b = piv.loc[sec, "2025 (2024-26)"]
        print(f"    {sec:22} {a:5.1%} -> {b:5.1%}  ({b-a:+.1%})  "
              f"[n {int(npiv.loc[sec, '2015 (2014-16)']):>4} / {int(npiv.loc[sec, '2025 (2024-26)']):>4}]")
    tot = inc.groupby("period")["n_unweighted"].sum()
    print(f"    total unweighted owners: {int(tot.get('2015 (2014-16)',0)):,} (2015) | "
          f"{int(tot.get('2025 (2024-26)',0)):,} (2025)")
    print(f"\nWrote {OUT_DIR / 'owner_25_29_industry_by_period.csv'}")

    # ---- IND1990 robustness (time-consistent classification, coarser sectors) ----
    rob = []
    for owner_def, codes in [("incorporated_SE", SE_INC), ("all_SE", SE_ALL)]:
        owners = young[young["CLASSWKR"].isin(codes)]
        for period in ["2015 (2014-16)", "2025 (2024-26)"]:
            d = owners[(owners["period"] == period) & (owners["sector1990"] != "Unknown")]
            for sector in sorted(d["sector1990"].unique()):
                rob.append(dict(owner_def=owner_def, period=period, sector=sector,
                                share=wshare(d, d["sector1990"] == sector),
                                n_unweighted=int((d["sector1990"] == sector).sum())))
    robdf = pd.DataFrame(rob)
    robdf.to_csv(OUT_DIR / "owner_25_29_industry_by_period_IND1990.csv", index=False)
    print("\n=== ROBUSTNESS: same cut on time-consistent IND1990 (incorporated SE) ===")
    ri = robdf[robdf["owner_def"] == "incorporated_SE"]
    rpiv = ri.pivot_table(index="sector", columns="period", values="share").fillna(0)
    rpiv = rpiv.reindex(rpiv.mean(axis=1).sort_values(ascending=False).index)
    for sec in rpiv.index:
        a = rpiv.loc[sec, "2015 (2014-16)"]; b = rpiv.loc[sec, "2025 (2024-26)"]
        print(f"    {sec:32} {a:5.1%} -> {b:5.1%}  ({b-a:+.1%})")
    print(f"Wrote {OUT_DIR / 'owner_25_29_industry_by_period_IND1990.csv'}")


if __name__ == "__main__":
    main()
