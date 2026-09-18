"""Harta sintetica completa run 5j ep_count #439.
Toate camerele plasate spatial cu sageti directionale flow.
"""
import json
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D

POS_FILE = "positions_run5j_postshop.jsonl"
OUT_DIR  = "results_v4"

A102      = "res://Levels/Area01/02.tscn"
A101      = "res://Levels/Area01/01.tscn"
A103      = "res://Levels/Area01/03.tscn"
A201      = "res://Levels/Area02/01.tscn"
A102_SHOP = "res://Levels/Area01/02_shop.tscn"
A202      = "res://Levels/Area02/02.tscn"

# Layout pe canvas sintetic (x, y, width, height) — coords arbitrare in pixeli
# Aranjate aproximativ spatial conform path-ului in joc
ROOM_LAYOUT = {
    A103:      {"x":   0, "y":   0, "w": 320, "h": 280, "color": "#9b59b6", "label": "A1/03\nBuff Room"},
    A101:      {"x":   0, "y": 360, "w": 320, "h": 200, "color": "#e67e22", "label": "A1/01\nCombat Goblini"},
    A102:      {"x":   0, "y": 640, "w": 320, "h": 200, "color": "#3498db", "label": "A1/02\nStart (NPC)"},
    A201:      {"x": 420, "y":   0, "w": 280, "h": 600, "color": "#e74c3c", "label": "A2/01\nWaves + Pod"},
    A102_SHOP: {"x": 770, "y": 100, "w": 230, "h": 180, "color": "#f1c40f", "label": "A1/02_shop\nShopkeeper"},
    A202:      {"x": 770, "y": 360, "w": 230, "h": 240, "color": "#1abc9c", "label": "A2/02\nLever ★"},
}

# Path flow secventa (de la → la, label) — fara step 8 BLOCKED
PATH_FLOW = [
    (A102, A101, "1"),
    (A101, A103, "2"),
    (A103, A201, "3"),
    (A201, A102_SHOP, "4"),
    (A102_SHOP, A201, "5"),    # re-entry shop
    (A201, A102_SHOP, "6"),
    (A102_SHOP, A202, "7"),
]

# Door positions per scene (pe canvas global, calculat aproximativ)
DOOR_POSITIONS = {
    (A102, "out"):       (160, 600),   # A1/02 north → A1/01
    (A101, "in_south"):  (160, 570),   # A1/01 south (from A1/02)
    (A101, "out_north"): (160, 350),   # A1/01 north → A1/03
    (A103, "in_south"):  (160, 320),   # A1/03 south (from A1/01)
    (A103, "out_ne"):    (320, 50),    # A1/03 NE → A2/01
    (A201, "in_west"):   (400, 100),   # A2/01 west (from A1/03)
    (A201, "out_south"): (540, 700),   # A2/01 south
    (A201, "to_shop"):   (680, 200),   # A2/01 → shop east
    (A102_SHOP, "in_west"): (730, 250),
    (A102_SHOP, "in_top"):  (820, 200),  # from A2/01
    (A102_SHOP, "out_bottom"): (820, 400), # to A2/02
    (A202, "in_top"):    (820, 450),
}


def load_positions(path):
    by_ep = defaultdict(list)
    with open(path, "r") as f:
        for line in f:
            try:
                d = json.loads(line)
                ep = d.get("episode")
                if ep is None: continue
                by_ep[ep].append((d["x"], d["y"], d["scene"]))
            except: continue
    return by_ep


def scene_to_canvas(scene, local_x, local_y, scene_extent):
    """Map local (x, y) within scene to canvas coords."""
    layout = ROOM_LAYOUT[scene]
    bx0, bx1, by0, by1 = scene_extent
    # Normalize local coords
    nx = (local_x - bx0) / max(bx1 - bx0, 1)
    ny = (local_y - by0) / max(by1 - by0, 1)
    cx = layout["x"] + nx * layout["w"]
    cy = layout["y"] + ny * layout["h"]
    return cx, cy


SCENE_EXTENTS = {
    A102:      (-50, 500, -150, 400),
    A101:      (  0, 480,  -80, 380),
    A103:      (-50, 650, -650, 380),
    A201:      (-100, 700, -100, 1150),
    A102_SHOP: ( 60, 400,   20, 280),
    A202:      (-100, 700,  -50, 600),
}


