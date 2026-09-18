"""Genereaza 2 chart-uri suplimentare pentru PPT v8e:
- cross_run_progress_v8e.png   = timeline progres iterativ peste runuri (cine a deblocat ce)
- quality_5f_vs_v8e.png        = comparatie calitate joc (buffs, level, depth, kills) 5f vs v8e

Rulare: python generate_v8e_extras.py
Iese in: results_v8e/
"""
import os
import csv
import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "results_v8e")

plt.rcParams.update({
    "figure.facecolor": "#2d3b47",
    "axes.facecolor":   "#3a4a5a",
    "axes.edgecolor":   "#cccccc",
    "axes.labelcolor":  "#ffffff",
    "axes.titlecolor":  "#ffffff",
    "xtick.color":      "#ffffff",
    "ytick.color":      "#ffffff",
    "text.color":       "#ffffff",
    "font.size":        12,
})


def chart_cross_run_progress():
    """Stacked view: pentru fiecare run, cat % din ep ajung A2/01, A2/02, SHOP, D01."""
    table_path = os.path.join(OUT_DIR, "table_peak_runs.csv")
    rows = []
    with open(table_path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)

    # Filtrez doar runurile PPO (fara baseline-uri random/claude)
    ppo_rows = [r for r in rows if r["status"] != "baseline"]

    runs = [r["run"] for r in ppo_rows]
    a2_01 = [float(r["A2/01_nat_pct"]) for r in ppo_rows]
    a2_02 = [float(r["A2/02_nat_pct"]) for r in ppo_rows]
    shop  = [int(r["SHOP_count"]) for r in ppo_rows]
    d01   = [int(r["D01_count"]) for r in ppo_rows]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), dpi=120,
                                    gridspec_kw={"height_ratios": [1.4, 1]})
    fig.suptitle("Progresia iterativa a runurilor PPO+BC — cine a deblocat ce camera",
                 fontsize=16, color="#ffffff", y=0.995)

    # Panel 1: A2/01 + A2/02 procentual (line chart cu markers)
    x = np.arange(len(runs))
    ax1.plot(x, a2_01, color="#3fd0d4", marker='o', linewidth=2.5, markersize=10,
             label="A2/01 reach (cam. 4) natural %", markeredgecolor="#fff", markeredgewidth=1.2)
    ax1.plot(x, a2_02, color="#e88a4a", marker='s', linewidth=2.5, markersize=10,
             label="A2/02 reach (cam. 6) natural %", markeredgecolor="#fff", markeredgewidth=1.2)

    # Annotate peak v8e + record v8 + record 5k
    for i, (a, b) in enumerate(zip(a2_01, a2_02)):
        if a > 0:
            ax1.text(i, a + 1.5, f"{a:.1f}%", ha='center', fontsize=8.5,
                     color="#3fd0d4", weight='bold')
        if b > 0:
            ax1.text(i, b - 1.5, f"{b:.2f}%", ha='center', fontsize=8.5,
                     color="#e88a4a", weight='bold', va='top')

    ax1.set_xticks(x)
    ax1.set_xticklabels(runs, rotation=20, ha='right', fontsize=10)
    ax1.set_ylabel("% episoade naturale", fontsize=11)
    ax1.set_title("Reach rate per cameră (cap-coadă, fara curriculum)", fontsize=13, pad=10)
    ax1.legend(loc="upper left", fontsize=11, facecolor="#3a4a5a", edgecolor="#888")
    ax1.grid(True, alpha=0.25)
    ax1.set_axisbelow(True)
    for spine in ax1.spines.values():
        spine.set_color("#666666")

    # Panel 2: SHOP + D01 count absolut (stacked bars)
    width = 0.38
    bars_s = ax2.bar(x - width/2, shop, width, color="#9b59b6", edgecolor="#cccccc",
                     label="SHOP reach (count ep)")
    bars_d = ax2.bar(x + width/2, d01, width, color="#27ae60", edgecolor="#ffd700",
                     linewidth=1.5, label="D01 reach (count ep) — PRIMUL la v8e")

    for bar, v in zip(bars_s, shop):
        if v > 0:
            ax2.text(bar.get_x() + bar.get_width()/2, v + 0.05,
                     str(v), ha='center', fontsize=9, color="#fff", weight='bold')
    for bar, v in zip(bars_d, d01):
        if v > 0:
            ax2.text(bar.get_x() + bar.get_width()/2, v + 0.05,
                     str(v), ha='center', fontsize=9, color="#ffd700", weight='bold')

    ax2.set_xticks(x)
    ax2.set_xticklabels(runs, rotation=20, ha='right', fontsize=10)
    ax2.set_ylabel("Numar episoade", fontsize=11)
    ax2.set_title("Milestone-uri rare (SHOP / D01 reach)", fontsize=13, pad=10)
    ax2.legend(loc="upper left", fontsize=11, facecolor="#3a4a5a", edgecolor="#888")
    ax2.grid(True, axis='y', alpha=0.25)
    ax2.set_axisbelow(True)
    for spine in ax2.spines.values():
        spine.set_color("#666666")

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    out = os.path.join(OUT_DIR, "cross_run_progress_v8e.png")
    plt.savefig(out, facecolor="#2d3b47", bbox_inches='tight')
    plt.close()
    print(f"[saved] {out}")


