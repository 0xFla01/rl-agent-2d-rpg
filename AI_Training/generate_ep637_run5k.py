"""Traseu ep 637 din Run 5k — episodul care ATINGE A2/02 cu cel mai lung stay.
Stilul top_runs_chart_run5f, dar 5 camere (extins cu A2/02 — boss area).
Rulare:  python generate_ep637_run5k.py
Output:  results_v4/traseu_ep637_run5k_A202.png
"""
import json
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

POS_FILE = "positions_run5k.jsonl"
OUT_DIR = "results_v4"
os.makedirs(OUT_DIR, exist_ok=True)

EP = 637

ROOM_BOUNDS = {
    "res://Levels/Area01/02.tscn":      (-50, 500,  -150, 400),
    "res://Levels/Area01/01.tscn":      (  0, 480,   -80, 380),
    "res://Levels/Area01/03.tscn":      (-50, 650,  -650, 380),
    "res://Levels/Area02/01.tscn":      (-100, 700, -100, 1150),
    "res://Levels/Area02/02.tscn":      (-50, 700,   -50, 650),
    "res://Levels/Area01/02_shop.tscn": (100, 420,    -20, 260),
}
ROOM_SHORT = {
    "res://Levels/Area01/02.tscn":      "Area01/02 — Start (NPC)",
    "res://Levels/Area01/01.tscn":      "Area01/01 — Combat Goblini",
    "res://Levels/Area01/03.tscn":      "Area01/03 — Buff Room",
    "res://Levels/Area02/01.tscn":      "Area02/01 — Waves + Pod",
    "res://Levels/Area02/02.tscn":      "Area02/02 — BOSS REACH",
    "res://Levels/Area01/02_shop.tscn": "Shop NPC (A1/02 vendor)",
}

ROOM_LANDMARKS = {
    "res://Levels/Area01/02.tscn": {
        "spawn":    (244, 152),
        "door_in":  None,
        "door_out": (224, -55, "Usa nord -> A1/01"),
    },
    "res://Levels/Area01/01.tscn": {
        "spawn":    (209, 317),
        "door_in":  (240, 320, "Usa sud <- A1/02"),
        "door_out": (240, -32, "Usa nord -> A1/03"),
    },
    "res://Levels/Area01/03.tscn": {
        "spawn":    (266, 301),
        "door_in":  (272, 320, "Usa sud <- A1/01"),
        "door_out": (587, -594, "Usa NE -> A2/01"),
    },
    "res://Levels/Area02/01.tscn": {
        "spawn":    (-33, 70),
        "door_in":  (-51, 63, "Usa vest <- A1/03"),
        "door_out": (416, 1105, "Usa sud -> A2/02"),
    },
    "res://Levels/Area02/02.tscn": {
        "spawn":    (308, 53),
        "door_in":  (308, 30, "Usa nord <- A2/01"),
        "door_out": None,
    },
    "res://Levels/Area01/02_shop.tscn": {
        "spawn":    (131, 95),
        "door_in":  None,
        "door_out": None,
    },
}

ROOM_GUIDES = {
    "res://Levels/Area01/03.tscn": {
        "trigger_y": (-490, "Trigger Line y=-490"),
        "waypoints": [(0, "WP y=0"), (-200, "WP y=-200"), (-350, "WP y=-350")],
    },
    "res://Levels/Area02/01.tscn": {
        "trigger_y": None,
        "waypoints": [(300, "WP y=300"), (600, "WP y=600 (pod)"),
                      (900, "WP y=900 (pod)"), (1050, "WP y=1050")],
    },
}

CANONICAL = [
    "res://Levels/Area01/02.tscn",
    "res://Levels/Area01/01.tscn",
    "res://Levels/Area01/03.tscn",
    "res://Levels/Area02/01.tscn",
    "res://Levels/Area01/02_shop.tscn",
    "res://Levels/Area02/02.tscn",
]


def load_positions_for_ep(path, target_ep):
    out = []
    with open(path, "r") as f:
        for line in f:
            try:
                d = json.loads(line)
                if d.get("episode") == target_ep:
                    out.append((d["x"], d["y"], d["scene"]))
            except Exception:
                continue
    return out


