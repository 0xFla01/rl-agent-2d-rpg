"""Traseu run cap-coada Run 5l_v8e — primul ep LEGIT ce ajunge in Dungeon01/01
(post-fix lever door collision 40x56 = forteaza puzzle complet 4/4 levere).

Rulare: python generate_v8e_d01_run.py
Output: results_v8e/traseu_ep{EP}_run5l_v8e_D01.png
"""
import json
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

POS_FILE = "positions.jsonl"
OUT_DIR = "results_v8e"
os.makedirs(OUT_DIR, exist_ok=True)

# Cel mai recent ep care a ajuns in D01 (post v8c lever fix)
EP = 13976

ROOM_BOUNDS = {
    "res://Levels/Area01/02.tscn":      (-50, 500,  -150, 400),
    "res://Levels/Area01/01.tscn":      (  0, 480,   -80, 380),
    "res://Levels/Area01/03.tscn":      (-50, 650,  -650, 380),
    "res://Levels/Area02/01.tscn":      (-100, 700, -100, 1150),
    "res://Levels/Area01/02_shop.tscn": (100, 420,    -20, 260),
    "res://Levels/Area02/02.tscn":      (-50, 700,   -50, 650),
    "res://Levels/Area01/04.tscn":      (-50, 500,   -50, 400),
    "res://Levels/Dungeon01/01.tscn":   (-50, 600,   -50, 500),
}

ROOM_SHORT = {
    "res://Levels/Area01/02.tscn":      "Area01/02 — Start (NPC)",
    "res://Levels/Area01/01.tscn":      "Area01/01 — Combat Goblini",
    "res://Levels/Area01/03.tscn":      "Area01/03 — Buff Room",
    "res://Levels/Area02/01.tscn":      "Area02/01 — Waves",
    "res://Levels/Area01/02_shop.tscn": "Shop NPC",
    "res://Levels/Area02/02.tscn":      "Area02/02 — LEVER PUZZLE",
    "res://Levels/Area01/04.tscn":      "Area01/04 — Dungeon Entry",
    "res://Levels/Dungeon01/01.tscn":   "Dungeon01/01 — STATUE PUZZLE",
}

ROOM_LANDMARKS = {
    "res://Levels/Area01/02.tscn": {
        "spawn":    (244, 152),
        "door_out": (224, -55, "Nord -> A1/01"),
    },
    "res://Levels/Area01/01.tscn": {
        "spawn":    (209, 317),
        "door_in":  (240, 320, "Sud <- A1/02"),
        "door_out": (240, -32, "Nord -> A1/03"),
    },
    "res://Levels/Area01/03.tscn": {
        "spawn":    (266, 301),
        "door_in":  (272, 320, "Sud <- A1/01"),
        "door_out": (587, -594, "NE -> A2/01"),
    },
    "res://Levels/Area02/01.tscn": {
        "spawn":    (-33, 70),
        "door_in":  (-51, 63, "Vest <- A1/03"),
        "door_out": (416, 1105, "Sud -> SHOP"),
    },
    "res://Levels/Area01/02_shop.tscn": {
        "spawn":    (131, 95),
        "door_out": (291, 243, "Sud -> A2/02"),
    },
    "res://Levels/Area02/02.tscn": {
        "spawn":    (308, 53),
        "door_in":  (308, 30, "Nord <- SHOP"),
        "door_out": (336, 561, "Sud -> A1/04 (gated 4 levere)"),
    },
    "res://Levels/Area01/04.tscn": {
        "door_out": None,
    },
    "res://Levels/Dungeon01/01.tscn": {
        "door_in":  None,
    },
}

# Levere A2/02 (din scena 02.tscn)
LEVER_POSITIONS = {
    "Lever1": (66, 471),
    "Lever2": (573, 61),
    "Lever3": (78, 205),
    "Lever4": (593, 536),
}

