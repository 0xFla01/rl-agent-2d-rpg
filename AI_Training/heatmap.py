"""
Genereaza heatmap-uri per scena din positions.jsonl.
Rulare: python heatmap.py
Output: results/heatmap_<scene>.png
"""

import json
import os
from collections import defaultdict
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np

POSITIONS_FILE = "positions.jsonl"
OUT_DIR = "results_v4"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M")
os.makedirs(OUT_DIR, exist_ok=True)

SCENE_NAMES = {
    "res://Levels/Area01/02.tscn":      "Area01_02_NPC",
    "res://Levels/Area01/01.tscn":      "Area01_01_Goblins",
    "res://Levels/Area01/03.tscn":      "Area01_03",
    "res://Levels/Area02/01.tscn":      "Area02_01",
    "res://Levels/Area01/02_shop.tscn": "Area01_02_Shop",
    "res://Levels/Area02/02.tscn":      "Area02_02_Levers",
    "res://Levels/Area01/04.tscn":      "Area01_04_Dungeon_Entry",
    "res://Levels/Dungeon01/01.tscn":   "Dungeon01_01_Statue",
    "res://Levels/Dungeon01/02.tscn":   "Dungeon01_02_Hub",
    "res://Levels/Dungeon01/03.tscn":   "Dungeon01_03_Waves",
    "res://Levels/Dungeon01/04.tscn":   "Dungeon01_04_Boss",
}

# Bounds REALE ale camerelor (x_min, x_max, y_min, y_max) — pentru a vizualiza zonele NEEXPLORATE
# Daca o scena nu e aici, foloseste min/max real al pozitiilor
SCENE_BOUNDS = {
    "res://Levels/Area01/02.tscn":    (-50, 500, -100, 400),
    "res://Levels/Area01/01.tscn":    (50, 450, -50, 380),
    "res://Levels/Area01/03.tscn":    (-50, 650, -650, 380),   # camera mare — chests la y=-550, exit sud y=312
    "res://Levels/Area02/01.tscn":    (-50, 700, -400, 1100),  # camera cu 3 waves + bridge
    "res://Levels/Area02/02.tscn":    (-50, 700, -50, 700),
    "res://Levels/Area01/04.tscn":    (-50, 500, -50, 500),
    "res://Levels/Dungeon01/01.tscn": (-50, 500, -50, 500),
    "res://Levels/Dungeon01/02.tscn": (-50, 700, -100, 700),
    "res://Levels/Dungeon01/03.tscn": (-50, 700, -50, 700),
    "res://Levels/Dungeon01/04.tscn": (-50, 700, -50, 700),
}

# Scene excluse din analiza (date din teste manuale, nu AI training)
EXCLUDED_SCENES = {
    "res://Levels/Dungeon01/02.tscn",
    "res://Levels/Dungeon01/03.tscn",
}

def load_positions(path):
    by_scene = defaultdict(list)
    total = 0
    skipped = 0
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                scene = d.get("scene", "")
                if scene in EXCLUDED_SCENES:
                    skipped += 1
                    continue
                x = d.get("x", 0)
                y = d.get("y", 0)
                by_scene[scene].append((x, y))
                total += 1
            except Exception:
                continue
    print(f"Incarcat {total} pozitii din {len(by_scene)} scene. ({skipped} excluse - teste manuale)")
    return by_scene

def make_heatmap(scene, positions, out_dir):
    if len(positions) < 10:
        return
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]

    # Foloseste bounds REALE ale camerei daca sunt definite (arata zonele neexplorate)
    if scene in SCENE_BOUNDS:
        x_min, x_max, y_min, y_max = SCENE_BOUNDS[scene]
    else:
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        margin = 50
        x_min -= margin; x_max += margin
        y_min -= margin; y_max += margin

    bins = 60
    h, xedges, yedges = np.histogram2d(xs, ys, bins=bins,
                                        range=[[x_min, x_max], [y_min, y_max]])

    fig, ax = plt.subplots(figsize=(8, 6))
    # transpunem si inversam Y (Godot: y creste in jos)
    img = ax.imshow(
        h.T,
        origin="upper",
        extent=[x_min, x_max, y_max, y_min],
        aspect="auto",
        cmap="hot",
        interpolation="bilinear",
    )
    plt.colorbar(img, ax=ax, label="Vizite")
    scene_label = SCENE_NAMES.get(scene, scene.split("/")[-1].replace(".tscn", ""))
    ax.set_title(f"Heatmap pozitii — {scene_label}\n({len(positions)} sample-uri)")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    plt.tight_layout()

    fname = os.path.join(out_dir, f"heatmap_{scene_label}_{TIMESTAMP}.png")
    plt.savefig(fname, dpi=120)
    plt.close()
    print(f"  Salvat: {fname}")

def main():
    if not os.path.exists(POSITIONS_FILE):
        print(f"Fisierul {POSITIONS_FILE} nu exista inca.")
        print("Lasa AI-ul sa ruleze cateva episoade si ruleaza din nou.")
        return

    by_scene = load_positions(POSITIONS_FILE)
    for scene, positions in sorted(by_scene.items(), key=lambda x: -len(x[1])):
        label = SCENE_NAMES.get(scene, scene)
        print(f"  {label}: {len(positions)} pozitii")
        make_heatmap(scene, positions, OUT_DIR)

    print(f"\nGata. Heatmap-urile sunt in: {OUT_DIR}/")

if __name__ == "__main__":
    main()
