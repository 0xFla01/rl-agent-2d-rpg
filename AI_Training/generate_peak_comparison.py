"""Chart comparativ peak runuri — arata progresia depth-ului maxim atins.
v8e = BEST: primul run cu D01 reach natural cap-coada.

Rulare: python generate_peak_comparison.py
Output: results_v8e/peak_comparison_runs.png + table_peak_runs.csv
"""
import os
import csv
import matplotlib.pyplot as plt
import numpy as np

OUT_DIR = "results_v8e"
os.makedirs(OUT_DIR, exist_ok=True)

# Date din memorie + dataset curent
# Format: (nume run, A2/01 nat%, A2/02 nat%, SHOP%, D01 reach count, status)
RUNS = [
    ("Random",        0.00,  0.00,  0,   0, "baseline"),
    ("Claude Haiku",  0.00,  0.00,  0,   0, "baseline"),
    ("Claude Opus",   0.00,  0.00,  0,   0, "baseline"),
    ("Run 5e",        0.78,  0.00,  0,   0, "esuat"),
    ("Run 5f",        2.97,  0.00,  0,   0, "stable"),
    ("Run 5g",        0.20,  0.00,  0,   0, "esuat"),
    ("Run 5h v2",     0.00,  0.00,  0,   0, "esuat"),
    ("Run 5j",        0.50,  0.00,  1,   0, "1 ep cap-coada"),
    ("Run 5k",        5.03,  0.34,  3,   0, "Q3 RECORD A2/01"),
    ("Run 5l",        0.50,  0.00,  0,   0, "esuat lever bug"),
    ("Run 5l v2",     0.20,  0.11,  0,   0, "0 lever activari"),
    ("Run 5l v8",    28.40,  0.60,  0,   0, "breakthrough A2/02 + lever"),
    ("Run 5l v8e",   25.30,  0.90,  2,   3, "PRIMUL D01 REACH"),
]

names    = [r[0] for r in RUNS]
a201_pct = [r[1] for r in RUNS]
a202_pct = [r[2] for r in RUNS]
shop_cnt = [r[3] for r in RUNS]
d01_cnt  = [r[4] for r in RUNS]
status   = [r[5] for r in RUNS]

fig, axes = plt.subplots(2, 1, figsize=(15, 10))
fig.patch.set_facecolor("white")

# === PANEL 1: Reach percentage ===
ax = axes[0]
x = np.arange(len(names))
width = 0.35

bars1 = ax.bar(x - width/2, a201_pct, width, label="A2/01 reach NATURAL %",
               color="#3498db", edgecolor="black", linewidth=0.6)
bars2 = ax.bar(x + width/2, a202_pct, width, label="A2/02 reach NATURAL %",
               color="#e74c3c", edgecolor="black", linewidth=0.6)

# Highlight v8e — peak depth
ax.axvspan(len(names) - 1.5, len(names) - 0.5, alpha=0.18, color="gold", zorder=0)

# Annotate values
for bar, val in zip(bars1, a201_pct):
    if val > 0:
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.4,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")
for bar, val in zip(bars2, a202_pct):
    if val > 0:
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.4,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=8, color="#922")

ax.set_xticks(x)
ax.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
ax.set_ylabel("Reach rate NATURAL (%)", fontsize=11)
ax.set_title("Progresia reach rate per run — depth NATURAL cap-coada",
             fontsize=13, fontweight="bold", pad=10)
ax.legend(loc="upper left", fontsize=10, frameon=True)
ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
ax.set_ylim(0, max(max(a201_pct), max(a202_pct)) * 1.25)

# === PANEL 2: Discrete events (SHOP, D01) ===
ax = axes[1]
bars3 = ax.bar(x - width/2, shop_cnt, width, label="SHOP reach (episoade)",
               color="#9b59b6", edgecolor="black", linewidth=0.6)
bars4 = ax.bar(x + width/2, d01_cnt, width, label="Dungeon01 reach (episoade)",
               color="#27ae60", edgecolor="black", linewidth=0.6)

ax.axvspan(len(names) - 1.5, len(names) - 0.5, alpha=0.18, color="gold", zorder=0)
ax.annotate("PEAK: PRIMUL\nD01 REACH NAT",
            xy=(len(names) - 1, max(d01_cnt) + 0.2),
            xytext=(len(names) - 2.5, max(d01_cnt) + 1.5),
            fontsize=11, fontweight="bold", color="#27ae60",
            arrowprops=dict(arrowstyle="->", color="#27ae60", lw=2),
            ha="center")

for bar, val in zip(bars3, shop_cnt):
    if val > 0:
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.05,
                str(val), ha="center", va="bottom", fontsize=9, fontweight="bold")
for bar, val in zip(bars4, d01_cnt):
    if val > 0:
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.05,
                str(val), ha="center", va="bottom", fontsize=9, color="#1a5e3a", fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
ax.set_ylabel("Numar episoade", fontsize=11)
ax.set_title("Milestone events: SHOP + Dungeon01 reach (count absolut)",
             fontsize=13, fontweight="bold", pad=10)
ax.legend(loc="upper left", fontsize=10, frameon=True)
ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
ax.set_ylim(0, max(max(shop_cnt), max(d01_cnt)) + 2)

plt.suptitle("Progresie experimente Dark Wizard — comparativ runuri (Run 5l v8e = BEST depth)",
             fontsize=15, fontweight="bold", y=1.00)
plt.tight_layout()
out_png = os.path.join(OUT_DIR, "peak_comparison_runs.png")
plt.savefig(out_png, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"[saved] {out_png}")

# === CSV ===
csv_path = os.path.join(OUT_DIR, "table_peak_runs.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["run", "A2/01_nat_pct", "A2/02_nat_pct", "SHOP_count", "D01_count", "status"])
    for r in RUNS:
        w.writerow(r)
print(f"[saved] {csv_path}")

# Print tabel ASCII
print()
print("=" * 95)
print(f"{'Run':<16} | {'A2/01 nat %':>11} | {'A2/02 nat %':>11} | {'SHOP':>5} | {'D01':>4} | Status")
print("-" * 95)
for r in RUNS:
    print(f"{r[0]:<16} | {r[1]:>10.2f}% | {r[2]:>10.2f}% | {r[3]:>5} | {r[4]:>4} | {r[5]}")
print("=" * 95)
print()
print(f">>> Run 5l v8e e singurul cu D01 reach NATURAL ({d01_cnt[-1]} episoade).")
