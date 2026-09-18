"""Harta sintetica a jocului — dimensiuni proportionale cu sceneele reale.
Layout-ul user:
  Sus orizontal: A1/02 — A1/01 — A1/03 — A2/01
  De la A2/01 in jos: SHOP, A2/02, A1/04
  De la A1/04 dreapta: D01/01 - D01/02 — D01/03 (bidirectional D01/02↔D01/03)
  Boss (D01/04): sus de D01/02
"""
import os
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

OUT_DIR = "results_v4"
os.makedirs(OUT_DIR, exist_ok=True)


# ============ ROOM BOUNDS REALE (din scene .tscn / ROOM_BOUNDS top_runs_chart) ============
# Format: (w_units, h_units) — dimensiuni reale ale camerei in joc
REAL_DIMS = {
    "A1/02":  (550, 550),
    "A1/01":  (480, 460),
    "A1/03":  (700, 1030),   # alungit vertical (north chest area)
    "A2/01":  (800, 1250),   # foarte alungit vertical (pod)
    "SHOP":   (340, 260),    # mic
    "A2/02":  (800, 650),
    "A1/04":  (480, 460),    # estimat similar A1/01
    "D01/01": (480, 460),    # estimat
    "D01/02": (550, 450),    # estimat (hub)
    "D01/03": (650, 500),    # estimat (wave manager)
    "D01/04": (700, 600),    # boss room mai mare
}

# Scale: 1 game unit = X canvas units
SCALE = 0.18
def s(v): return v * SCALE


# ============ LAYOUT POSITIONS — respecta directiile din joc ============
# Sus in joc = sus pe canvas (y mic). Convention canvas: y mic = sus.
#  Vertical: A1/02 (jos) ↑ A1/01 ↑ A1/03 (sus)
#  Lateral: A1/03 → DREAPTA → A2/01
#  Vertical jos de A2/01: SHOP ↓ A2/02
#  Lateral A2/02 → DREAPTA → A1/04
#  Vertical: A1/04 ↑ D01/01 ↑ D01/02 ↑ BOSS (D01/04)
#  Lateral: D01/02 → DREAPTA → D01/03 (bidir)

GAP = 70  # spacing standard
ROOM_X = {}; ROOM_Y = {}

# Coloana 1 (Area 01 stanga): A1/02 jos → A1/01 mijloc → A1/03 sus
col1_x = 0
# A1/03 e foarte alungit (1030) — center-l deasupra de A1/01
ROOM_X["A1/03"] = col1_x + s(REAL_DIMS["A1/03"][0])/2
ROOM_X["A1/01"] = col1_x + s(REAL_DIMS["A1/03"][0])/2  # aliniat cu A1/03 centru
ROOM_X["A1/02"] = col1_x + s(REAL_DIMS["A1/03"][0])/2

# A1/03 sus (y mic) — vom alinia centrul cu A2/01 pentru sageata orizontala perfecta
A103_TOP_Y = 0
ROOM_Y["A1/03"] = A103_TOP_Y + s(REAL_DIMS["A2/01"][1])/2  # centrul lui A2/01 ca anchor
# A1/01 sub A1/03
A103_BOTTOM = ROOM_Y["A1/03"] + s(REAL_DIMS["A1/03"][1])/2
ROOM_Y["A1/01"] = A103_BOTTOM + GAP + s(REAL_DIMS["A1/01"][1])/2
# A1/02 sub A1/01
A101_BOTTOM = ROOM_Y["A1/01"] + s(REAL_DIMS["A1/01"][1])/2
ROOM_Y["A1/02"] = A101_BOTTOM + GAP + s(REAL_DIMS["A1/02"][1])/2

# Coloana 2 (Area 02 mijloc): A2/01 langa A1/03 (dreapta) → SHOP jos → A2/02 jos
col2_x = ROOM_X["A1/03"] + s(REAL_DIMS["A1/03"][0])/2 + GAP + s(REAL_DIMS["A2/01"][0])/2
ROOM_X["A2/01"] = col2_x
ROOM_X["SHOP"]  = col2_x
ROOM_X["A2/02"] = col2_x

# A2/01 aliniat cu A1/03 la nord (top alignment)
ROOM_Y["A2/01"] = A103_TOP_Y + s(REAL_DIMS["A2/01"][1])/2
A201_BOTTOM = ROOM_Y["A2/01"] + s(REAL_DIMS["A2/01"][1])/2
# SHOP sub A2/01
ROOM_Y["SHOP"] = A201_BOTTOM + GAP + s(REAL_DIMS["SHOP"][1])/2
SHOP_BOTTOM = ROOM_Y["SHOP"] + s(REAL_DIMS["SHOP"][1])/2
# A2/02 sub SHOP
ROOM_Y["A2/02"] = SHOP_BOTTOM + GAP + s(REAL_DIMS["A2/02"][1])/2

