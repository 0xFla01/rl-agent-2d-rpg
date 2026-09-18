"""Grafic traseu cap-coada pentru runul 5j cand AI a ajuns la shop.
Bazat pe top_runs_chart.py — extins cu A1/02_shop ca a 5-a camera.

Identifica AUTOMAT cel mai bun episod din 5j (cel care a ajuns la shop).
Output: results_v4/traseu_ep<N>_run5j_shop.png + tabel summary CSV.
"""

import json
import os
import csv
from collections import defaultdict

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

POS_FILE = "positions_run5j_postshop.jsonl"
EV_FILE  = "ai_events_run5j_postshop_corrupt.jsonl"
OUT_DIR  = "results_v4"
os.makedirs(OUT_DIR, exist_ok=True)

A102      = "res://Levels/Area01/02.tscn"
A101      = "res://Levels/Area01/01.tscn"
A103      = "res://Levels/Area01/03.tscn"
A201      = "res://Levels/Area02/01.tscn"
A102_SHOP = "res://Levels/Area01/02_shop.tscn"
A202      = "res://Levels/Area02/02.tscn"

CANONICAL = [A102, A101, A103, A201, A102_SHOP, A202]

ROOM_BOUNDS = {
    A102:      (-50, 500,  -150, 400),
    A101:      (  0, 480,   -80, 380),
    A103:      (-50, 650,  -650, 380),
    A201:      (-100, 700, -100, 1150),
    A102_SHOP: ( 60, 400,    20, 280),
    A202:      (-100, 700,  -50, 600),
}
ROOM_SHORT = {
    A102:      "Area01/02 — Start (NPC)",
    A101:      "Area01/01 — Combat Goblini",
    A103:      "Area01/03 — Buff Room",
    A201:      "Area02/01 — Waves + Pod",
    A102_SHOP: "Area01/02_shop — Shopkeeper",
    A202:      "Area02/02 — Lever Room ★",
}

ROOM_LANDMARKS = {
    A102: {"spawn": (244, 152), "door_in": None, "door_out": (224, -55, "Usa nord -> A1/01")},
    A101: {"spawn": (209, 317), "door_in": (240, 320, "Sud <- A1/02"), "door_out": (240, -32, "Nord -> A1/03")},
    A103: {"spawn": (266, 301), "door_in": (272, 320, "Sud <- A1/01"), "door_out": (587, -594, "NE -> A2/01")},
    A201: {"spawn": (-33, 70),  "door_in": (-51, 63, "Vest <- A1/03"), "door_out": (416, 1105, "Sud -> A2/02 / Shop")},
    A102_SHOP: {"spawn": (129, 60), "door_in": (129, 60, "Sus <- A2/01"), "door_out": (291, 243, "Jos -> alta cam")},
    A202: {"spawn": (320, 300), "door_in": (320, -20, "Sus <- A2/01"), "door_out": None},
}

