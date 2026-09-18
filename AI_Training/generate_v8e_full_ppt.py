"""Genereaza TOATE chart-urile updated pentru PPT cu v8e inclus.
Stil identic cu baseline_comparison_multi.png din results_v4 (dark theme).

Output: results_v8e/
- baseline_comparison_multi_v8e.png  (4 paneluri: kills, depth, A2/01, trigger)
- learning_curve_v8e.png             (kills/reward/depth smoothed peste episoade)
- time_per_room_v8e.png              (% timp per cameră)
- nivel_final_v8e.png                (histogram level la final ep)
- distributie_depth_v8e.png          (histogram depth maxim per ep)
- heatmap_<room>_v8e.png             (heatmap-uri 4 camere cheie)
- compare_runs_v8e.csv               (CSV updated cu coloana v8e)

Rulare: python generate_v8e_full_ppt.py
"""
import json
import os
import csv
from collections import Counter, defaultdict
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "results_v8e")
os.makedirs(OUT_DIR, exist_ok=True)

# === DARK THEME (same as baseline_comparison_multi.png) ===
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
    "font.family":      "sans-serif",
})

SCENE_DEPTH = {
    "res://Levels/Area01/02.tscn":       1,
    "res://Levels/Area01/01.tscn":       2,
    "res://Levels/Area01/03.tscn":       3,
    "res://Levels/Area02/01.tscn":       4,
    "res://Levels/Area01/02_shop.tscn":  5,
    "res://Levels/Area02/02.tscn":       6,
    "res://Levels/Area01/04.tscn":       7,
    "res://Levels/Dungeon01/01.tscn":    8,
    "res://Levels/Dungeon01/02.tscn":    9,
    "res://Levels/Dungeon01/03.tscn":   10,
    "res://Levels/Dungeon01/04.tscn":   11,
}
SCENE_SHORT = {
    "res://Levels/Area01/02.tscn":       "A1/02",
    "res://Levels/Area01/01.tscn":       "A1/01",
    "res://Levels/Area01/03.tscn":       "A1/03",
    "res://Levels/Area02/01.tscn":       "A2/01",
    "res://Levels/Area01/02_shop.tscn":  "SHOP",
    "res://Levels/Area02/02.tscn":       "A2/02",
    "res://Levels/Area01/04.tscn":       "A1/04",
    "res://Levels/Dungeon01/01.tscn":    "D01/01",
    "res://Levels/Dungeon01/02.tscn":    "D01/02",
    "res://Levels/Dungeon01/03.tscn":    "D01/03",
    "res://Levels/Dungeon01/04.tscn":    "D01/04",
}
A2_SCENE = "res://Levels/Area02/01.tscn"


def load_episodes(path):
    if not os.path.exists(path): return []
    eps, cur = [], None
    wp350 = False; trigger = False; a2 = False; buffs = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: ev = json.loads(line)
            except: continue
            e = ev.get("event")
            if e == "run_started":
                cur = {"rooms": set()}
                wp350 = False; trigger = False; a2 = False; buffs = 0
            elif cur is not None:
                if e == "room_entered":
                    scn = ev.get("scene_path")
                    cur["rooms"].add(scn)
                    if scn == A2_SCENE: a2 = True
                elif e == "waypoint_y350": wp350 = True
                elif e == "trigger_line_crossed": trigger = True
                elif e == "buff_picked": buffs += 1
                elif e == "episode_end":
                    cur["kills"] = ev.get("kills", 0)
                    cur["time"] = ev.get("time", 0.0)
                    cur["reward"] = ev.get("reward_total", 0.0)
                    cur["outcome"] = ev.get("outcome", "")
                    cur["damage"] = ev.get("damage_taken", 0)
                    cur["level"] = ev.get("level", 1)
                    cur["buffs"] = ev.get("buff_count", buffs)
                    cur["depth"] = max((SCENE_DEPTH.get(r, 0) for r in cur["rooms"]), default=0)
                    cur["a2"] = a2
                    cur["wp350"] = wp350
                    cur["trigger"] = trigger
                    eps.append(cur)
                    cur = None
    return eps