# Coloana 3 (Dungeon dreapta): A1/04 jos, BOSS sus
col3_x = ROOM_X["A2/02"] + s(REAL_DIMS["A2/02"][0])/2 + GAP + s(REAL_DIMS["A1/04"][0])/2
ROOM_X["A1/04"]  = col3_x
ROOM_X["D01/01"] = col3_x
ROOM_X["D01/02"] = col3_x
ROOM_X["D01/04"] = col3_x

# A1/04 aliniat la CENTRU cu A2/02 (acelasi cy) — pentru sageata orizontala perfecta
ROOM_Y["A1/04"] = ROOM_Y["A2/02"]
# D01/01 sus de A1/04
A104_TOP = ROOM_Y["A1/04"] - s(REAL_DIMS["A1/04"][1])/2
ROOM_Y["D01/01"] = A104_TOP - GAP - s(REAL_DIMS["D01/01"][1])/2
# D01/02 sus de D01/01
D101_TOP = ROOM_Y["D01/01"] - s(REAL_DIMS["D01/01"][1])/2
ROOM_Y["D01/02"] = D101_TOP - GAP - s(REAL_DIMS["D01/02"][1])/2
# BOSS sus de D01/02
D102_TOP = ROOM_Y["D01/02"] - s(REAL_DIMS["D01/02"][1])/2
ROOM_Y["D01/04"] = D102_TOP - GAP - s(REAL_DIMS["D01/04"][1])/2

# D01/03 in DREAPTA de D01/02 (aliniat cu D01/02 vertical)
col4_x = ROOM_X["D01/02"] + s(REAL_DIMS["D01/02"][0])/2 + GAP + s(REAL_DIMS["D01/03"][0])/2
ROOM_X["D01/03"] = col4_x
ROOM_Y["D01/03"] = ROOM_Y["D01/02"]


# ============ DATA STRUCTURE ============
ROOMS = {
    "A1/02":  {"c": "#3498db", "area": "A01", "title": "Start Room",     "sub": "NPC + quest"},
    "A1/01":  {"c": "#e67e22", "area": "A01", "title": "Combat Room",    "sub": "goblini"},
    "A1/03":  {"c": "#9b59b6", "area": "A01", "title": "Buff Room",      "sub": "chest + reward"},
    "A2/01":  {"c": "#e74c3c", "area": "A02", "title": "Wave Room",      "sub": "pod + waves"},
    "SHOP":   {"c": "#f1c40f", "area": "A01", "title": "Shop",           "sub": "shopkeeper"},
    "A2/02":  {"c": "#1abc9c", "area": "A02", "title": "Lever Room",     "sub": "puzzle leveler"},
    "A1/04":  {"c": "#7f8c8d", "area": "A01", "title": "Dungeon Entry",  "sub": "key required"},
    "D01/01": {"c": "#34495e", "area": "D01", "title": "Dungeon 1",      "sub": "entrance"},
    "D01/02": {"c": "#2c3e50", "area": "D01", "title": "Dungeon 2",      "sub": "hub · locked door"},
    "D01/03": {"c": "#8e44ad", "area": "D01", "title": "Dungeon 3",      "sub": "wave manager · key"},
    "D01/04": {"c": "#c0392b", "area": "D01", "title": "Boss Room",      "sub": "Dark Wizard ★"},
}

# Fill in pos/dims
for key, r in ROOMS.items():
    r["cx"] = ROOM_X[key]; r["cy"] = ROOM_Y[key]
    r["w"]  = s(REAL_DIMS[key][0]); r["h"] = s(REAL_DIMS[key][1])

CONNECTIONS = [
    ("A1/02", "A1/01"),    # sus
    ("A1/01", "A1/03"),    # sus
    ("A1/03", "A2/01"),    # dreapta
    ("A2/01", "SHOP"),     # jos
    ("SHOP", "A2/02"),     # jos
    ("A2/02", "A1/04"),    # dreapta (lateral A2/02 → A1/04)
    ("A1/04", "D01/01"),   # sus
    ("D01/01", "D01/02"),  # sus
    ("D01/02", "D01/04"),  # sus la boss
]

BIDIR_CONNECTIONS = [
    ("D01/02", "D01/03"),  # bidirectional — AI ia key in D01/03 si se intoarce la D01/02
]

AREAS = {
    "A01": {"label": "Area 01", "color": "#5dade2"},
    "A02": {"label": "Area 02", "color": "#e74c3c"},
    "D01": {"label": "Dungeon 01", "color": "#8e44ad"},
}


