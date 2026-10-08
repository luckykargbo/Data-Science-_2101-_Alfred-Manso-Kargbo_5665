"""Phase 5: cleaning and preparation (MICS6 Sierra Leone 2017, ch.sav).

- The raw file is only READ, never modified (SHA-256 checked before/after).
- Name columns are dropped on load and never saved.
- Cleaned data goes to data/processed/ (git-ignored). Only aggregated
  logs and validation tables go to reports/tables/.
"""
import hashlib
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

DATA_PATH = Path(os.environ.get("MICS_CH_SAV", "data/raw/ch.sav"))
if not DATA_PATH.exists():
    raise SystemExit("Set the MICS_CH_SAV environment variable to the location of ch.sav (see README).")
OUT_T = Path("reports/tables")
OUT_D = Path("data/processed")
OUT_T.mkdir(parents=True, exist_ok=True)
OUT_D.mkdir(parents=True, exist_ok=True)
NAME_COLS = ["AN3N", "AN5N", "AN7N"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def derive_status(d):
    """Registered = certificate seen/not seen (BR1 1 or 2) OR BR2 = 1.
    Not registered = no certificate and BR2 = 2. Everything else = Unknown."""
    has_cert = d["BR1"].isin([1, 2])
    status = pd.Series("Unknown", index=d.index)
    status[has_cert | (d["BR2"] == 1)] = "Registered"
    status[(~has_cert) & (d["BR2"] == 2)] = "Not registered"
    return status


def rates(d):
    k = d[d["reg_status"] != "Unknown"]
    r = (k["reg_status"] == "Registered")
    return (round(100 * r.mean(), 1),
            round(100 * (k["chweight"] * r).sum() / k["chweight"].sum(), 1))


hash_before = sha256(DATA_PATH)

# ---------------------------------------------------------------
# LOAD (raw stays untouched)
# ---------------------------------------------------------------
raw, meta = pyreadstat.read_sav(DATA_PATH)
raw = raw.drop(columns=[c for c in NAME_COLS if c in raw.columns])
labels = meta.variable_value_labels
raw["raw_row"] = raw.index
raw["reg_status"] = derive_status(raw)
n_raw = len(raw)
print("Loaded raw:", raw.shape)

log = []


def log_step(step, before, after, reason):
    log.append({"step": step, "rows_before": before, "rows_after": after,
                "rows_removed": before - after, "reason": reason})
    print(f"{step}: {before} -> {after} (removed {before - after})")


# ---------------------------------------------------------------
# STEP 1: keep completed interviews only
# ---------------------------------------------------------------
df = raw[raw["UF17"] == 1].copy()
log_step("1. Keep completed interviews (UF17 = 1)", n_raw, len(df),
         "Not at home / refused / no consent / other: no usable answers, weight 0")

# STEP 2: keep positive sample weights
n = len(df)
df = df[df["chweight"] > 0].copy()
log_step("2. Keep chweight > 0", n, len(df), "Zero weight = excluded from survey estimates")

# ---------------------------------------------------------------
# STEP 3: recode placeholders
# ---------------------------------------------------------------
df["windex5"] = df["windex5"].replace(0, np.nan)   # 0 was a placeholder, not a group

# ---------------------------------------------------------------
# STEP 4: readable labels and derived variables
# ---------------------------------------------------------------
def lab(col):
    return df[col].map(labels[col]).str.title()


out = pd.DataFrame(index=df.index)
out["raw_row"] = df["raw_row"]
out["district_code"] = df["HH7A"].astype("Int64")
out["district"] = lab("HH7A")
out["region"] = lab("HH7")
out["area"] = lab("HH6")
out["sex"] = lab("HL4")
out["age_months"] = df["CAGE"].astype("Int64")
out["age_group"] = pd.cut(df["CAGE"], bins=[-1, 11, 23, 35, 47, 59],
                          labels=["0-11 m", "12-23 m", "24-35 m", "36-47 m", "48-59 m"])
out["birth_year"] = df["UB1Y"].astype("Int64")
out["wealth_code"] = df["windex5"].astype("Int64")
out["wealth_quintile"] = lab("windex5")
out["mother_education_code"] = df["melevel"].astype("Int64")
out["mother_education"] = lab("melevel")

out["BR1"] = df["BR1"].astype("Int64")
out["br1_label"] = lab("BR1")
out["BR2"] = df["BR2"].astype("Int64")
out["br2_label"] = lab("BR2").fillna("Not asked (skip pattern)")
out["BR3"] = df["BR3"].astype("Int64")
out["br3_label"] = lab("BR3").fillna("Not asked (skip pattern)")

out["reg_status"] = df["reg_status"]
out["reg_binary"] = out["reg_status"].map({"Registered": 1, "Not registered": 0}).astype("Int64")
out["chweight"] = df["chweight"]
for opt in ["psu", "stratum"]:          # kept for later survey-based estimates
    if opt in df.columns:
        out[opt] = df[opt]

clean = out.reset_index(drop=True)
print("\nClean shape:", clean.shape)

# ---------------------------------------------------------------
# STEP 5: save cleaned data (git-ignored folder) and exclusion log
# ---------------------------------------------------------------
clean.to_csv(OUT_D / "ch_clean.csv", index=False)
log.append({"step": "3-4. Recode windex5 = 0; add labels, age group, reg_status",
            "rows_before": len(clean), "rows_after": len(clean), "rows_removed": 0,
            "reason": f"Columns reduced from {raw.shape[1] - 2} to {clean.shape[1]}"})
pd.DataFrame(log).to_csv(OUT_T / "clean_exclusion_log.csv", index=False)

# ---------------------------------------------------------------
# VALIDATION: before vs after
# ---------------------------------------------------------------
rb, ra = rates(raw), rates(clean)
val = pd.DataFrame([
    ["Rows", n_raw, len(clean)],
    ["Columns", raw.shape[1] - 2, clean.shape[1]],
    ["Zero-weight records", int((raw["chweight"] == 0).sum()), int((clean["chweight"] == 0).sum())],
    ["Missing BR1", int(raw["BR1"].isna().sum()), int(clean["BR1"].isna().sum())],
    ["Missing district", int(raw["HH7A"].isna().sum()), int(clean["district_code"].isna().sum())],
    ["windex5 = 0 placeholder", int((raw["windex5"] == 0).sum()), 0],
    ["Registration status Unknown", int((raw["reg_status"] == "Unknown").sum()),
     int((clean["reg_status"] == "Unknown").sum())],
    ["Registration rate, known status, unweighted %", rb[0], ra[0]],
    ["Registration rate, known status, weighted %", rb[1], ra[1]],
    ["Districts present", int(raw["HH7A"].nunique()), int(clean["district_code"].nunique())],
], columns=["metric", "raw_before", "cleaned_after"])
val.to_csv(OUT_T / "clean_validation_before_after.csv", index=False)
print("\n=== BEFORE vs AFTER ===")
print(val.to_string(index=False))

print("\n=== CHECKS ===")
hash_after = sha256(DATA_PATH)
checks = [
    ("Raw file unchanged (SHA-256 identical)", hash_before == hash_after),
    ("No duplicate rows", int(clean["raw_row"].duplicated().sum()) == 0),
    ("All weights > 0", bool((clean["chweight"] > 0).all())),
    ("No missing district; 14 districts", clean["district_code"].notna().all() and clean["district_code"].nunique() == 14),
    ("Age within 0-59 months", bool(clean["age_months"].between(0, 59).all())),
    ("Wealth quintile 1-5, none missing", bool(clean["wealth_code"].between(1, 5).all())),
    ("reg_status has 3 valid values, none missing",
     set(clean["reg_status"].unique()) <= {"Registered", "Not registered", "Unknown"}),
    ("BR2 blank only where certificate present", bool(clean.loc[clean["BR2"].isna(), "BR1"].isin([1, 2]).all())),
    ("No name columns in output", not any(c in clean.columns for c in NAME_COLS)),
]
for name, ok in checks:
    print(("PASS  " if ok else "FAIL  ") + name)

print("\nregistration status counts:")
print(clean["reg_status"].value_counts().to_string())
print("\nDone. Cleaned data in data/processed/ (git-ignored). Logs in reports/tables/.")