def compute_metrics(eps):
    n = len(eps)
    if n == 0: return {"episodes": 0}
    return {
        "episodes": n,
        "avg_kills": sum(e["kills"] for e in eps) / n,
        "avg_reward": sum(e["reward"] for e in eps) / n,
        "avg_depth": sum(e["depth"] for e in eps) / n,
        "max_depth": max(e["depth"] for e in eps),
        "pct_a2": 100 * sum(1 for e in eps if e["a2"]) / n,
        "pct_trigger": 100 * sum(1 for e in eps if e["trigger"]) / n,
        "avg_time": sum(e["time"] for e in eps) / n,
        "buffs_total": sum(e["buffs"] for e in eps),
        "avg_level": sum(e["level"] for e in eps) / n,
        "max_level": max(e["level"] for e in eps),
    }


# === Load all runs ===
GODOT_BASE = "C:/Users/grigo/AppData/Roaming/Godot/app_userdata/VERSIUNE FINALA"
RUNS_BASELINE = {
    "uniform":      f"{HERE}/ai_events_uniform.jsonl",
    "realistic":    f"{HERE}/ai_events_realistic.jsonl",
    "claude_haiku": f"{HERE}/ai_events_claude_haiku.jsonl",
    "claude_opus":  f"{HERE}/ai_events_claude_opus.jsonl",
    "run5f":        f"{HERE}/ai_events_run5f.jsonl",
    "run5l_v8e":    f"{HERE}/ai_events_run5l_v8e_snapshot.jsonl",
}

LABELS = {
    "uniform":      "Random\nuniform",
    "realistic":    "Random\nrealistic",
    "claude_haiku": "Claude\nHaiku 4.5",
    "claude_opus":  "Claude\nOpus 4.7",
    "run5f":        "PPO+BC\nRun 5f",
    "run5l_v8e":    "PPO+BC\nRun 5l v8e\n(BEST)",
}

COLORS = {
    "uniform":      "#888888",
    "realistic":    "#aaaaaa",
    "claude_haiku": "#e88a4a",
    "claude_opus":  "#d46e2a",
    "run5f":        "#4cb84c",
    "run5l_v8e":    "#7ad77a",   # cel mai luminos = BEST
}

run_eps = {name: load_episodes(path) for name, path in RUNS_BASELINE.items()}
run_metrics = {name: compute_metrics(eps) for name, eps in run_eps.items()}

# NU mai filtram — folosim TOATE eps din snapshot (v8/v8b/v8e era complet).
# Filtru pe last 1000 ar fi exclus D01 reaches (care erau in mijloc).

print(f"\nEpisoade per run:")
for name, eps in run_eps.items():
    print(f"  {name}: {len(eps)} ep")