def draw_room(ax, key, r):
    cx, cy = r["cx"], r["cy"]
    w, h = r["w"], r["h"]
    # Shadow
    shadow = FancyBboxPatch(
        (cx - w/2 + 3, cy - h/2 + 3), w, h,
        boxstyle="round,pad=0.02,rounding_size=8",
        linewidth=0, facecolor="#000000", alpha=0.10, zorder=1,
    )
    ax.add_patch(shadow)
    # Main box
    bbox = FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle="round,pad=0.02,rounding_size=8",
        linewidth=2.8, edgecolor=r["c"],
        facecolor=r["c"], alpha=0.22, zorder=2,
    )
    ax.add_patch(bbox)
    # Boss Room: label DEASUPRA in afara casetei (sa nu fie peste stea)
    if key == "D01/04":
        ax.text(
            cx, cy - h/2 - 12,
            r["title"], ha="center", va="bottom",
            fontsize=13, fontweight="bold", color=r["c"],
            zorder=4,
        )
    else:
        # Restul: label IN INTERIOR caseta (centru)
        ax.text(
            cx, cy,
            r["title"], ha="center", va="center",
            fontsize=12, fontweight="bold", color="#222",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=r["c"], lw=1.6, alpha=0.95),
            zorder=4,
        )


def edge_points(rf, rt):
    """Punctele de iesire/intrare pe marginile casetelor."""
    fx, fy = rf["cx"], rf["cy"]
    tx, ty = rt["cx"], rt["cy"]
    dx, dy = tx - fx, ty - fy
    if abs(dx) > abs(dy):
        if dx > 0:
            return (fx + rf["w"]/2, fy), (tx - rt["w"]/2, ty)
        else:
            return (fx - rf["w"]/2, fy), (tx + rt["w"]/2, ty)
    else:
        if dy > 0:
            return (fx, fy + rf["h"]/2), (tx, ty - rt["h"]/2)
        else:
            return (fx, fy - rf["h"]/2), (tx, ty + rt["h"]/2)


def main():
    fig, ax = plt.subplots(figsize=(20, 14), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fafbfc")

    # FARA area backgrounds + FARA area labels (user a cerut sa le scot)
    # Rooms doar
    for key, r in ROOMS.items():
        draw_room(ax, key, r)

    # Straight connections
    for f, t in CONNECTIONS:
        rf, rt = ROOMS[f], ROOMS[t]
        (fx, fy), (tx, ty) = edge_points(rf, rt)
        arrow = FancyArrowPatch(
            (fx, fy), (tx, ty),
            arrowstyle="->", mutation_scale=22,
            color="#5d6d7e", linewidth=2.4, alpha=0.9, zorder=3,
        )
        ax.add_patch(arrow)

    # Bidirectional connections (D01/02 ↔ D01/03) — fara label, doua sageti paralele
    for f, t in BIDIR_CONNECTIONS:
        rf, rt = ROOMS[f], ROOMS[t]
        (fx, fy), (tx, ty) = edge_points(rf, rt)
        import math
        ang = math.atan2(ty - fy, tx - fx)
        perp = (-math.sin(ang) * 14, math.cos(ang) * 14)
        arrow1 = FancyArrowPatch(
            (fx + perp[0], fy + perp[1]),
            (tx + perp[0], ty + perp[1]),
            arrowstyle="->", mutation_scale=22,
            color="#16a085", linewidth=2.4, alpha=0.95, zorder=4,
        )
        arrow2 = FancyArrowPatch(
            (tx - perp[0], ty - perp[1]),
            (fx - perp[0], fy - perp[1]),
            arrowstyle="->", mutation_scale=22,
            color="#16a085", linewidth=2.4, alpha=0.95, zorder=4,
        )
        ax.add_patch(arrow1)
        ax.add_patch(arrow2)

    # Boss star — CENTRATA in camera boss
    boss = ROOMS["D01/04"]
    ax.scatter(boss["cx"], boss["cy"],
               s=900, marker="*", color="#f1c40f", edgecolor="#c0392b",
               linewidth=2.6, zorder=5)

    # Axis
    all_x_left = [r["cx"] - r["w"]/2 for r in ROOMS.values()]
    all_x_right = [r["cx"] + r["w"]/2 for r in ROOMS.values()]
    all_y_top = [r["cy"] - r["h"]/2 for r in ROOMS.values()]
    all_y_bot = [r["cy"] + r["h"]/2 for r in ROOMS.values()]
    pad = 80
    ax.set_xlim(min(all_x_left) - pad, max(all_x_right) + pad)
    ax.set_ylim(max(all_y_bot) + pad + 30, min(all_y_top) - pad - 50)  # invert y
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values(): spine.set_visible(False)

    fig.suptitle(
        "Harta jocului — camere si conexiuni (proportii reale)",
        fontsize=20, fontweight="bold", y=0.96,
    )

    legend_items = [
        Line2D([0], [0], color="#5d6d7e", linewidth=2.5,
               marker=">", markersize=10, label="Tranzitie unidirectionala"),
        Line2D([0], [0], color="#16a085", linewidth=2.5,
               marker=">", markersize=10, label="Tranzitie bidirectionala (cu return)"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#f1c40f",
               markeredgecolor="#c0392b", markersize=18, label="Boss final (Dark Wizard)"),
    ]
    fig.legend(handles=legend_items, loc="lower center", bbox_to_anchor=(0.5, 0.02),
               ncol=3, fontsize=12, facecolor="#f8f8f8", edgecolor="#bbb")

    out = os.path.join(OUT_DIR, "harta_joc_completa.png")
    plt.savefig(out, dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
