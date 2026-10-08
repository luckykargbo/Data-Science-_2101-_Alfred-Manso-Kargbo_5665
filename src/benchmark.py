"""Benchmark check plus first answers for RQ1 and RQ3 (cleaned MICS6 file).

Reads data/processed/ch_clean.csv (no names, no IDs). Prints results and
saves small aggregated tables to reports/tables/. All rates weighted.
"""
from pathlib import Path

import pandas as pd

CLEAN = Path("data/processed/ch_clean.csv")
TAB = Path("reports/tables")
TAB.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CLEAN)
N = len(df)


def wpct(mask, d=None):
    if d is None:
        d = df
    return 100 * d.loc[mask, "chweight"].sum() / d["chweight"].sum()


registered = df["reg_status"] == "Registered"
unknown = df["reg_status"] == "Unknown"
cert = df["BR1"].isin([1, 2])
reg_no_cert = (df["BR1"] == 3) & (df["BR2"] == 1)

# ---------------------------------------------------------------
print("=== 1. BENCHMARK: registered share over ALL children (unknown in denominator) ===")
print(f"Children: {N}")
print(f"Unweighted: {100 * registered.mean():.1f}%   Weighted: {wpct(registered):.1f}%")
known = df[~unknown]
print(f"Known-status only (earlier figure): weighted {wpct(known['reg_status'] == 'Registered', known):.1f}%")
print("Published 2017 national figure (to compare, from UNICEF-based sources): about 81%")

rows = []
for col in ["sex", "area"]:
    for g, d in df.groupby(col):
        rows.append({"group": f"{col}: {g}", "n_all": len(d),
                     "weighted_pct_registered": round(wpct(d["reg_status"] == "Registered", d), 1)})
bench = pd.DataFrame(rows)
print("\nBy sex and area (all children, weighted):")
print(bench.to_string(index=False))
bench.to_csv(TAB / "benchmark_sex_area.csv", index=False)

# ---------------------------------------------------------------
print("\n=== 2. RQ1: certificate vs registration ===")
print(f"Certificate (seen or not seen): {int(cert.sum())} children, weighted {wpct(cert):.1f}%")
print(f"  of which certificate SEEN: weighted {wpct(df['BR1'] == 1):.1f}%")
print(f"Registered, no certificate: {int(reg_no_cert.sum())} children, weighted {wpct(reg_no_cert):.1f}%")
print(f"Not registered: {int((df['reg_status'] == 'Not registered').sum())}, "
      f"weighted {wpct(df['reg_status'] == 'Not registered'):.1f}%")
print(f"Unknown: {int(unknown.sum())}, weighted {wpct(unknown):.1f}%")

# ---------------------------------------------------------------
print("\n=== 3. RQ3: among NOT registered, do caretakers know how to register (BR3)? ===")
nr = df[df["reg_status"] == "Not registered"]
print("Not-registered children:", len(nr))
t = nr.groupby("br3_label").agg(n=("chweight", "size"), w=("chweight", "sum"))
t["weighted_pct"] = (100 * t["w"] / t["w"].sum()).round(1)
print(t[["n", "weighted_pct"]].to_string())
t[["n", "weighted_pct"]].to_csv(TAB / "rq3_br3_overall.csv")

nr_known = nr[nr["br3_label"].isin(["Yes", "No"])]
rows = []
for col in ["area", "district"]:
    for g, d in nr_known.groupby(col):
        rows.append({"group": f"{col}: {g}", "n": len(d),
                     "pct_know_how": round(wpct(d["br3_label"] == "Yes", d), 1)})
rq3 = pd.DataFrame(rows)
print("\nShare who know how to register (Yes/No answers only, weighted):")
print(rq3.to_string(index=False))
rq3.to_csv(TAB / "rq3_by_area_district.csv", index=False)

print("\nDone. Only aggregated tables were saved.")