# === CHART 1: Multi-panel comparison (style baseline_comparison_multi.png) ===
def chart_comparison_multi():
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), dpi=120)
    fig.suptitle("Comparatie baseline-uri vs PPO+BC trained — Run 5l v8e e BEST",
                 fontsize=16, color="#ffffff", y=0.99)

    runs_order = ["uniform", "realistic", "claude_haiku", "claude_opus", "run5f", "run5l_v8e"]
    labels = [LABELS[r] for r in runs_order]
    colors = [COLORS[r] for r in runs_order]

    metrics_to_plot = [
        ("Avg kills/ep", lambda m: m.get("avg_kills", 0), "kills mediu", "{:.2f}"),
        ("Avg depth", lambda m: m.get("avg_depth", 0), "depth mediu (1-11)", "{:.2f}"),
        ("% A2/01 reach", lambda m: m.get("pct_a2", 0), "% episoade ating A2/01", "{:.1f}%"),
        ("% trigger A1/03", lambda m: m.get("pct_trigger", 0), "% A1/03 nord cross", "{:.1f}%"),
    ]

    for ax, (title, extract, ylabel, fmt) in zip(axes.flatten(), metrics_to_plot):
        values = [extract(run_metrics[r]) for r in runs_order]
        bars = ax.bar(labels, values, color=colors, edgecolor="#cccccc", linewidth=1.0)
        bars[-1].set_edgecolor("#ffd700")
        bars[-1].set_linewidth(2.8)
        for bar, v in zip(bars, values):
            h = bar.get_height()
            offset = max(values) * 0.02 if max(values) > 0 else 0.02
            ax.text(bar.get_x() + bar.get_width()/2.0, h + offset,
                    fmt.format(v), ha='center', va='bottom',
                    fontsize=9, color="#ffffff", weight='bold')
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=12, pad=8)
        ax.grid(True, axis='y', alpha=0.2)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color("#666666")
        ax.tick_params(axis='x', labelsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(OUT_DIR, "baseline_comparison_multi_v8e.png")
    plt.savefig(out, facecolor="#2d3b47", bbox_inches='tight')
    plt.close()
    print(f"[saved] {out}")


# === CHART 2: Learning curve (kills/reward/depth over episodes) ===
def chart_learning_curve():
    eps = run_eps["run5l_v8e"]
    if not eps:
        print("v8e no eps for learning curve"); return
    n = len(eps)
    x = np.arange(1, n + 1)
    kills = np.array([e["kills"] for e in eps])
    rewards = np.array([e["reward"] for e in eps])
    depths = np.array([e["depth"] for e in eps])

    # Smoothing window
    w = max(20, n // 50)
    def smooth(arr):
        if len(arr) < w: return arr
        return np.convolve(arr, np.ones(w)/w, mode='valid')

    sx = np.arange(w, n + 1)
    sk = smooth(kills)
    sr = smooth(rewards)
    sd = smooth(depths)

    fig, axes = plt.subplots(3, 1, figsize=(13, 9), dpi=120, sharex=True)
    fig.suptitle(f"Curba de invatare — Run 5l v8e (ultimele {n} episoade, smoothed w={w})",
                 fontsize=15, color="#ffffff", y=0.99)

    axes[0].plot(x, kills, color="#7ad77a", alpha=0.25, linewidth=0.6)
    axes[0].plot(sx, sk, color="#7ad77a", linewidth=2.4, label=f"Smoothed (w={w})")
    axes[0].set_ylabel("Kills / ep", fontsize=11)
    axes[0].legend(loc="upper left")
    axes[0].grid(True, alpha=0.2)

    axes[1].plot(x, rewards, color="#e88a4a", alpha=0.25, linewidth=0.6)
    axes[1].plot(sx, sr, color="#e88a4a", linewidth=2.4)
    axes[1].set_ylabel("Reward total / ep", fontsize=11)
    axes[1].grid(True, alpha=0.2)
    axes[1].axhline(y=0, color="#888", linestyle="--", alpha=0.5)

    axes[2].plot(x, depths, color="#3fd0d4", alpha=0.25, linewidth=0.6)
    axes[2].plot(sx, sd, color="#3fd0d4", linewidth=2.4)
    axes[2].set_ylabel("Depth max / ep (1-11)", fontsize=11)
    axes[2].set_xlabel("Episode index (in v8e era)", fontsize=11)
    axes[2].grid(True, alpha=0.2)
    axes[2].set_yticks(range(0, 12))

    for ax in axes:
        for spine in ax.spines.values():
            spine.set_color("#666666")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(OUT_DIR, "learning_curve_v8e.png")
    plt.savefig(out, facecolor="#2d3b47", bbox_inches='tight')
    plt.close()
    print(f"[saved] {out}")


# === CHART 3: Time per room ===
def chart_time_per_room():
    # Use positions.jsonl for v8e era (last ~969 ep)
    eps_time = defaultdict(float)
    eps_count = defaultdict(int)
    pos_file = f"{HERE}/positions.jsonl"
    with open(pos_file, encoding="utf-8") as f:
        for line in f:
            try: d = json.loads(line)
            except: continue
            s = d.get("scene", "")
            if s in SCENE_DEPTH:
                eps_time[s] += 1  # each sample = 4 steps * 0.08s = 0.32s
                eps_count[s] += 1
    # Convert to seconds
    times_s = {s: c * 0.32 for s, c in eps_count.items()}
    total = sum(times_s.values())

    sorted_rooms = sorted(times_s.keys(), key=lambda s: SCENE_DEPTH[s])
    labels = [SCENE_SHORT[s] for s in sorted_rooms]
    values_pct = [100 * times_s[s] / total for s in sorted_rooms]
    values_min = [times_s[s] / 60 for s in sorted_rooms]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), dpi=120)
    fig.suptitle("Timp petrecut per cameră — Run 5l v8e",
                 fontsize=15, color="#ffffff", y=1.02)

    # Panel 1: % time
    colors_room = plt.cm.viridis(np.linspace(0.2, 0.9, len(labels)))
    bars1 = axes[0].bar(labels, values_pct, color=colors_room, edgecolor="#cccccc")
    for bar, v in zip(bars1, values_pct):
        h = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width()/2.0, h + 0.5,
                     f"{v:.1f}%", ha='center', va='bottom', fontsize=9, color="#ffffff", weight='bold')
    axes[0].set_ylabel("% din total timp", fontsize=11)
    axes[0].set_title("Distributie procentuala", fontsize=12)
    axes[0].grid(True, axis='y', alpha=0.2)
    axes[0].tick_params(axis='x', labelsize=10, rotation=20)

    # Panel 2: absolute minutes
    bars2 = axes[1].bar(labels, values_min, color=colors_room, edgecolor="#cccccc")
    for bar, v in zip(bars2, values_min):
        h = bar.get_height()
        axes[1].text(bar.get_x() + bar.get_width()/2.0, h + max(values_min)*0.01,
                     f"{v:.1f}m", ha='center', va='bottom', fontsize=9, color="#ffffff", weight='bold')
    axes[1].set_ylabel("Timp absolut (min)", fontsize=11)
    axes[1].set_title("Timp absolut", fontsize=12)
    axes[1].grid(True, axis='y', alpha=0.2)
    axes[1].tick_params(axis='x', labelsize=10, rotation=20)

    for ax in axes:
        for spine in ax.spines.values():
            spine.set_color("#666666")

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "time_per_room_v8e.png")
    plt.savefig(out, facecolor="#2d3b47", bbox_inches='tight')
    plt.close()
    print(f"[saved] {out}")


