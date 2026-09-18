"""Genereaza chart-uri vizuale din compare_runs data pentru slide-uri PPT."""
import csv
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "results_v4", "compare_runs.csv")
OUT_DIR = os.path.join(HERE, "results_v4")
os.makedirs(OUT_DIR, exist_ok=True)

# Dark theme matching PPT
plt.rcParams.update({
    "figure.facecolor": "#2d3b47",
    "axes.facecolor":   "#3a4a5a",
    "axes.edgecolor":   "#cccccc",
    "axes.labelcolor":  "#ffffff",
    "axes.titlecolor":  "#ffffff",
    "xtick.color":      "#ffffff",
    "ytick.color":      "#ffffff",
    "text.color":       "#ffffff",
    "font.size":        13,
    "font.family":      "sans-serif",
})

# Read CSV
data = {}
with open(CSV_PATH, encoding="utf-8") as f:
    reader = csv.reader(f)
    headers = next(reader)  # ["Metrica", "uniform", "realistic", ...]
    runs = headers[1:]
    for row in reader:
        metric = row[0]
        values = []
        for v in row[1:]:
            try:
                values.append(float(v))
            except Exception:
                values.append(0.0)
        data[metric] = dict(zip(runs, values))

# Label-uri prietenoase
LABEL_MAP = {
    "uniform":      "Random\nuniform",
    "realistic":    "Random\nrealistic",
    "claude_haiku": "Claude\nHaiku 4.5",
    "claude_opus":  "Claude\nOpus 4.7",
    "run5c":        "PPO+BC\nRun 5c",
    "run5e":        "PPO+BC\nRun 5e",
    "run5f":        "PPO+BC\nRun 5f",
}

# Colors: random gri, claude orange, PPO verde+galben (5f e cel mai stralucitor)
COLORS = {
    "uniform":      "#888888",
    "realistic":    "#aaaaaa",
    "claude_haiku": "#e88a4a",
    "claude_opus":  "#d46e2a",
    "run5c":        "#2e8b3e",
    "run5e":        "#4cb84c",
    "run5f":        "#7ad77a",  # cel mai luminos verde — best run
}

labels = [LABEL_MAP.get(r, r) for r in runs]
colors = [COLORS.get(r, "#888888") for r in runs]


def plot_metric(metric_key, ylabel, fname, log=False, title=None):
    fig, ax = plt.subplots(figsize=(12, 5.5), dpi=120)
    values = [data[metric_key][r] for r in runs]
    bars = ax.bar(labels, values, color=colors, edgecolor="#cccccc", linewidth=1.2)

    # Highlight best value (last bar = Run 5e)
    bars[-1].set_edgecolor("#ffd700")
    bars[-1].set_linewidth(3)

    # Value labels deasupra barelor
    for bar, v in zip(bars, values):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, h + max(values)*0.015,
                f"{v:.2f}" if isinstance(v, float) and v != int(v) else f"{v:.0f}",
                ha='center', va='bottom', fontsize=11, color="#ffffff", weight='bold')

    ax.set_ylabel(ylabel, fontsize=13)
    if title:
        ax.set_title(title, fontsize=15, pad=15)
    if log:
        ax.set_yscale("log")
    ax.grid(True, axis='y', alpha=0.25, color="#777777")
    ax.set_axisbelow(True)

    # Spines
    for spine in ax.spines.values():
        spine.set_color("#888888")

    plt.tight_layout()
    out = os.path.join(OUT_DIR, fname)
    plt.savefig(out, facecolor="#2d3b47", bbox_inches='tight')
    plt.close()
    print(f"Salvat: {out}")
    return out


def plot_multi_panel():
    """4 sub-plot-uri intr-o singura figura — toate metricile critice."""
    fig, axes = plt.subplots(2, 2, figsize=(13, 7), dpi=120)
    fig.suptitle("Comparatie baseline-uri vs PPO+BC trained — metrici critice",
                 fontsize=16, color="#ffffff", y=0.99)

    metrics = [
        ("Avg kills/ep", "avg_kills", "kills per episod"),
        ("Avg depth", "avg_depth", "depth mediu (camera)"),
        ("% A2/01 reach", "pct_reach_A2_01", "% episoade A2/01"),
        ("% trigger cross", "pct_trigger_cross", "% A1/03 nord cross"),
    ]

    for ax, (display, key, ylabel) in zip(axes.flatten(), metrics):
        values = [data[display][r] for r in runs]
        bars = ax.bar(labels, values, color=colors, edgecolor="#cccccc", linewidth=1.0)
        bars[-1].set_edgecolor("#ffd700")
        bars[-1].set_linewidth(2.5)
        for bar, v in zip(bars, values):
            h = bar.get_height()
            offset = max(values) * 0.02 if max(values) > 0 else 0.02
            txt = f"{v:.2f}" if v < 10 else f"{v:.0f}"
            ax.text(bar.get_x() + bar.get_width()/2.0, h + offset,
                    txt, ha='center', va='bottom', fontsize=9, color="#ffffff", weight='bold')
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(display, fontsize=12, pad=8)
        ax.grid(True, axis='y', alpha=0.2)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color("#666666")
        ax.tick_params(axis='x', labelsize=9)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(OUT_DIR, "baseline_comparison_multi.png")
    plt.savefig(out, facecolor="#2d3b47", bbox_inches='tight')
    plt.close()
    print(f"Salvat: {out}")
    return out


if __name__ == "__main__":
    plot_metric("Avg kills/ep", "Kills per episod (mediu)", "baseline_kills.png",
                title="Kills per episod: random spam castiga prin accident, doar PPO+BC e consistent")
    plot_metric("Max depth", "Depth maxim atins (camera)", "baseline_depth.png",
                title="Depth maxim: doar PPO+BC ajunge la A2/01 (depth 4)")
    plot_multi_panel()
    print("\nGata. Folosim in PPT.")