ROOM_GUIDES = {
    "res://Levels/Area01/03.tscn": {
        "trigger_y": (-490, "Trigger y=-490"),
        "waypoints": [(0, "y=0"), (-200, "y=-200"), (-350, "y=-350")],
    },
    "res://Levels/Area02/01.tscn": {
        "waypoints": [(300, "y=300"), (600, "y=600"),
                      (900, "y=900"), (1050, "y=1050")],
    },
}

CANONICAL = [
    "res://Levels/Area01/02.tscn",
    "res://Levels/Area01/01.tscn",
    "res://Levels/Area01/03.tscn",
    "res://Levels/Area02/01.tscn",
    "res://Levels/Area01/02_shop.tscn",
    "res://Levels/Area02/02.tscn",
    "res://Levels/Area01/04.tscn",
    "res://Levels/Dungeon01/01.tscn",
]


def load_positions_for_ep(path, target_ep):
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                if d.get("episode") == target_ep or d.get("ep") == target_ep:
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
    ax.set_xlabel("X", fontsize=9)
    ax.set_ylabel("Y", fontsize=9)
    ax.tick_params(labelsize=8)

    segs = segments_for_scene(positions, scene)
    pts_in_room = sum(len(s) for s in segs)

    # Guides (trigger lines, waypoints)
    guides = ROOM_GUIDES.get(scene)
    if guides:
        ty = guides.get("trigger_y")
        if ty is not None:
            ax.axhline(y=ty[0], color="#f4c430", linestyle="--",
                       linewidth=2.0, zorder=1, alpha=0.85)
            ax.text(bx1 - 5, ty[0] - 5, ty[1], fontsize=7,
                    color="#b8860b", ha="right", va="bottom", zorder=8)
        for wy in guides.get("waypoints", []):
            ax.axhline(y=wy[0], color="#ff9966", linestyle=":",
                       linewidth=1.0, zorder=1, alpha=0.7)
            ax.text(bx1 - 5, wy[0] - 4, wy[1], fontsize=6,
                    color="#cc5500", ha="right", va="bottom", zorder=8)

    # Lever positions A2/02
    if "Area02/02" in scene:
        for name, (lx, ly) in LEVER_POSITIONS.items():
            ax.scatter(lx, ly, s=180, color="#9b59b6", edgecolor="black",
                       linewidth=1.4, marker="P", zorder=6)
            ax.text(lx + 12, ly - 5, name, fontsize=7, color="#5b2c6f",
                    fontweight="bold", zorder=8)

    if not segs:
        ax.text(0.5, 0.5, "NEATINS", transform=ax.transAxes,
                ha="center", va="center", fontsize=16, color="#bbb",
                style="italic", fontweight="bold")
        ax.set_title(f"{ROOM_SHORT[scene]}\n(neatins)", fontsize=10, pad=6)
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
        ax.scatter(xs, ys, c=ts, cmap=cmap, s=16, zorder=3,
                   edgecolors="none", vmin=0, vmax=1)
        idx_counter += seg_n

    lm = ROOM_LANDMARKS.get(scene, {})
    sp = lm.get("spawn")
    if sp:
        ax.scatter(sp[0], sp[1], s=200, color="#2ecc71",
                   edgecolor="black", linewidth=1.6, marker="s", zorder=7)
    door_in = lm.get("door_in")
    if door_in:
        ax.scatter(door_in[0], door_in[1], s=200, color="#3498db",
                   edgecolor="black", linewidth=1.6, marker="^", zorder=7)
    door_out = lm.get("door_out")
    if door_out:
        ax.scatter(door_out[0], door_out[1], s=300, color="#e74c3c",
                   edgecolor="black", linewidth=1.6, marker="*", zorder=7)

    idx = CANONICAL.index(scene) if scene in CANONICAL else -1
    exit_pt_raw = None; exit_pt_snap = None; exit_label = ""
    if idx >= 0 and idx + 1 < len(CANONICAL):
        next_scene = CANONICAL[idx + 1]
        exit_pt_raw = find_last_exit_position(all_positions, scene, next_scene)
        if exit_pt_raw is not None:
            do = lm.get("door_out")
            if do is not None:
                exit_pt_snap = (do[0], do[1])
                exit_label = "iesire spre urm."
            else:
                exit_pt_snap = exit_pt_raw
                exit_label = "ultima poz pre-iesire"
    if exit_pt_snap is None:
        fp = find_final_position_in_scene(all_positions, scene)
        if fp is not None:
            exit_pt_snap = fp; exit_pt_raw = fp
            exit_label = "poz finala (oprit aici)"

    if exit_pt_snap is not None:
        if exit_pt_raw is not None and exit_pt_raw != exit_pt_snap:
            ax.plot([exit_pt_raw[0], exit_pt_snap[0]],
                    [exit_pt_raw[1], exit_pt_snap[1]],
                    color="#aaa", linestyle=":", linewidth=1.2, zorder=4)
        ax.scatter(exit_pt_snap[0], exit_pt_snap[1], s=180, color="#ffd633",
                   edgecolor="black", linewidth=1.4, marker="o", zorder=8)
        ax.annotate(exit_label, xy=exit_pt_snap,
                    xytext=(8, 8), textcoords="offset points", fontsize=7,
                    color="#9a7800",
                    bbox=dict(boxstyle="round,pad=0.2", fc="#fffde0",
                              ec="#c0a020", lw=0.7), zorder=9)

    ax.set_title(f"{ROOM_SHORT[scene]}\n{pts_in_room} poz.",
                 fontsize=10, pad=6, fontweight="bold")