# === CHART 4: Player level distribution at end of episode ===
def chart_level_final():
    eps = run_eps["run5l_v8e"]
    if not eps: return
    levels = [e["level"] for e in eps]
    max_lv = max(levels)

    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=120)
    counts = Counter(levels)
    levels_sorted = sorted(counts.keys())
    counts_sorted = [counts[l] for l in levels_sorted]

    bars = ax.bar(levels_sorted, counts_sorted,
                  color="#7ad77a", edgecolor="#ffd700", linewidth=1.4)
    for bar, v in zip(bars, counts_sorted):
        ax.text(bar.get_x() + bar.get_width()/2.0, v + max(counts_sorted)*0.01,
                str(v), ha='center', va='bottom', fontsize=10, color="#ffffff", weight='bold')

    ax.set_xlabel("Nivel player la final de episod", fontsize=12)
    ax.set_ylabel("Numar episoade", fontsize=12)
    ax.set_title(f"Distributia nivelului final — Run 5l v8e ({len(eps)} ep, max nivel {max_lv})",
                 fontsize=14, pad=10)
    ax.set_xticks(levels_sorted)
    ax.grid(True, axis='y', alpha=0.2)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color("#666666")

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "nivel_final_v8e.png")
    plt.savefig(out, facecolor="#2d3b47", bbox_inches='tight')
    plt.close()
    print(f"[saved] {out}")