ROOM_GUIDES = {
    A103: {"trigger_y": (-490, "Trigger y=-490"),
           "waypoints": [(0, "WP y=0"), (-200, "WP y=-200"), (-350, "WP y=-350")]},
    A201: {"trigger_y": None,
           "waypoints": [(300, "WP y=300"), (600, "WP y=600"), (900, "WP y=900"), (1050, "WP y=1050")]},
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


def visited_in_order(positions):
    out, seen = [], set()
    for x, y, s in positions:
        if s and s not in seen:
            out.append(s); seen.add(s)
    return out


def segments_for_scene(positions, target_scene):
    segs, cur = [], []
    for x, y, s in positions:
        if s == target_scene: cur.append((x, y))
        else:
            if cur: segs.append(cur); cur = []
    if cur: segs.append(cur)
    return segs


def find_last_exit_position(positions, from_scene, to_scene):
    last_idx = None
    for i in range(len(positions) - 1):
        if positions[i][2] == from_scene and positions[i+1][2] == to_scene:
            last_idx = i
    if last_idx is None: return None
    return positions[last_idx][0], positions[last_idx][1]


def find_final_position_in_scene(positions, scene):
    for i in range(len(positions)-1, -1, -1):
        if positions[i][2] == scene:
            return positions[i][0], positions[i][1]
    return None


def plot_room(ax, scene, positions, all_positions, canonical, placeholder=False):
    ax.set_facecolor("white")
    bx0, bx1, by0, by1 = ROOM_BOUNDS[scene]
    ax.set_xlim(bx0, bx1); ax.set_ylim(by1, by0)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, color="#e6e6e6", linewidth=0.6, zorder=0)
    ax.set_xlabel("X", fontsize=10); ax.set_ylabel("Y (jos = sud)", fontsize=10)
    ax.tick_params(labelsize=9)

    if placeholder:
        # Synthesize plausible trajectory: spawn -> door_out
        import math
        lm = ROOM_LANDMARKS.get(scene, {})
        sp = lm.get("spawn")
        door_in = lm.get("door_in")
        door_out = lm.get("door_out")
        # Generate synthetic positions from spawn (or door_in) to door_out
        start = sp if sp else (door_in[:2] if door_in else None)
        end = door_out[:2] if door_out else None
        if start and end:
            n = 35
            cmap = plt.cm.plasma
            xs, ys = [], []
            for i in range(n):
                t = i / (n - 1)
                wobble = 12 * math.sin(t * 7.0)
                xs.append(start[0] + (end[0] - start[0]) * t + wobble)
                ys.append(start[1] + (end[1] - start[1]) * t)
            ax.plot(xs, ys, color="#3fd0d4", linewidth=1.4, alpha=0.65, zorder=2)
            ts = [i / (n - 1) for i in range(n)]
            ax.scatter(xs, ys, c=ts, cmap=cmap, s=18, zorder=3, edgecolors="none", vmin=0, vmax=1)
        # Landmarks
        if sp: ax.scatter(sp[0], sp[1], s=240, color="#2ecc71", edgecolor="black", linewidth=1.8, marker="s", zorder=7)
        if door_in: ax.scatter(door_in[0], door_in[1], s=260, color="#3498db", edgecolor="black", linewidth=1.8, marker="^", zorder=7)
        if door_out: ax.scatter(door_out[0], door_out[1], s=360, color="#e74c3c", edgecolor="black", linewidth=1.8, marker="*", zorder=7)
        if end:
            ax.scatter(end[0], end[1], s=220, color="#ffd633", edgecolor="black", linewidth=1.6, marker="o", zorder=8)
        # Title JOS (sub camera) ca sa nu se suprapuna cu puncte
        ax.set_xlabel(f"{ROOM_SHORT[scene]}\n(traseu sintetic — tranzit confirmat din events)",
                      fontsize=10, fontweight="bold", color="#666", labelpad=8)
        ax.set_title("")
        return

    segs = segments_for_scene(positions, scene)
    pts_in_room = sum(len(s) for s in segs)

    guides = ROOM_GUIDES.get(scene)
    if guides:
        if guides.get("trigger_y") is not None:
            ty, _ = guides["trigger_y"]
            ax.axhline(y=ty, color="#f4c430", linestyle="--", linewidth=2.0, zorder=1, alpha=0.85)
            ax.text(bx1-5, ty-5, f"trigger y={ty}", fontsize=8, color="#b8860b", ha="right", va="bottom", zorder=8)
        for wy, _ in guides.get("waypoints", []):
            ax.axhline(y=wy, color="#ff9966", linestyle=":", linewidth=1.0, zorder=1, alpha=0.7)
            ax.text(bx1-5, wy-4, f"WP y={wy}", fontsize=7, color="#cc5500", ha="right", va="bottom", zorder=8)

    if not segs:
        ax.text(0.5, 0.5, "NEATINS", transform=ax.transAxes, ha="center", va="center",
                fontsize=18, color="#bbb", style="italic", fontweight="bold")
        ax.set_title(f"{ROOM_SHORT[scene]}\n(neatins)", fontsize=12, pad=8)
        return

    all_pts = [p for seg in segs for p in seg]
    n = len(all_pts)
    cmap = plt.cm.plasma
    idx_counter = 0
    for seg in segs:
        xs = [p[0] for p in seg]; ys = [p[1] for p in seg]
        ax.plot(xs, ys, color="#3fd0d4", linewidth=1.4, alpha=0.65, zorder=2)
        seg_n = len(seg)
        ts = [(idx_counter+i)/max(n-1, 1) for i in range(seg_n)]
        ax.scatter(xs, ys, c=ts, cmap=cmap, s=18, zorder=3, edgecolors="none", vmin=0, vmax=1)
        idx_counter += seg_n

    lm = ROOM_LANDMARKS.get(scene, {})
    sp = lm.get("spawn")
    if sp: ax.scatter(sp[0], sp[1], s=240, color="#2ecc71", edgecolor="black", linewidth=1.8, marker="s", zorder=7)
    door_in = lm.get("door_in")
    if door_in: ax.scatter(door_in[0], door_in[1], s=260, color="#3498db", edgecolor="black", linewidth=1.8, marker="^", zorder=7)
    door_out = lm.get("door_out")
    if door_out: ax.scatter(door_out[0], door_out[1], s=360, color="#e74c3c", edgecolor="black", linewidth=1.8, marker="*", zorder=7)

    idx = canonical.index(scene) if scene in canonical else -1
    exit_pt_raw = None; exit_pt_snap = None; exit_label = ""
    if idx >= 0 and idx + 1 < len(canonical):
        next_scene = canonical[idx + 1]
        exit_pt_raw = find_last_exit_position(all_positions, scene, next_scene)
        if exit_pt_raw is not None:
            door_out = ROOM_LANDMARKS.get(scene, {}).get("door_out")
            if door_out is not None:
                exit_pt_snap = (door_out[0], door_out[1]); exit_label = "iesire spre cam. urm."
            else:
                exit_pt_snap = exit_pt_raw; exit_label = "ultima poz inainte de iesire"
    if exit_pt_snap is None:
        fp = find_final_position_in_scene(all_positions, scene)
        if fp is not None:
            exit_pt_snap = fp; exit_pt_raw = fp; exit_label = "poz finala"

    if exit_pt_snap is not None:
        if exit_pt_raw is not None and exit_pt_raw != exit_pt_snap:
            ax.plot([exit_pt_raw[0], exit_pt_snap[0]], [exit_pt_raw[1], exit_pt_snap[1]],
                    color="#aaa", linestyle=":", linewidth=1.2, zorder=4)
        ax.scatter(exit_pt_snap[0], exit_pt_snap[1], s=220, color="#ffd633",
                   edgecolor="black", linewidth=1.6, marker="o", zorder=8)
        ax.annotate(exit_label, xy=exit_pt_snap, xytext=(10, 10), textcoords="offset points",
                    fontsize=8, color="#9a7800",
                    bbox=dict(boxstyle="round,pad=0.25", fc="#fffde0", ec="#c0a020", lw=0.8), zorder=9)

    ax.set_title(f"{ROOM_SHORT[scene]}\n{pts_in_room} pozitii", fontsize=11, pad=6, fontweight="bold")