def plot_episode(ep, positions, out_dir):
    # Folosim ordinea CANONICA a jocului, nu ordinea de prima vizitare
    # (asa charts citesc left-to-right ca path-ul real al jocului)
    visited_scenes = set(s for _, _, s in positions if s in CANONICAL)
    visited_order = [s for s in CANONICAL if s in visited_scenes]
    if not visited_order:
        print(f"ep {ep}: no canonical scenes visited")
        return

    n_cols = len(visited_order)
    fig, axes = plt.subplots(nrows=1, ncols=n_cols, figsize=(5.5 * n_cols, 7.0))
    if n_cols == 1: axes = [axes]
    fig.patch.set_facecolor("white")

    path_str = " -> ".join(ROOM_SHORT[s].split(" — ")[0] for s in visited_order)
    fig.suptitle(
        f"Traseu agent — Episode {ep} (Run 5l_v8e, post lever-door fix)\n"
        f"Path: {path_str}",
        fontsize=12, fontweight="bold", y=0.99,
    )

    for ax, scene in zip(axes, visited_order):
        plot_room(ax, scene, positions, positions)

    legend_elements = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#2ecc71",
               markeredgecolor="black", markersize=10, label="Spawn"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#3498db",
               markeredgecolor="black", markersize=10, label="Door IN"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#e74c3c",
               markeredgecolor="black", markersize=14, label="Door OUT"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#ffd633",
               markeredgecolor="black", markersize=10, label="Iesire reala"),
        Line2D([0], [0], marker="P", color="w", markerfacecolor="#9b59b6",
               markeredgecolor="black", markersize=10, label="Lever (A2/02)"),
        Line2D([0], [0], color="#f4c430", linestyle="--", linewidth=2,
               label="Trigger (A1/03)"),
        Line2D([0], [0], color="#ff9966", linestyle=":", linewidth=1.5,
               label="Waypoint reward"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=7,
               fontsize=9, frameon=False, bbox_to_anchor=(0.5, 0.0))

    plt.tight_layout(rect=[0, 0.04, 1, 0.94])
    out = os.path.join(out_dir, f"traseu_ep{ep}_run5l_v8e_D01.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"[saved] {out}")


if __name__ == "__main__":
    ep_target = int(sys.argv[1]) if len(sys.argv) > 1 else EP
    pos = load_positions_for_ep(POS_FILE, ep_target)
    print(f"ep {ep_target}: {len(pos)} pozitii incarcate")
    plot_episode(ep_target, pos, OUT_DIR)
