"""
Top 3 runuri Run 5f — un fisier per episod, stil 'traseu_ep221' imbunatatit.
Pentru fiecare episod: o subfigura per camera vizitata (cap-coada in ordine reala).
Markerii sunt PE USILE REALE din scena (PlayerSpawn + LevelTransition), nu pe pozitia
agentului. Legenda mare, lizibila.
Rulare:  python top_runs_chart.py
Output:  results_v4/traseu_ep<N>_run5f.png  (cate unul per episod)
"""

import json
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

POS_FILE = "positions_run5f.jsonl"
OUT_DIR = "results_v4"
os.makedirs(OUT_DIR, exist_ok=True)

# Top 3 START din A1/02 cu path canonic complet 4 camere, dupa adincime in A2/01
SELECTED = [185, 764, 161]
EP_DEPTH = {185: 791, 764: 676, 161: 565}

ROOM_BOUNDS = {
    "res://Levels/Area01/02.tscn":  (-50, 500,  -150, 400),
    "res://Levels/Area01/01.tscn":  (  0, 480,   -80, 380),
    "res://Levels/Area01/03.tscn":  (-50, 650,  -650, 380),
    "res://Levels/Area02/01.tscn":  (-100, 700, -100, 1150),
}
ROOM_SHORT = {
    "res://Levels/Area01/02.tscn":  "Area01/02 — Start (NPC)",
    "res://Levels/Area01/01.tscn":  "Area01/01 — Combat Goblini",
    "res://Levels/Area01/03.tscn":  "Area01/03 — Buff Room",
    "res://Levels/Area02/01.tscn":  "Area02/01 — Waves + Pod",
}

# Landmarks per camera — coordonate REALE din .tscn (PlayerSpawn + LevelTransition)
# Format: dict cu 'spawn' (x,y), 'door_in' (x,y, eticheta), 'door_out' (x,y, eticheta)
ROOM_LANDMARKS = {
    "res://Levels/Area01/02.tscn": {
        "spawn":    (244, 152),
        "door_in":  None,  # camera de start — nu exista o usa "anterioara"
        "door_out": (224, -55, "Usa nord → A1/01"),
    },
    "res://Levels/Area01/01.tscn": {
        "spawn":    (209, 317),
        "door_in":  (240, 320, "Usa sud ← A1/02"),
        "door_out": (240, -32, "Usa nord → A1/03"),
    },
    "res://Levels/Area01/03.tscn": {
        "spawn":    (266, 301),
        "door_in":  (272, 320, "Usa sud ← A1/01"),
        "door_out": (587, -594, "Usa NE → A2/01"),
    },
    "res://Levels/Area02/01.tscn": {
        "spawn":    (-33, 70),
        "door_in":  (-51, 63, "Usa vest ← A1/03"),
        "door_out": (416, 1105, "Usa sud → A2/02"),
    },
}

# Trigger + waypoints (din global_ai_state_exporter.gd)
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

EP_NAME = {185: "albastru", 687: "verde", 337: "rosu"}


def load_positions(path):
    by_ep = defaultdict(list)
    with open(path, "r") as f:
        for line in f:
            try:
                d = json.loads(line)
                ep = d.get("episode")
                if ep is None:
                    continue
                by_ep[ep].append((d["x"], d["y"], d["scene"]))
            except Exception:
                continue
    return by_ep


def visited_in_order(positions):
    out, seen = [], set()
    for x, y, s in positions:
        if s and s not in seen:
            out.append(s)
            seen.add(s)
    return out


def segments_for_scene(positions, target_scene):
    segs, cur = [], []
    for x, y, s in positions:
        if s == target_scene:
            cur.append((x, y))
        else:
            if cur:
                segs.append(cur)
                cur = []
    if cur:
        segs.append(cur)
    return segs


def find_last_exit_position(positions, from_scene, to_scene):
    """Returneaza ultima pozitie in from_scene chiar inainte de o tranzitie la to_scene.
    Daca nu exista o astfel de tranzitie, returneaza None."""
    last_idx = None
    for i in range(len(positions) - 1):
        if positions[i][2] == from_scene and positions[i + 1][2] == to_scene:
            last_idx = i
    if last_idx is None:
        return None
    return positions[last_idx][0], positions[last_idx][1]


def find_final_position_in_scene(positions, scene):
    """Ultima pozitie a agentului in scena (pentru camera finala — unde a murit/terminat)."""
    for i in range(len(positions) - 1, -1, -1):
        if positions[i][2] == scene:
            return positions[i][0], positions[i][1]
    return None


