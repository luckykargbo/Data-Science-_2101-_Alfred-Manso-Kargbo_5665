import hashlib
import os
from pathlib import Path
import pandas as pd
import pyreadstat

DATA_PATH = Path(os.environ.get("MICS_CH_SAV", "data/raw/ch.sav"))
if not DATA_PATH.exists():
    raise SystemExit("Set the MICS_CH_SAV environment variable to the location of ch.sav (see README).")
OUT = Path(__file__).resolve().parents[1] / "reports" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

print("File:", DATA_PATH.name)
print("SHA-256:", hashlib.sha256(DATA_PATH.read_bytes()).hexdigest())

df, meta = pyreadstat.read_sav(DATA_PATH)      # numeric codes kept
df = df.drop(columns=[c for c in ["AN3N","AN5N","AN7N"] if c in df.columns])
labels = meta.variable_value_labels
print("Shape:", df.shape)

NAMES = {"AN3N", "AN5N", "AN7N"}               # never display these
print("Name columns present:", sorted(NAMES & set(df.columns)))
safe = [c for c in df.columns if c not in NAMES]
print(df[safe].dtypes.value_counts())

key = ["BR1", "BR2", "BR3", "HH6", "HH7", "HH7A",
       "UB1Y", "CAGE", "HL4", "chweight", "windex5"]
present = [k for k in key if k in df.columns]
print("Not in file:", [k for k in key if k not in df.columns])

miss = pd.DataFrame({"missing": df[present].isna().sum(),
                     "pct": (df[present].isna().mean() * 100).round(2)})
print(miss)
miss.to_csv(OUT / "raw_missing_key_vars.csv")

for k in ["BR1", "BR2", "BR3", "HH6", "HH7", "HH7A"]:
    if k in df.columns:
        vc = df[k].value_counts(dropna=False).rename("count").to_frame()
        vc["label"] = [labels.get(k, {}).get(i, "") for i in vc.index]
        print("\n", k, "-", meta.column_names_to_labels[k])
        print(vc)
        vc.to_csv(OUT / f"raw_counts_{k}.csv")

if {"BR1", "BR2"} <= set(df.columns):
    print(pd.crosstab(df["BR1"], df["BR2"], dropna=False))

print("Duplicate rows:", df[safe].duplicated().sum())
ids = [c for c in ["HH1", "HH2", "UF3"] if c in df.columns]
if len(ids) == 3:
    print("Duplicate child IDs:", df.duplicated(subset=ids).sum())