# === CHART 5: Depth distribution (progress) ===
def chart_depth_distribution():
    eps = run_eps["run5l_v8e"]
    if not eps: return
    depths = [e["depth"] for e in eps]

    fig, ax = plt.subplots(figsize=(13, 5.5), dpi=120)
    counts = Counter(depths)
    depths_all = list(range(0, 12))
    counts_all = [counts.get(d, 0) for d in depths_all]
    labels_d = [SCENE_SHORT[s] for d, s in
                sorted([(v, k) for k, v in SCENE_DEPTH.items()])
                if d in depths_all]
    # Map depth -> short name
    DEPTH_LABELS = {0: "ne-intrat", 1: "A1/02", 2: "A1/01", 3: "A1/03", 4: "A2/01",
                    5: "SHOP", 6: "A2/02", 7: "A1/04", 8: "D01/01",
                    9: "D01/02", 10: "D01/03", 11: "D01/04"}
    xlabels = [f"{d}\n{DEPTH_LABELS[d]}" for d in depths_all]

    # Color gradient: deeper = greener
    colors_d = plt.cm.RdYlGn(np.linspace(0.15, 0.9, len(depths_all)))
    bars = ax.bar(range(len(depths_all)), counts_all,
                  color=colors_d, edgecolor="#cccccc", linewidth=0.8)
    for bar, v in zip(bars, counts_all):
        if v > 0:
            ax.text(bar.get_x() + bar.get_width()/2.0, v + max(counts_all)*0.01,
                    str(v), ha='center', va='bottom', fontsize=9, color="#ffffff", weight='bold')

    ax.set_xticks(range(len(depths_all)))
    ax.set_xticklabels(xlabels, fontsize=9)
    ax.set_xlabel("Depth maxim atins (cameră cea mai adâncă)", fontsize=12)
    ax.set_ylabel("Numar episoade", fontsize=12)
    ax.set_title(f"Distributia depth maxim per ep — Run 5l v8e ({len(eps)} ep)",
                 fontsize=14, pad=10)
    ax.grid(True, axis='y', alpha=0.2)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color("#666666")

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "distributie_depth_v8e.png")
    plt.savefig(out, facecolor="#2d3b47", bbox_inches='tight')
    plt.close()
    print(f"[saved] {out}")


# === CHART 6: Heatmaps for key rooms (stilul vechi din heatmap.py — light theme, bilinear) ===
def chart_heatmaps():
    pos_file = f"{HERE}/positions.jsonl"
    room_pos = defaultdict(list)
    with open(pos_file, encoding="utf-8") as f:
        for line in f:
            try: d = json.loads(line)
            except: continue
            s = d.get("scene", "")
            x = d.get("x", 0); y = d.get("y", 0)
            if s in SCENE_DEPTH:
                room_pos[s].append((x, y))

    # Bounds REALE camere — match cu heatmap.py original
    ROOM_BOUNDS = {
        "res://Levels/Area01/03.tscn":   (-50, 650, -650, 380),
        "res://Levels/Area02/01.tscn":   (-50, 700, -400, 1100),
        "res://Levels/Area02/02.tscn":   (-50, 700, -50, 700),
        "res://Levels/Dungeon01/01.tscn": (-50, 500, -50, 500),
    }
    SCENE_LABELS = {
        "res://Levels/Area01/03.tscn":   "Area01_03",
        "res://Levels/Area02/01.tscn":   "Area02_01",
        "res://Levels/Area02/02.tscn":   "Area02_02_Levers",
        "res://Levels/Dungeon01/01.tscn": "Dungeon01_01_Statue",
    }

    # Switch la default style pentru heatmaps (light background)
    with plt.style.context("default"):
        for scene, pts in room_pos.items():
            if scene not in ROOM_BOUNDS or len(pts) < 10: continue
            x_min, x_max, y_min, y_max = ROOM_BOUNDS[scene]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]

            # Bins adaptiv: mai putine pt sparse data (eviti pixelat ugly)
            bins = 60 if len(pts) > 500 else 40 if len(pts) > 100 else 25
            h, xedges, yedges = np.histogram2d(xs, ys, bins=bins,
                                                range=[[x_min, x_max], [y_min, y_max]])

            fig, ax = plt.subplots(figsize=(8, 6))
            # YlOrRd start la alb → light background pentru zone neexplorate
            # gaussian interpolation = smooth pentru sparse data
            img = ax.imshow(
                h.T,
                origin="upper",
                extent=[x_min, x_max, y_max, y_min],
                aspect="auto",
                cmap="YlOrRd",  # white → yellow → orange → red (clean)
                interpolation="gaussian",
            )
            plt.colorbar(img, ax=ax, label="Vizite")
            scene_label = SCENE_LABELS[scene]
            ax.set_title(f"Heatmap pozitii — {scene_label} (Run 5l v8e)\n({len(pts)} sample-uri)")
            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            ax.set_facecolor("white")
            plt.tight_layout()

            out = os.path.join(OUT_DIR, f"heatmap_{scene_label}_v8e.png")
            plt.savefig(out, dpi=120, facecolor="white")
            plt.close()
            print(f"[saved] {out}")


