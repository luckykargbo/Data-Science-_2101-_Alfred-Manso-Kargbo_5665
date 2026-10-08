"""RQ2 addition: birth registration by mother's education (cleaned file).

Reads data/processed/ch_clean.csv (no names, no IDs). Weighted rates use
chweight and children with a known registration status, as in figures.py.
Saves one small aggregated table to reports/tables/.
"""
from pathlib import Path

import pandas as pd

CLEAN = Path("data/processed/ch_clean.csv")
TAB = Path("reports/tables")
TAB.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CLEAN)
known = df[df["reg_status"] != "Unknown"].copy()
known["is_reg"] = (known["reg_status"] == "Registered").astype(int)

rows = []
for code, d in known.groupby("mother_education_code"):
    w = d["chweight"]
    rows.append({
        "mother_education": d["mother_education"].iloc[0],
        "n_known": len(d),
        "weighted_pct": round(100 * (w * d["is_reg"]).sum() / w.sum(), 1),
        "unweighted_pct": round(100 * d["is_reg"].mean(), 1),
    })

out = pd.DataFrame(rows)
print(f"Children with known status: {len(known)}")
print(out.to_string(index=False))
out.to_csv(TAB / "rq2_by_mother_education.csv", index=False)
print("\nSaved reports/tables/rq2_by_mother_education.csv")