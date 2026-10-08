"""Phase 4c: final small checks (MICS6 Sierra Leone 2017, ch.sav).

Read-only. Name columns dropped on load. Nothing is saved; output is
printed only (no names, no IDs).
"""
import os
from pathlib import Path

import pyreadstat

DATA_PATH = Path(os.environ.get("MICS_CH_SAV", "data/raw/ch.sav"))
if not DATA_PATH.exists():
    raise SystemExit("Set the MICS_CH_SAV environment variable to the location of ch.sav (see README).")
NAME_COLS = ["AN3N", "AN5N", "AN7N"]

df, meta = pyreadstat.read_sav(DATA_PATH)
df = df.drop(columns=[c for c in NAME_COLS if c in df.columns])
labels = meta.variable_value_labels
w0 = df["chweight"] == 0
print("Loaded:", df.shape, "| zero-weight children:", int(w0.sum()))


def counts(series, var):
    vc = series.value_counts(dropna=False).rename("count").to_frame()
    vc["label"] = [labels.get(var, {}).get(i, "") for i in vc.index]
    return vc


# ---------------------------------------------------------------
print("\n=== A. UF17 (result of interview), all children ===")
print(counts(df["UF17"], "UF17").to_string())
print("\nUF17 among the zero-weight children:")
print(counts(df.loc[w0, "UF17"], "UF17").to_string())

# ---------------------------------------------------------------
print("\n=== B. windex5 = 0 overlap ===")
z = df["windex5"] == 0
print("windex5 == 0:", int(z.sum()))
print("  of which zero-weight:", int((z & w0).sum()))

# ---------------------------------------------------------------
print("\n=== C. Exact age from CDOI - CDOB (months) vs CAGE ===")
valid = df[["CDOI", "CDOB", "CAGE"]].notna().all(axis=1)
diff = (df["CDOI"] - df["CDOB"])[valid]
print("Rows compared:", int(valid.sum()))
print("CDOB missing:", int(df["CDOB"].isna().sum()),
      "| CDOI missing:", int(df["CDOI"].isna().sum()))
print("Computed age (months): min", diff.min(), "max", diff.max())
print("Negative computed ages:", int((diff < 0).sum()))
print("Computed age != CAGE:", int((diff != df.loc[valid, "CAGE"]).sum()))
print("Differs from CAGE by more than 1 month:",
      int(((diff - df.loc[valid, "CAGE"]).abs() > 1).sum()))

# ---------------------------------------------------------------
print("\n=== D. The record with no district ===")
missing_hh7a = df["HH7A"].isna()
print(f"Rows missing HH7A: {int(missing_hh7a.sum())}")
print(f"  with chweight == 0: {int((missing_hh7a & (df['chweight'] == 0)).sum())}")

print("\nDone. Nothing was saved.")