# === CSV updated ===
def write_csv():
    runs_order = ["uniform", "realistic", "claude_haiku", "claude_opus", "run5f", "run5l_v8e"]
    rows = [
        ("Episoade", lambda m: m.get("episodes", 0)),
        ("Avg kills/ep", lambda m: round(m.get("avg_kills", 0), 2)),
        ("Avg reward/ep", lambda m: round(m.get("avg_reward", 0), 1)),
        ("Avg depth", lambda m: round(m.get("avg_depth", 0), 2)),
        ("Max depth", lambda m: m.get("max_depth", 0)),
        ("Avg timp (s)", lambda m: round(m.get("avg_time", 0), 1)),
        ("% A2/01 reach", lambda m: round(m.get("pct_a2", 0), 2)),
        ("% trigger cross", lambda m: round(m.get("pct_trigger", 0), 2)),
        ("Buffs total", lambda m: m.get("buffs_total", 0)),
        ("Avg level final", lambda m: round(m.get("avg_level", 0), 2)),
        ("Max level final", lambda m: m.get("max_level", 0)),
    ]
    csv_path = os.path.join(OUT_DIR, "compare_runs_v8e.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Metrica"] + runs_order)
        for label, extract in rows:
            w.writerow([label] + [extract(run_metrics[r]) for r in runs_order])
    print(f"[saved] {csv_path}")
    return csv_path


# === CHART 7: Conversion funnel (% ep ajung la fiecare milestone) ===
def chart_conversion_funnel():
    eps = run_eps["run5l_v8e"]
    if not eps: return
    n = len(eps)
    milestones = [
        ("Start (A1/02)", 1),
        ("A1/01 reach", 2),
        ("A1/03 reach", 3),
        ("A2/01 reach", 4),
        ("SHOP reach", 5),
        ("A2/02 reach", 6),
        ("A1/04 reach", 7),
        ("D01/01 reach", 8),
    ]
    counts = []
    for label, d in milestones:
        c = sum(1 for e in eps if e["depth"] >= d)
        counts.append(c)
    pcts = [100 * c / n for c in counts]

    fig, ax = plt.subplots(figsize=(13, 6), dpi=120)
    y_pos = np.arange(len(milestones))
    labels = [m[0] for m in milestones]
    colors_funnel = plt.cm.RdYlGn(np.linspace(0.15, 0.9, len(milestones)))

    bars = ax.barh(y_pos, pcts, color=colors_funnel, edgecolor="#cccccc", linewidth=1.0)
    for i, (bar, c, pct) in enumerate(zip(bars, counts, pcts)):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f"{c} ep ({pct:.2f}%)", ha='left', va='center',
                fontsize=10, color="#ffffff", weight='bold')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel("% episoade care ating milestone", fontsize=11)
    ax.set_title(f"Conversion funnel — Run 5l v8e ({n} ep)\nDrop-off cap-coada per cameră",
                 fontsize=14, pad=12)
    ax.grid(True, axis='x', alpha=0.2)
    ax.set_axisbelow(True)
    ax.set_xlim(0, max(pcts) * 1.25)
    for spine in ax.spines.values():
        spine.set_color("#666666")

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "conversion_funnel_v8e.png")
    plt.savefig(out, facecolor="#2d3b47", bbox_inches='tight')
    plt.close()
    print(f"[saved] {out}")