CANONICAL = [
    "res://Levels/Area01/02.tscn",
    "res://Levels/Area01/01.tscn",
    "res://Levels/Area01/03.tscn",
    "res://Levels/Area02/01.tscn",
]


def plot_room(ax, scene, positions, all_positions):
    ax.set_facecolor("white")
    bx0, bx1, by0, by1 = ROOM_BOUNDS[scene]
    ax.set_xlim(bx0, bx1)
    ax.set_ylim(by1, by0)  # y inversat (jos = sud, ca in joc)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, color="#e6e6e6", linewidth=0.6, zorder=0)
    ax.set_xlabel("X", fontsize=10)
    ax.set_ylabel("Y (jos = sud)", fontsize=10)
    ax.tick_params(labelsize=9)

    segs = segments_for_scene(positions, scene)
    pts_in_room = sum(len(s) for s in segs)

    # Trigger + waypoints (orizontale)
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
        ax.text(0.5, 0.5, "NEATINS",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=18, color="#bbb", style="italic", fontweight="bold")
        ax.set_title(f"{ROOM_SHORT[scene]}\n(neatins in ep)", fontsize=12, pad=8)
        return

    # Traiectorie cu gradient timp pe puncte
    all_pts = [p for seg in segs for p in seg]
    n = len(all_pts)
    cmap = plt.cm.plasma

    idx_counter = 0
    for seg in segs:
        xs = [p[0] for p in seg]
        ys = [p[1] for p in seg]
        ax.plot(xs, ys, color="#3fd0d4", linewidth=1.4, alpha=0.65, zorder=2)
        seg_n = len(seg)
        ts = [(idx_counter + i) / max(n - 1, 1) for i in range(seg_n)]
        ax.scatter(xs, ys, c=ts, cmap=cmap, s=18, zorder=3,
                   edgecolors="none", vmin=0, vmax=1)
        idx_counter += seg_n

    # Landmarks fixe ale camerei (USI REALE din .tscn)
    lm = ROOM_LANDMARKS.get(scene, {})

    sp = lm.get("spawn")
    if sp:
        ax.scatter(sp[0], sp[1], s=240, color="#2ecc71", edgecolor="black",
                   linewidth=1.8, marker="s", zorder=7)

    door_in = lm.get("door_in")
    if door_in:
        ax.scatter(door_in[0], door_in[1], s=260, color="#3498db", edgecolor="black",
                   linewidth=1.8, marker="^", zorder=7)

    door_out = lm.get("door_out")
    if door_out:
        ax.scatter(door_out[0], door_out[1], s=360, color="#e74c3c", edgecolor="black",
                   linewidth=1.8, marker="*", zorder=7)

    # Marker "ieșire reala": snapped la usa de iesire daca agentul a tranzitat la camera
    # urmatoare canonica. Linie punctata subtire arata extrapolarea de la ultima poz la usa.
    idx = CANONICAL.index(scene) if scene in CANONICAL else -1
    exit_pt_raw = None
    exit_pt_snap = None
    exit_label = ""
    if idx >= 0 and idx + 1 < len(CANONICAL):
        next_scene = CANONICAL[idx + 1]
        exit_pt_raw = find_last_exit_position(all_positions, scene, next_scene)
        if exit_pt_raw is not None:
            door_out = ROOM_LANDMARKS.get(scene, {}).get("door_out")
            if door_out is not None:
                exit_pt_snap = (door_out[0], door_out[1])
                exit_label = "iesire spre cam. urm."
            else:
                exit_pt_snap = exit_pt_raw
                exit_label = "ultima poz inainte de iesire"
    if exit_pt_snap is None:
        # Nu a iesit catre camera urmatoare → poz finala a episodului in camera
        fp = find_final_position_in_scene(all_positions, scene)
        if fp is not None:
            exit_pt_snap = fp
            exit_pt_raw = fp
            exit_label = "poz finala (nu a iesit spre urm.)"

    if exit_pt_snap is not None:
        if exit_pt_raw is not None and exit_pt_raw != exit_pt_snap:
            # Linie punctata de la ultima pozitie inregistrata la usa (extrapolare)
            ax.plot([exit_pt_raw[0], exit_pt_snap[0]],
                    [exit_pt_raw[1], exit_pt_snap[1]],
                    color="#aaa", linestyle=":", linewidth=1.2, zorder=4)
        ax.scatter(exit_pt_snap[0], exit_pt_snap[1], s=220, color="#ffd633",
                   edgecolor="black", linewidth=1.6, marker="o", zorder=8)
        ax.annotate(exit_label, xy=exit_pt_snap,
                    xytext=(10, 10), textcoords="offset points",
                    fontsize=8, color="#9a7800",
                    bbox=dict(boxstyle="round,pad=0.25", fc="#fffde0", ec="#c0a020", lw=0.8),
                    zorder=9)

    ax.set_title(f"{ROOM_SHORT[scene]}\n{pts_in_room} pozitii in camera",
                 fontsize=12, pad=8, fontweight="bold")