def chart_quality_5f_vs_v8e():
    """Comparatie calitate joc: nu doar 'ajunge mai departe' ci 'joaca mai bine'."""
    csv_path = os.path.join(OUT_DIR, "compare_runs_v8e.csv")
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.reader(f))

    headers = rows[0]
    data = {h: [] for h in headers}
    for row in rows[1:]:
        for h, v in zip(headers, row):
            data[h].append(v)

    metric_col = data["Metrica"]

    def get(metric, run):
        i = metric_col.index(metric)
        return float(data[run][i])

    # Folosim doar metrici robuste (nu % reach care include curriculum override).
    # Pentru A2/01 / A2/02 / D01 NATURAL, citim din table_peak_runs.csv (cap-coada).
    peak_path = os.path.join(OUT_DIR, "table_peak_runs.csv")
    nat = {}
    with open(peak_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            nat[row["run"]] = row

    metrics_for_chart = [
        ("Avg kills/ep",  "Kills medii / episod"),
        ("Avg depth",     "Depth mediu (1-11)"),
        ("Max depth",     "Depth maxim atins"),
        ("Avg level final", "Nivel mediu final"),
        ("Buffs total",   "Buff-uri culese (total)"),
    ]

    labels = [m[1] for m in metrics_for_chart]
    vals_5f  = [get(m[0], "run5f") for m in metrics_for_chart]
    vals_v8e = [get(m[0], "run5l_v8e") for m in metrics_for_chart]

    # Adaug A2/01_nat si A2/02_nat din table_peak_runs (natural cap-coada)
    labels.append("A2/01 reach NATURAL (%)")
    vals_5f.append(float(nat["Run 5f"]["A2/01_nat_pct"]))
    vals_v8e.append(float(nat["Run 5l v8e"]["A2/01_nat_pct"]))

    labels.append("A2/02 reach NATURAL (%)")
    vals_5f.append(float(nat["Run 5f"]["A2/02_nat_pct"]))
    vals_v8e.append(float(nat["Run 5l v8e"]["A2/02_nat_pct"]))

    # Calcul ratio pentru annotation
    ratios = []
    for a, b in zip(vals_5f, vals_v8e):
        if a > 0:
            ratios.append(b / a)
        else:
            ratios.append(float('inf'))

    fig, ax = plt.subplots(figsize=(14, 7), dpi=120)
    fig.suptitle("Calitatea jocului — Run 5f vs Run 5l v8e (BEST)",
                 fontsize=16, color="#ffffff", y=0.99)

    x = np.arange(len(labels))
    width = 0.36

    # Normalize: pentru fiecare metric, scalez la max(5f, v8e) ca sa fie comparabile pe acelasi grafic
    vals_5f_norm  = []
    vals_v8e_norm = []
    raw_5f = []
    raw_v8e = []
    for a, b in zip(vals_5f, vals_v8e):
        m = max(a, b)
        if m == 0: m = 1
        vals_5f_norm.append(100 * a / m)
        vals_v8e_norm.append(100 * b / m)
        raw_5f.append(a)
        raw_v8e.append(b)

    bars_5f  = ax.bar(x - width/2, vals_5f_norm, width,
                      color="#4cb84c", edgecolor="#cccccc", label="Run 5f (805 ep)")
    bars_v8e = ax.bar(x + width/2, vals_v8e_norm, width,
                      color="#7ad77a", edgecolor="#ffd700", linewidth=1.8,
                      label="Run 5l v8e (3959 ep) — BEST")

    for bar, v in zip(bars_5f, raw_5f):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                f"{v:.2f}" if v < 100 else f"{v:.0f}",
                ha='center', fontsize=9, color="#4cb84c", weight='bold')
    for bar, v, ratio in zip(bars_v8e, raw_v8e, ratios):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                f"{v:.2f}" if v < 100 else f"{v:.0f}",
                ha='center', fontsize=9, color="#ffd700", weight='bold')
        # Multiplier annotation deasupra
        if ratio != float('inf') and ratio >= 1.2:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 7,
                    f"{ratio:.1f}×", ha='center', fontsize=11, color="#ffd700",
                    weight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10, rotation=15, ha='right')
    ax.set_ylabel("% din max (5f vs v8e, normalizat)", fontsize=11)
    ax.set_title("Cifrele exacte sunt deasupra fiecarei coloane. Multiplicatorul × arata cresterea v8e vs 5f.",
                 fontsize=11, pad=10, color="#cccccc")
    ax.legend(loc="upper left", fontsize=12, facecolor="#3a4a5a", edgecolor="#888")
    ax.grid(True, axis='y', alpha=0.25)
    ax.set_axisbelow(True)
    ax.set_ylim(0, 130)
    for spine in ax.spines.values():
        spine.set_color("#666666")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(OUT_DIR, "quality_5f_vs_v8e.png")
    plt.savefig(out, facecolor="#2d3b47", bbox_inches='tight')
    plt.close()
    print(f"[saved] {out}")


if __name__ == "__main__":
    chart_cross_run_progress()
    chart_quality_5f_vs_v8e()
    print("Done.")