# === CHART 8: Reward chunked over training ===
def chart_reward_chunks():
    eps = run_eps["run5l_v8e"]
    if not eps: return
    chunk = 100
    chunks_idx = list(range(0, len(eps), chunk))
    chunks_avg_r = []; chunks_avg_d = []; chunks_avg_k = []
    for i in chunks_idx:
        chunk_eps = eps[i:i+chunk]
        chunks_avg_r.append(np.mean([e["reward"] for e in chunk_eps]))
        chunks_avg_d.append(np.mean([e["depth"] for e in chunk_eps]))
        chunks_avg_k.append(np.mean([e["kills"] for e in chunk_eps]))

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), dpi=120)
    fig.suptitle(f"Trend evolutie per chunk de {chunk} ep — Run 5l v8e ({len(eps)} ep total)",
                 fontsize=15, color="#ffffff", y=1.01)

    x_lbl = [f"{i//chunk+1}" for i in chunks_idx]
    x_vals = np.arange(len(chunks_idx))

    axes[0].plot(x_vals, chunks_avg_r, color="#e88a4a", marker='o', linewidth=2, markersize=6)
    axes[0].axhline(y=0, color="#888", linestyle="--", alpha=0.5)
    axes[0].set_title("Avg reward / chunk", fontsize=12)
    axes[0].set_xlabel(f"Chunk #{chunk}ep", fontsize=10)
    axes[0].set_ylabel("Reward mediu", fontsize=10)

    axes[1].plot(x_vals, chunks_avg_d, color="#3fd0d4", marker='s', linewidth=2, markersize=6)
    axes[1].set_title("Avg depth max / chunk", fontsize=12)
    axes[1].set_xlabel(f"Chunk #{chunk}ep", fontsize=10)
    axes[1].set_ylabel("Depth mediu (1-11)", fontsize=10)
    axes[1].set_yticks(range(0, 9))

    axes[2].plot(x_vals, chunks_avg_k, color="#7ad77a", marker='^', linewidth=2, markersize=6)
    axes[2].set_title("Avg kills / chunk", fontsize=12)
    axes[2].set_xlabel(f"Chunk #{chunk}ep", fontsize=10)
    axes[2].set_ylabel("Kills medii", fontsize=10)

    for ax in axes:
        ax.grid(True, alpha=0.2)
        for spine in ax.spines.values():
            spine.set_color("#666666")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(OUT_DIR, "reward_chunks_v8e.png")
    plt.savefig(out, facecolor="#2d3b47", bbox_inches='tight')
    plt.close()
    print(f"[saved] {out}")


# === CHART 9: Outcome breakdown (fail / trunc / win) ===
def chart_outcome_breakdown():
    eps = run_eps["run5l_v8e"]
    if not eps: return
    outcomes = Counter(e["outcome"] for e in eps)
    # Normalize labels
    labels_map = {
        "fail": "Moarte",
        "truncated_room": "Trunc cameră (step limit)",
        "truncated_global": "Trunc global (timer)",
        "win": "Win (boss kill)",
        "": "Necunoscut",
    }

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), dpi=120)
    fig.suptitle(f"Outcome breakdown — Run 5l v8e ({len(eps)} ep)",
                 fontsize=15, color="#ffffff", y=0.99)

    # Panel 1: Pie chart
    sorted_oc = sorted(outcomes.items(), key=lambda x: -x[1])
    labels = [labels_map.get(o, o) for o, _ in sorted_oc]
    sizes = [c for _, c in sorted_oc]
    colors_pie = ["#e74c3c", "#f39c12", "#9b59b6", "#27ae60", "#888888"][:len(sizes)]

    wedges, texts, autotexts = axes[0].pie(sizes, labels=labels, colors=colors_pie,
                                            autopct=lambda p: f"{p:.1f}%\n({int(p*sum(sizes)/100)})",
                                            startangle=90, textprops={'fontsize': 10, 'color': '#fff'},
                                            wedgeprops={'edgecolor': '#2d3b47', 'linewidth': 2})
    axes[0].set_title("Distributie outcome", fontsize=13, pad=10)

    # Panel 2: Bar count
    axes[1].bar(labels, sizes, color=colors_pie, edgecolor="#cccccc", linewidth=1.0)
    for i, (lbl, c) in enumerate(zip(labels, sizes)):
        axes[1].text(i, c + max(sizes)*0.01, str(c), ha='center', va='bottom',
                     fontsize=11, color="#ffffff", weight='bold')
    axes[1].set_ylabel("Numar episoade", fontsize=11)
    axes[1].set_title("Count absolut", fontsize=13, pad=10)
    axes[1].grid(True, axis='y', alpha=0.2)
    axes[1].set_axisbelow(True)
    axes[1].tick_params(axis='x', labelsize=9, rotation=15)
    for spine in axes[1].spines.values():
        spine.set_color("#666666")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(OUT_DIR, "outcome_breakdown_v8e.png")
    plt.savefig(out, facecolor="#2d3b47", bbox_inches='tight')
    plt.close()
    print(f"[saved] {out}")