def plot_episode(ep, positions, out_dir):
    vio = visited_in_order(positions)
    canonical = [
        "res://Levels/Area01/02.tscn",
        "res://Levels/Area01/01.tscn",
        "res://Levels/Area01/03.tscn",
        "res://Levels/Area02/01.tscn",
    ]
    rooms = [s for s in vio if s in canonical]
    if not rooms:
        return

    n_cols = len(rooms)
    fig, axes = plt.subplots(
        nrows=1, ncols=n_cols,
        figsize=(7.0 * n_cols, 8.5),
    )
    if n_cols == 1:
        axes = [axes]
    fig.patch.set_facecolor("white")

    fig.suptitle(
        f"Traseul agentului — Episode {ep} (Run 5f)\n"
        f"{len(positions)} pozitii totale  |  ordinea camerelor: "
        + " → ".join([ROOM_SHORT[s].split(' — ')[0] for s in rooms]),
        fontsize=15, fontweight="bold", y=1.005,
    )

    for i, scene in enumerate(rooms):
        plot_room(axes[i], scene, positions, positions)
        if i < n_cols - 1:
            axes[i].annotate(
                "",
                xy=(1.07, 0.5), xycoords=axes[i].transAxes,
                xytext=(1.02, 0.5),
                arrowprops=dict(arrowstyle="->", color="#555", lw=2.5),
            )

    # Legenda mare, separata pe doua randuri sub fig
    legend_markers = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#2ecc71",
               markeredgecolor="black", markersize=14, label="Spawn (din scena)"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#3498db",
               markeredgecolor="black", markersize=14, label="Usa intrare (camera anterioara)"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#e74c3c",
               markeredgecolor="black", markersize=18, label="Usa iesire (catre camera urmatoare)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#ffd633",
               markeredgecolor="black", markersize=12, label="Iesire reala (sau poz finala)"),
    ]
    legend_lines = [
        Line2D([0], [0], color="#3fd0d4", linewidth=2.5, label="Traiectorie (cyan)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#7e3a93",
               markeredgecolor="none", markersize=11, label="Puncte: mov → galben = timp"),
        Line2D([0], [0], color="#f4c430", linestyle="--", linewidth=2.5,
               label="Trigger line (reward majora)"),
        Line2D([0], [0], color="#ff9966", linestyle=":", linewidth=1.8,
               label="Waypoint (reward intermediar)"),
    ]
    leg1 = fig.legend(handles=legend_markers, loc="lower left",
                      bbox_to_anchor=(0.05, -0.02),
                      ncol=4, fontsize=11, frameon=True,
                      facecolor="#f8f8f8", edgecolor="#888",
                      title="Markeri", title_fontsize=11)
    leg1.get_title().set_fontweight("bold")
    leg2 = fig.legend(handles=legend_lines, loc="lower right",
                      bbox_to_anchor=(0.95, -0.02),
                      ncol=2, fontsize=11, frameon=True,
                      facecolor="#f8f8f8", edgecolor="#888",
                      title="Linii / coloraj", title_fontsize=11)
    leg2.get_title().set_fontweight("bold")
    fig.add_artist(leg1)

    out_path = os.path.join(out_dir, f"traseu_ep{ep}_run5f.png")
    plt.savefig(out_path, dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved: {out_path}  ({n_cols} camere)")


def main():
    by_ep = load_positions(POS_FILE)
    print(f"Loaded {len(by_ep)} episodes")
    for ep in SELECTED:
        if ep not in by_ep:
            print(f"  WARN ep {ep} not found")
            continue
        plot_episode(ep, by_ep[ep], OUT_DIR)


if __name__ == "__main__":
    main()
