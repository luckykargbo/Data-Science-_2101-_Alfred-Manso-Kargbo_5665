"""Phase 4: raw data-quality audit (MICS6 Sierra Leone 2017, ch.sav).

Read-only: the raw file is never modified. Name columns (AN3N/AN5N/AN7N)
are never selected, printed or saved. Only aggregated tables are written.
"""
import os
from pathlib import Path

import pandas as pd
import pyreadstat

DATA_PATH = Path(os.environ.get("MICS_CH_SAV", "data/raw/ch.sav"))
if not DATA_PATH.exists():
    raise SystemExit("Set the MICS_CH_SAV environment variable to the location of ch.sav (see README).")
OUT = Path("reports/tables")
OUT.mkdir(parents=True, exist_ok=True)

df, meta = pyreadstat.read_sav(DATA_PATH)
df = df.drop(columns=[c for c in ["AN3N","AN5N","AN7N"] if c in df.columns])
labels = meta.variable_value_labels
print("Loaded:", df.shape)

# ---------------------------------------------------------------
# STEP 1: records with missing key fields (no names, no IDs shown)
# ---------------------------------------------------------------
print("\n=== STEP 1a: children with missing BR1 ===")
missing_br1 = df["BR1"].isna()
print(f"Rows missing BR1: {int(missing_br1.sum())}")
print(f"  also lacking UB1Y and CAGE: {int((missing_br1 & df['UB1Y'].isna() & df['CAGE'].isna()).sum())}")
print(f"  with chweight == 0: {int((missing_br1 & (df['chweight'] == 0)).sum())}")
same = (df["BR1"].isna() == df["UB1Y"].isna()) & (df["BR1"].isna() == df["CAGE"].isna())
print("BR1, UB1Y and CAGE missing on exactly the same rows:", bool(same.all()))

print("\n=== STEP 1b: record(s) with missing district ===")
missing_hh7a = df["HH7A"].isna()
print(f"Rows missing HH7A: {int(missing_hh7a.sum())}")
print(f"  with chweight == 0: {int((missing_hh7a & (df['chweight'] == 0)).sum())}")

# ---------------------------------------------------------------
# STEP 2: draft "ever registered" variable from BR1 + BR2
# Registered     = certificate seen/not seen (BR1 = 1 or 2) OR BR2 = 1
# Not registered = BR2 = 2 and no certificate
# Unknown        = everything else (DK, no response, missing)
# ---------------------------------------------------------------
has_cert = df["BR1"].isin([1, 2])
reg = has_cert | (df["BR2"] == 1)
not_reg = (~has_cert) & (df["BR2"] == 2)

df["reg_status"] = "Unknown"
df.loc[reg, "reg_status"] = "Registered"
df.loc[not_reg, "reg_status"] = "Not registered"

counts = df["reg_status"].value_counts().rename("count").to_frame()
counts["pct"] = (100 * counts["count"] / len(df)).round(2)
print("\n=== STEP 2: draft registration status ===")
print(counts)
counts.to_csv(OUT / "audit_reg_status_counts.csv")

# ---------------------------------------------------------------
# STEP 3: registration rate by group, unweighted and weighted
# Denominator = children with a known status (Unknown excluded).
# ---------------------------------------------------------------
known = df[df["reg_status"] != "Unknown"].copy()
known["is_reg"] = (known["reg_status"] == "Registered").astype(int)

overall_u = 100 * known["is_reg"].mean()
overall_w = 100 * (known["chweight"] * known["is_reg"]).sum() / known["chweight"].sum()
print(f"\nOverall (known status only, n={len(known)}): "
      f"unweighted {overall_u:.1f}%, weighted {overall_w:.1f}%")


def rate_table(by, name):
    rows = []
    for code, g in known.groupby(by):
        w = g["chweight"]
        rows.append({
            by: code,
            "label": labels.get(by, {}).get(code, ""),
            "n_known": len(g),
            "unweighted_pct": round(100 * g["is_reg"].mean(), 1),
            "weighted_pct": round(100 * (w * g["is_reg"]).sum() / w.sum(), 1),
        })
    out = pd.DataFrame(rows).sort_values("weighted_pct")
    print(f"\n=== STEP 3: by {name} ===")
    print(out.to_string(index=False))
    out.to_csv(OUT / f"audit_reg_rate_by_{name}.csv", index=False)


rate_table("HH7A", "district")
rate_table("HH6", "area")
rate_table("windex5", "wealth_quintile")

print("\nDone. Only aggregated tables were saved to reports/tables/.")