# === CHART 10: Death position heatmap (where AI dies most) ===
def chart_death_heatmap():
    # Read ai_events for death positions
    deaths_per_scene = defaultdict(list)
    path = f"{HERE}/ai_events_run5l_v8e_snapshot.jsonl"
    with open(path, encoding="utf-8") as f:
        for line in f:
            try: ev = json.loads(line)
            except: continue
            if ev.get("event") == "episode_end" and ev.get("outcome") == "fail":
                scn = ev.get("scene_path", "")
                dx = ev.get("death_x"); dy = ev.get("death_y")
                if scn and dx is not None and dy is not None:
                    deaths_per_scene[scn].append((dx, dy))

    ROOM_BOUNDS = {
        "res://Levels/Area01/02.tscn":   (-50, 500, -100, 400),
        "res://Levels/Area01/01.tscn":   (50, 450, -50, 380),
        "res://Levels/Area01/03.tscn":   (-50, 650, -650, 380),
        "res://Levels/Area02/01.tscn":   (-50, 700, -400, 1100),
    }
    SCENE_LABELS = {
        "res://Levels/Area01/02.tscn": "Area01_02_NPC",
        "res://Levels/Area01/01.tscn": "Area01_01_Goblins",
        "res://Levels/Area01/03.tscn": "Area01_03",
        "res://Levels/Area02/01.tscn": "Area02_01",
    }

    with plt.style.context("default"):
        for scene, pts in deaths_per_scene.items():
            if scene not in ROOM_BOUNDS or len(pts) < 5: continue
            x_min, x_max, y_min, y_max = ROOM_BOUNDS[scene]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]

            fig, ax = plt.subplots(figsize=(8, 6))
            # Scatter cu transparenta — vezi cluster fara sa fie ugly cu binning sparse
            ax.scatter(xs, ys, c="#e74c3c", s=25, alpha=0.4, edgecolors='black', linewidths=0.4)
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_max, y_min)
            ax.set_aspect("auto")
            ax.set_facecolor("#f5f5f5")
            ax.grid(True, alpha=0.4, color="#bbb", linestyle="--")
            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            label = SCENE_LABELS[scene]
            ax.set_title(f"Pozitii de moarte AI — {label}\n({len(pts)} morti din ep cu outcome=fail)")
            plt.tight_layout()

            out = os.path.join(OUT_DIR, f"death_positions_{label}_v8e.png")
            plt.savefig(out, dpi=120, facecolor="white")
            plt.close()
            print(f"[saved] {out}")


if __name__ == "__main__":
    print("=" * 60)
    print("Generez chart-uri actualizate cu v8e...")
    print("=" * 60)
    chart_comparison_multi()
    chart_learning_curve()
    chart_time_per_room()
    chart_level_final()
    chart_depth_distribution()
    chart_heatmaps()
    chart_conversion_funnel()
    chart_reward_chunks()
    chart_outcome_breakdown()
    chart_death_heatmap()
    write_csv()
    print()
    print("Toate chart-urile salvate in:", OUT_DIR)