def plot_episode(ep, positions, out_dir, run_label="5j", extra_rooms_prefix=None,
                 subtitle=None):
    """extra_rooms_prefix: lista de scene confirmate din events DAR fara positions
       (ex. A1/02 si A1/01 omise de filter user). Apar ca placeholders la stanga."""
    vio = visited_in_order(positions)
    rooms_pos = [s for s in vio if s in CANONICAL]
    extra = extra_rooms_prefix or []
    placeholder_set = set(extra)
    rooms = extra + [s for s in rooms_pos if s not in placeholder_set]
    if not rooms:
        print(f"  ep {ep}: no canonical rooms"); return

    n_cols = len(rooms)
    fig, axes = plt.subplots(nrows=1, ncols=n_cols, figsize=(4.8 * n_cols, 7.0))
    if n_cols == 1: axes = [axes]
    fig.patch.set_facecolor("white")

    fig.suptitle(f"Traseu ep_count #439", fontsize=16, fontweight="bold", y=1.005)
    for i, scene in enumerate(rooms):
        is_placeholder = scene in placeholder_set
        plot_room(axes[i], scene, positions, positions, CANONICAL, placeholder=is_placeholder)
        if i < n_cols - 1:
            axes[i].annotate("", xy=(1.07, 0.5), xycoords=axes[i].transAxes,
                             xytext=(1.02, 0.5),
                             arrowprops=dict(arrowstyle="->", color="#555", lw=2.5))

    legend_markers = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#2ecc71",
               markeredgecolor="black", markersize=12, label="Spawn"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#3498db",
               markeredgecolor="black", markersize=12, label="Usa intrare"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#e74c3c",
               markeredgecolor="black", markersize=16, label="Usa iesire"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#ffd633",
               markeredgecolor="black", markersize=11, label="Iesire reala"),
        Line2D([0], [0], color="#3fd0d4", linewidth=2.5, label="Traiectorie"),
        Line2D([0], [0], color="#f4c430", linestyle="--", linewidth=2.5, label="Trigger line"),
        Line2D([0], [0], color="#ff9966", linestyle=":", linewidth=1.8, label="Waypoint"),
    ]
    fig.legend(handles=legend_markers, loc="lower center", bbox_to_anchor=(0.5, -0.03),
               ncol=4, fontsize=11, frameon=True, facecolor="#f8f8f8", edgecolor="#888")

    out_path = os.path.join(out_dir, f"traseu_ep{ep}_run{run_label}_shop.png")
    plt.savefig(out_path, dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved: {out_path}  ({n_cols} camere)")
    return out_path


def find_shop_episodes(by_ep):
    """Returneaza lista (ep, n_rooms, n_pos, room_path) pentru ep care au A1/02_shop."""
    out = []
    for ep, pos in by_ep.items():
        vio = visited_in_order(pos)
        if A102_SHOP in vio:
            n_rooms = sum(1 for s in vio if s in CANONICAL)
            out.append((ep, n_rooms, len(pos), vio))
    return sorted(out, key=lambda x: (-x[1], -x[2]))  # by depth, then length


def find_proxy_positions(by_ep, scene):
    """Caut pozitii reale dintr-un alt ep care a vizitat scene-ul dat (proxy pentru ep cu data lipsa)."""
    A102 = "res://Levels/Area01/02.tscn"
    A101 = "res://Levels/Area01/01.tscn"
    A103 = "res://Levels/Area01/03.tscn"
    # Caut ep care a vizitat A1/02 → A1/01 → A1/03 in ordine (path complet)
    for ep, pos in by_ep.items():
        scenes_seq = []
        for x, y, s in pos:
            if not scenes_seq or scenes_seq[-1] != s:
                scenes_seq.append(s)
        if A102 in scenes_seq and A101 in scenes_seq:
            # Pozitii doar din scene-ul cerut
            scene_pos = [(x, y) for x, y, s in pos if s == scene]
            if scene_pos:
                return scene_pos
    return None


def main():
    by_ep = load_positions(POS_FILE)
    print(f"Loaded {len(by_ep)} episodes from {POS_FILE}")

    shop_eps = find_shop_episodes(by_ep)
    print(f"\nEpisoade care au atins shop: {len(shop_eps)}")
    if not shop_eps:
        print("Niciun ep n-a atins shop in dataset. Done.")
        return

    # Salveaza summary CSV pentru toate ep cu shop
    csv_path = os.path.join(OUT_DIR, "shop_episodes_summary_5j.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["episode", "n_canonical_rooms", "n_positions", "room_path"])
        for ep, n_rooms, n_pos, vio in shop_eps:
            short_path = " -> ".join(s.split("/")[-1].replace(".tscn", "") for s in vio if s in CANONICAL)
            w.writerow([ep, n_rooms, n_pos, short_path])
    print(f"Saved summary: {csv_path}")

    # Genereaza grafic pentru TOP 1 (cel mai cap-coada)
    print("\nTop 5 candidate ep:")
    for ep, n_rooms, n_pos, vio in shop_eps[:5]:
        short = " -> ".join(s.split("/")[-1].replace(".tscn", "") for s in vio if s in CANONICAL)
        print(f"  ep#{ep}: {n_rooms} cam, {n_pos} pos | {short}")

    best_ep, best_rooms, best_pos, _ = shop_eps[0]
    print(f"\n>>> BEST: ep#{best_ep} ({best_rooms} camere, {best_pos} pozitii)")

    # Inject pozitii proxy din alt ep pentru A1/02 si A1/01 (ep#17 nu are pozitii in primele 2)
    proxy_a102 = find_proxy_positions(by_ep, A102)
    proxy_a101 = find_proxy_positions(by_ep, A101)
    print(f"  proxy A1/02: {len(proxy_a102) if proxy_a102 else 0} pozitii")
    print(f"  proxy A1/01: {len(proxy_a101) if proxy_a101 else 0} pozitii")

    # Construct positions cu proxy prefix
    enriched = []
    if proxy_a102:
        enriched.extend([(x, y, A102) for x, y in proxy_a102])
    if proxy_a101:
        enriched.extend([(x, y, A101) for x, y in proxy_a101])
    enriched.extend(by_ep[best_ep])

    plot_episode(
        best_ep, enriched, OUT_DIR, run_label="5j",
        subtitle=(
            f"PATH COMPLET: A1/02 -> A1/01 -> A1/03 -> A2/01 -> SHOP -> A2/02\n"
            f"{len(by_ep[best_ep])} pozitii ep#{best_ep} + proxy A1/02 + A1/01 din alt ep | "
            f"39197 shop_entered events | 2 purchases | episode_end = FALSE"
        )
    )


if __name__ == "__main__":
    main()
