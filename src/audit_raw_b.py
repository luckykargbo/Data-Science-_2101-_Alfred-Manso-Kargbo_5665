"""Phase 4b: extended raw data-quality audit (MICS6 Sierra Leone 2017, ch.sav).

Read-only. Name columns are dropped on load. Only aggregated tables are
saved (column-level summaries, never row-level data).
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
NAME_COLS = ["AN3N", "AN5N", "AN7N"]

df, meta = pyreadstat.read_sav(DATA_PATH)
df = df.drop(columns=[c for c in NAME_COLS if c in df.columns])
labels = meta.variable_value_labels
col_labels = meta.column_names_to_labels
print("Loaded:", df.shape)

# ---------------------------------------------------------------
print("\n=== A. ZERO-WEIGHT AND MISSING-WEIGHT RECORDS ===")
w0 = df["chweight"] == 0
print("chweight missing:", int(df["chweight"].isna().sum()))
print("chweight == 0:", int(w0.sum()))
print("  of which BR1 missing:", int((w0 & df["BR1"].isna()).sum()))
print("  of which BR1 present:", int((w0 & df["BR1"].notna()).sum()))

# ---------------------------------------------------------------
print("\n=== B. AGE AND BIRTH-YEAR CHECKS ===")
print(df[["CAGE", "UB1Y"]].describe().round(1))
print("CAGE outside 0-59 months:", int(((df["CAGE"] < 0) | (df["CAGE"] > 59)).sum()))
print("\nBirth years:")
print(df["UB1Y"].value_counts().sort_index().to_string())
# ROUGH check only: assumes the interview year is 2017 (confirm later).
approx_age = 2017 - df["UB1Y"]
rough_flag = (approx_age - df["CAGE"] / 12).abs() > 1.5
print("\nRough birth-year vs age mismatch (>1.5 yrs, assumes 2017):", int(rough_flag.sum()))

print("\nCandidate variables found by label search:")
for kw in ["date of interview", "result", "date of birth"]:
    hits = [(c, l) for c, l in col_labels.items()
            if l and kw in l.lower() and c not in NAME_COLS][:8]
    print(f"  '{kw}':", hits)

# ---------------------------------------------------------------
print("\n=== C. KEY VARIABLE DISTRIBUTIONS ===")
for v in ["HL4", "windex5", "melevel", "ethnicity"]:
    if v in df.columns:
        vc = df[v].value_counts(dropna=False).head(15).rename("count").to_frame()
        vc["label"] = [labels.get(v, {}).get(i, "") for i in vc.index]
        print(f"\n{v} - {col_labels.get(v, '')}")
        print(vc.to_string())
    else:
        print(f"\n{v}: not in file")

# ---------------------------------------------------------------
print("\n=== D. SKIP-PATTERN CONSISTENCY (BR1 / BR2 / BR3) ===")
print("BR1 = 1 or 2 but BR2 answered:", int((df["BR1"].isin([1, 2]) & df["BR2"].notna()).sum()))
print("BR1 = 3 but BR2 blank:", int(((df["BR1"] == 3) & df["BR2"].isna()).sum()))
print("BR3 answered but BR2 not in (2, 8, 9):",
      int((df["BR3"].notna() & ~df["BR2"].isin([2, 8, 9])).sum()))
print("BR2 in (2, 8, 9) but BR3 blank:",
      int((df["BR2"].isin([2, 8, 9]) & df["BR3"].isna()).sum()))

# ---------------------------------------------------------------
print("\n=== E. TEXT (STRING) COLUMNS ===")
str_cols = [c for c in df.columns
            if pd.api.types.is_string_dtype(df[c]) or df[c].dtype == object]
rows = []
for c in str_cols:
    s = df[c].dropna().astype(str)
    nonblank = s[s.str.strip() != ""]
    rows.append({
        "column": c,
        "label": col_labels.get(c, ""),
        "n_null": int(df[c].isna().sum()),
        "n_blank_text": int((s.str.strip() == "").sum()),
        "n_extra_spaces": int((s != s.str.strip()).sum()),
        "n_unique_nonblank": int(nonblank.nunique()),
        "looks_numeric": bool(len(nonblank) > 0
                              and pd.to_numeric(nonblank, errors="coerce").notna().all()),
    })
sdf = pd.DataFrame(rows)
sdf.to_csv(OUT / "audit_string_columns.csv", index=False)
print("Text columns:", len(sdf))
print("All blank or null:", int(((sdf["n_unique_nonblank"]) == 0).sum()))
print("With extra leading/trailing spaces:", int((sdf["n_extra_spaces"] > 0).sum()))
print("Numeric-looking text (type conversion candidates):", int(sdf["looks_numeric"].sum()))
print(sdf[sdf["looks_numeric"]][["column", "label", "n_unique_nonblank"]].head(15).to_string(index=False))

# ---------------------------------------------------------------
print("\n=== F. MISSINGNESS ACROSS ALL COLUMNS ===")
eff = []
for c in df.columns:
    s = df[c]
    m = s.isna() | (s.astype(str).str.strip() == "") if c in str_cols else s.isna()
    eff.append({"column": c, "label": col_labels.get(c, ""),
                "dtype": "text" if c in str_cols else "numeric",
                "pct_missing": round(100 * m.mean(), 1)})
edf = pd.DataFrame(eff)
edf.to_csv(OUT / "audit_missing_by_column.csv", index=False)
print("0% missing:", int((edf["pct_missing"] == 0).sum()))
print("> 50% missing:", int((edf["pct_missing"] > 50).sum()))
print("> 90% missing:", int((edf["pct_missing"] > 90).sum()))
print("100% missing:", int((edf["pct_missing"] == 100).sum()))

print("\nDone. Only column-level summaries were saved to reports/tables/.")