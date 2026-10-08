"""Phase 6: report figures from the cleaned file (aggregated outputs only).

Reads data/processed/ch_clean.csv (no names, no IDs). Saves 3 PNG figures
to reports/figures/ and 3 small rate tables to reports/tables/.
Rates are weighted (chweight) and exclude children with Unknown status.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

CLEAN = Path("data/processed/ch_clean.csv")
FIG = Path("reports/figures")
TAB = Path("reports/tables")
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CLEAN)
known = df[df["reg_status"] != "Unknown"].copy()
known["is_reg"] = (known["reg_status"] == "Registered").astype(int)
overall = 100 * (known["chweight"] * known["is_reg"]).sum() / known["chweight"].sum()
print(f"Children: {len(df)} | known status: {len(known)} | overall weighted rate: {overall:.1f}%")

NOTE = "Source: MICS6 Sierra Leone 2017; author's analysis. Weighted; excludes unknown status."


def rate_table(keys, label):
    rows = []
    for g, d in known.groupby(keys):
        g = g if isinstance(g, tuple) else (g,)
        rows.append({
            "label": d[label].iloc[0],
            "n_known": len(d),
            "weighted_pct": 100 * (d["chweight"] * d["is_reg"]).sum() / d["chweight"].sum(),
            "unweighted_pct": 100 * d["is_reg"].mean(),
        })
    return pd.DataFrame(rows)


def make_bar(t, title, fname, horizontal):
    fig, ax = plt.subplots(figsize=(8, 5.8) if horizontal else (8, 4.6))
    labels = t["label"].tolist()
    vals = t["weighted_pct"].tolist()
    ns = t["n_known"].tolist()
    if horizontal:
        ax.barh(labels, vals, color="#2a6f97")
        ax.axvline(overall, ls="--", color="grey", label=f"Overall {overall:.1f}%")
        for i, (v, n) in enumerate(zip(vals, ns)):
            ax.text(v + 1, i, f"{v:.1f}% (n={n:,})", va="center", fontsize=8)
        ax.set_xlim(0, 125)
        ax.set_xticks(range(0, 101, 20))
        ax.set_xlabel("Children with birth registered (%)")
    else:
        ax.bar(labels, vals, color="#2a6f97")
        ax.axhline(overall, ls="--", color="grey", label=f"Overall {overall:.1f}%")
        for i, (v, n) in enumerate(zip(vals, ns)):
            ax.text(i, v + 1.5, f"{v:.1f}%\nn={n:,}", ha="center", fontsize=8)
        ax.set_ylim(0, 115)
        ax.set_yticks(range(0, 101, 20))
        ax.set_ylabel("Children with birth registered (%)")
    ax.set_title(title, fontsize=11)
    ax.legend(loc="lower right", fontsize=8)
    fig.text(0.01, 0.01, NOTE, fontsize=7)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(FIG / fname, dpi=200)
    plt.close(fig)
    print("Saved", FIG / fname)


# 1. District (sorted lowest to highest)
t1 = rate_table("district_code", "district").sort_values("weighted_pct")
make_bar(t1, "Birth registration among children under 5, by district", "fig1_registration_by_district.png", True)
t1.round(1).to_csv(TAB / "fig1_rates_by_district.csv", index=False)

# 2. Area
t2 = rate_table("area", "area").sort_values("label", ascending=False)
make_bar(t2, "Birth registration among children under 5, by area", "fig2_registration_by_area.png", False)
t2.round(1).to_csv(TAB / "fig2_rates_by_area.csv", index=False)

# 3. Wealth quintile (Poorest to Richest)
t3 = rate_table("wealth_code", "wealth_quintile")
make_bar(t3, "Birth registration among children under 5, by wealth quintile", "fig3_registration_by_wealth.png", False)
t3.round(1).to_csv(TAB / "fig3_rates_by_wealth.csv", index=False)

print("\nDistrict table:")
print(t1.round(1).to_string(index=False))
print("\nDone.")