def segments_for_scene(positions, target_scene):
    segs, cur = [], []
    for x, y, s in positions:
        if s == target_scene:
            cur.append((x, y))
        else:
            if cur:
                segs.append(cur); cur = []
    if cur:
        segs.append(cur)
    return segs


def find_last_exit_position(positions, from_scene, to_scene):
    last_idx = None
    for i in range(len(positions) - 1):
        if positions[i][2] == from_scene and positions[i + 1][2] == to_scene:
            last_idx = i
    if last_idx is None:
        return None
    return positions[last_idx][0], positions[last_idx][1]


def find_final_position_in_scene(positions, scene):
    for i in range(len(positions) - 1, -1, -1):
        if positions[i][2] == scene:
            return positions[i][0], positions[i][1]
    return None


def plot_room(ax, scene, positions, all_positions):
    ax.set_facecolor("white")
    bx0, bx1, by0, by1 = ROOM_BOUNDS[scene]
    ax.set_xlim(bx0, bx1)
    ax.set_ylim(by1, by0)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, color="#e6e6e6", linewidth=0.6, zorder=0)
    ax.set_xlabel("X", fontsize=10)
    ax.set_ylabel("Y (jos = sud)", fontsize=10)
    ax.tick_params(labelsize=9)

    segs = segments_for_scene(positions, scene)
    pts_in_room = sum(len(s) for s in segs)

    guides = ROOM_GUIDES.get(scene)
    if guides:
        if guides.get("trigger_y") is not None:
            ty, _ = guides["trigger_y"]
            ax.axhline(y=ty, color="#f4c430", linestyle="--", linewidth=2.0, zorder=1, alpha=0.85)
            ax.text(bx1 - 5, ty - 5, f"trigger y={ty}", fontsize=8,
                    color="#b8860b", ha="right", va="bottom", zorder=8)
        for wy, _ in guides.get("waypoints", []):
            ax.axhline(y=wy, color="#ff9966", linestyle=":", linewidth=1.0, zorder=1, alpha=0.7)
            ax.text(bx1 - 5, wy - 4, f"WP y={wy}", fontsize=7,
                    color="#cc5500", ha="right", va="bottom", zorder=8)

    if not segs:
        ax.text(0.5, 0.5, "NEATINS", transform=ax.transAxes,
                ha="center", va="center", fontsize=18, color="#bbb",
                style="italic", fontweight="bold")
        ax.set_title(f"{ROOM_SHORT[scene]}\n(neatins in ep)", fontsize=12, pad=8)
        return

    all_pts = [p for seg in segs for p in seg]
    n = len(all_pts)
    cmap = plt.cm.plasma
    idx_counter = 0
    for seg in segs:
        xs = [p[0] for p in seg]; ys = [p[1] for p in seg]
        ax.plot(xs, ys, color="#3fd0d4", linewidth=1.4, alpha=0.65, zorder=2)
        seg_n = len(seg)
        ts = [(idx_counter + i) / max(n - 1, 1) for i in range(seg_n)]
        ax.scatter(xs, ys, c=ts, cmap=cmap, s=18, zorder=3,
                   edgecolors="none", vmin=0, vmax=1)
        idx_counter += seg_n

    lm = ROOM_LANDMARKS.get(scene, {})
    sp = lm.get("spawn")
    if sp:
        ax.scatter(sp[0], sp[1], s=240, color="#2ecc71", edgecolor="black",
                   linewidth=1.8, marker="s", zorder=7)
    door_in = lm.get("door_in")
    if door_in:
        ax.scatter(door_in[0], door_in[1], s=260, color="#3498db",
                   edgecolor="black", linewidth=1.8, marker="^", zorder=7)
    door_out = lm.get("door_out")
    if door_out:
        ax.scatter(door_out[0], door_out[1], s=360, color="#e74c3c",
                   edgecolor="black", linewidth=1.8, marker="*", zorder=7)

    idx = CANONICAL.index(scene) if scene in CANONICAL else -1
    exit_pt_raw = None; exit_pt_snap = None; exit_label = ""
    if idx >= 0 and idx + 1 < len(CANONICAL):
        next_scene = CANONICAL[idx + 1]
        exit_pt_raw = find_last_exit_position(all_positions, scene, next_scene)
        if exit_pt_raw is not None:
            do = ROOM_LANDMARKS.get(scene, {}).get("door_out")
            if do is not None:
                exit_pt_snap = (do[0], do[1])
                exit_label = "iesire spre cam. urm."
            else:
                exit_pt_snap = exit_pt_raw
                exit_label = "ultima poz inainte de iesire"
    if exit_pt_snap is None:
        fp = find_final_position_in_scene(all_positions, scene)
        if fp is not None:
            exit_pt_snap = fp; exit_pt_raw = fp
            exit_label = "poz finala (nu a iesit spre urm.)"

    if exit_pt_snap is not None:
        if exit_pt_raw is not None and exit_pt_raw != exit_pt_snap:
            ax.plot([exit_pt_raw[0], exit_pt_snap[0]],
                    [exit_pt_raw[1], exit_pt_snap[1]],
                    color="#aaa", linestyle=":", linewidth=1.2, zorder=4)
        ax.scatter(exit_pt_snap[0], exit_pt_snap[1], s=220, color="#ffd633",
                   edgecolor="black", linewidth=1.6, marker="o", zorder=8)
        ax.annotate(exit_label, xy=exit_pt_snap,
                    xytext=(10, 10), textcoords="offset points",
                    fontsize=8, color="#9a7800",
                    bbox=dict(boxstyle="round,pad=0.25", fc="#fffde0",
                              ec="#c0a020", lw=0.8),
                    zorder=9)

    ax.set_title(f"{ROOM_SHORT[scene]}\n{pts_in_room} pozitii in camera",
                 fontsize=12, pad=8, fontweight="bold")


