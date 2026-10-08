"""Generate a data dictionary for the cleaned file (docs/data_dictionary.csv).

Reads data/processed/ch_clean.csv. The dictionary lists variable names, types,
missing counts and value summaries only (no row-level records).
"""
from pathlib import Path

import pandas as pd

CLEAN = Path("data/processed/ch_clean.csv")
OUT = Path("docs")
OUT.mkdir(parents=True, exist_ok=True)

# column: (source variable in MICS6 ch.sav, meaning)
DESC = {
    "raw_row": ("row position in raw file", "Row number in the raw file, for traceability (not a survey ID)"),
    "district_code": ("HH7A", "District code"),
    "district": ("HH7A", "District name"),
    "region": ("HH7", "Region (North, South, East, West)"),
    "area": ("HH6", "Urban or rural area"),
    "sex": ("HL4", "Sex of child"),
    "age_months": ("CAGE", "Child age in completed months (0-59)"),
    "age_group": ("derived from CAGE", "Age group in months"),
    "birth_year": ("UB1Y", "Year of birth of child"),
    "wealth_code": ("windex5", "Wealth index quintile code (1 = poorest, 5 = richest)"),
    "wealth_quintile": ("windex5", "Wealth index quintile label"),
    "mother_education_code": ("melevel", "Mother's education level code"),
    "mother_education": ("melevel", "Mother's education level label"),
    "BR1": ("BR1", "Birth certificate: 1 seen, 2 not seen, 3 none, 8 DK, 9 no response"),
    "br1_label": ("BR1", "Label for BR1"),
    "BR2": ("BR2", "Birth registered: 1 yes, 2 no, 8 DK, 9 no response; blank if not asked (skip pattern)"),
    "br2_label": ("BR2", "Label for BR2; 'Not asked (skip pattern)' when BR2 is blank by design"),
    "BR3": ("BR3", "Caretaker knows how to register: 1 yes, 2 no, 9 no response; blank if not asked"),
    "br3_label": ("BR3", "Label for BR3; 'Not asked (skip pattern)' when blank by design"),
    "reg_status": ("derived from BR1, BR2", "Registered / Not registered / Unknown (SDG 16.9.1-style definition)"),
    "reg_binary": ("derived from reg_status", "1 registered, 0 not registered, blank if Unknown"),
    "chweight": ("chweight", "Sample weight for children under 5"),
}

df = pd.read_csv(CLEAN)
rows = []
for c in df.columns:
    s = df[c]
    n_unique = int(s.nunique(dropna=True))
    if n_unique <= 15:
        summary = "; ".join(f"{k} ({v})" for k, v in s.value_counts().items())
    else:
        summary = f"{s.min()} to {s.max()}"
    src, meaning = DESC.get(c, ("(not described)", "(add description)"))
    rows.append({
        "column": c,
        "type": str(s.dtype),
        "source_variable": src,
        "description": meaning,
        "n_missing": int(s.isna().sum()),
        "n_unique": n_unique,
        "values_or_range": summary[:300],
    })

dd = pd.DataFrame(rows)
dd.to_csv(OUT / "data_dictionary.csv", index=False)

print(f"Rows: {len(df)} | Columns: {df.shape[1]}")
print(dd[["column", "type", "n_missing", "n_unique"]].to_string(index=False))
undescribed = [c for c in df.columns if c not in DESC]
print("\nColumns without a description:", undescribed if undescribed else "none")
print("\nSaved docs/data_dictionary.csv")