def get_proxy_positions_from_other_ep(by_ep, scene):
    """Caut PRIMUL ep cu A1/02 SI A1/01 in path (consistenta cu traseu_ep17 cap-coada)."""
    # Aceeasi logica ca find_proxy_positions din generate_5j_shop_chart.py
    for ep in sorted(by_ep.keys()):
        pos = by_ep[ep]
        scenes_seq = []
        for x, y, s in pos:
            if not scenes_seq or scenes_seq[-1] != s:
                scenes_seq.append(s)
        if A102 in scenes_seq and A101 in scenes_seq:
            scene_pos = [(x, y, scene) for x, y, s in pos if s == scene]
            if scene_pos:
                return scene_pos
    return []


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    by_ep = load_positions(POS_FILE)
    if 17 not in by_ep:
        print("ep#17 not found"); return
    # Proxy positions REALE din alt ep care a vizitat A1/02 si A1/01
    proxy_a102 = get_proxy_positions_from_other_ep(by_ep, A102)
    proxy_a101 = get_proxy_positions_from_other_ep(by_ep, A101)
    print(f"  proxy A1/02: {len(proxy_a102)} pozitii")
    print(f"  proxy A1/01: {len(proxy_a101)} pozitii")
    positions = proxy_a102 + proxy_a101 + by_ep[17]

    fig, ax = plt.subplots(figsize=(16, 11))
    ax.set_facecolor("#1a1a1a")
    fig.patch.set_facecolor("white")

    # Draw room rectangles + label SUS (default) sau JOS (A1/01, A1/02, A2/02 — unde se suprapun cu sageti)
    LABEL_BELOW = {A101, A102, A202}  # label JOS sub caseta pentru aceste camere
    for scene, layout in ROOM_LAYOUT.items():
        rect = Rectangle(
            (layout["x"], layout["y"]), layout["w"], layout["h"],
            linewidth=2.5, edgecolor=layout["color"],
            facecolor=layout["color"], alpha=0.12, zorder=1,
        )
        ax.add_patch(rect)
        if scene in LABEL_BELOW:
            # Label JOS sub caseta (offset +18 sub bottom)
            ax.text(
                layout["x"] + layout["w"]/2, layout["y"] + layout["h"] + 18,
                layout["label"], ha="center", va="top",
                fontsize=10, fontweight="bold", color="white", zorder=5,
                bbox=dict(boxstyle="round,pad=0.3", fc=layout["color"], ec="white", lw=1.2, alpha=0.95)
            )
        else:
            # Label SUS in afara casetei (offset -38 deasupra)
            ax.text(
                layout["x"] + layout["w"]/2, layout["y"] - 38,
                layout["label"], ha="center", va="bottom",
                fontsize=10, fontweight="bold", color="white", zorder=5,
                bbox=dict(boxstyle="round,pad=0.3", fc=layout["color"], ec="white", lw=1.2, alpha=0.95)
            )

    # Plot positions transformed to canvas coords
    canvas_pts = []
    for x, y, s in positions:
        if s in SCENE_EXTENTS:
            cx, cy = scene_to_canvas(s, x, y, SCENE_EXTENTS[s])
            canvas_pts.append((cx, cy, s))

    if canvas_pts:
        # Color gradient by time
        n = len(canvas_pts)
        xs = [p[0] for p in canvas_pts]
        ys = [p[1] for p in canvas_pts]
        ts = [i/max(n-1, 1) for i in range(n)]
        ax.scatter(xs, ys, c=ts, cmap=plt.cm.plasma, s=14, zorder=4, alpha=0.85, edgecolors="none")
        # Trajectory line
        ax.plot(xs, ys, color="#3fd0d4", linewidth=0.8, alpha=0.4, zorder=3)

    # Path flow arrows SCOSE complet (user: se vede din pozitii si fara sageti)

    # Title + annotations
    ax.set_xlim(-60, 1050)
    ax.set_ylim(900, -90)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values(): spine.set_visible(False)

    fig.suptitle(
        "Harta completa run 5j ep_count #439 — TOATA harta parcursa",
        fontsize=18, fontweight="bold", y=0.96,
    )

    # Subtitle SCOS (user a cerut sa il elimin)

    # Legend
    legend_items = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#7e3a93",
               markeredgecolor="none", markersize=10, label="Pozitii (mov→galben = progres timp)"),
        Line2D([0], [0], color="#3fd0d4", linewidth=2, label="Traiectorie"),
    ]
    fig.legend(handles=legend_items, loc="lower center", bbox_to_anchor=(0.5, -0.01),
               ncol=2, fontsize=11, facecolor="#f8f8f8", edgecolor="#888", framealpha=0.95)

    out_path = os.path.join(OUT_DIR, "harta_completa_ep17_run5j.png")
    plt.savefig(out_path, dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