def plot_episode(ep, positions, out_dir):
    visited_order = []
    seen = set()
    for x, y, s in positions:
        if s in CANONICAL and s not in seen:
            visited_order.append(s); seen.add(s)
    if not visited_order:
        print(f"ep {ep}: no canonical scenes visited")
        return

    n_cols = len(visited_order)
    fig, axes = plt.subplots(nrows=1, ncols=n_cols, figsize=(6.5 * n_cols, 8.0))
    if n_cols == 1: axes = [axes]
    fig.patch.set_facecolor("white")

    fig.suptitle(
        f"Traseul agentului — Episode {ep} (Run 5k_v2)\n"
        f"Path: A1/02 -> A1/01 -> A1/03 (trigger) -> A2/01 (waves+pod) -> Shop NPC -> A2/02 (BOSS REACH)",
        fontsize=14, fontweight="bold", y=0.99,
    )

    for ax, scene in zip(axes, visited_order):
        plot_room(ax, scene, positions, positions)

    # Legenda generala
    legend_elements = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#2ecc71",
               markeredgecolor="black", markersize=12, label="Spawn (PlayerSpawn)"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#3498db",
               markeredgecolor="black", markersize=12, label="Usa intrare"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#e74c3c",
               markeredgecolor="black", markersize=16, label="Usa iesire (door_out)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#ffd633",
               markeredgecolor="black", markersize=11, label="Iesire reala (snapped la usa)"),
        Line2D([0], [0], color="#f4c430", linestyle="--", linewidth=2,
               label="Trigger Line (A1/03 y=-490)"),
        Line2D([0], [0], color="#ff9966", linestyle=":", linewidth=1.5,
               label="Waypoint reward"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=6,
               fontsize=10, frameon=False, bbox_to_anchor=(0.5, 0.0))

    plt.tight_layout(rect=[0, 0.04, 1, 0.94])
    out = os.path.join(out_dir, f"traseu_ep{ep}_run5k_A202_with_shop.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"[saved] {out}")


if __name__ == "__main__":
    pos = load_positions_for_ep(POS_FILE, EP)
    print(f"ep {EP}: {len(pos)} pozitii incarcate")
    plot_episode(EP, pos, OUT_DIR)
