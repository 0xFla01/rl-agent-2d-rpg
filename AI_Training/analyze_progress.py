"""
Analizeaza evolutia antrenarii AI-ului si genereaza grafice pentru licenta.
Citeste din ai_events.jsonl (logat de joc).

Rulare: python analyze_progress.py
Output: folder "results/" cu:
  - reward_per_episod.png      — reward per episod + medie mobila
  - winrate.png                — win-rate in timp
  - timp_completare.png        — timp la victorii
  - killuri.png                — kill-uri per episod
  - camera_atinsa.png          — progresul pe harta (ce camera a atins)
  - damage_luat.png            — damage suferit per episod
  - frecventa_buffs.png        — ce buff-uri alege agentul cel mai des
  - pozitie_moarte.png         — unde moare agentul pe harta
  - nivel_final.png            — nivelul playerului la final de run
  - milestone_progresie.png    — cand invata agentul fiecare obiectiv cheie
  - boss_hp_progresie.png      — progresul in lupta cu boss-ul (HP ramas)
  - timp_per_camera.png        — cat timp petrece agentul in fiecare camera
  - summary.csv                — statistici agregate
  - episoade.csv               — date brute per episod
  - observatii_comportament.txt — analiza text pentru licenta
"""

import os
import json
import csv
from collections import Counter
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.colors import LinearSegmentedColormap

EVENTS_FILE = os.path.join(
    os.environ["APPDATA"],
    "Godot", "app_userdata", "VERSIUNE FINALA", "ai_events.jsonl"
)
RESULTS_DIR = "results_v4"
os.makedirs(RESULTS_DIR, exist_ok=True)


# ── constante joc ─────────────────────────────────────────────────────────────

SCENE_DEPTH = {
    "res://Levels/Area01/02.tscn":       1,   # start run
    "res://Levels/Area01/01.tscn":       2,
    "res://Levels/Area01/03.tscn":       3,
    "res://Levels/Area02/01.tscn":       4,
    "res://Levels/Area01/02_shop.tscn":  5,   # shop (dupa A2/01)
    "res://Levels/Area02/02.tscn":       6,
    "res://Levels/Area01/04.tscn":       7,
    "res://Levels/Dungeon01/01.tscn":    8,
    "res://Levels/Dungeon01/02.tscn":    9,
    "res://Levels/Dungeon01/03.tscn":   10,
    "res://Levels/Dungeon01/04.tscn":   11,   # Boss
}

SCENE_LABEL = {
    "res://Levels/Area01/02.tscn":      "Start",
    "res://Levels/Area01/01.tscn":      "A1 Goblini",
    "res://Levels/Area01/03.tscn":      "A1 Buff",
    "res://Levels/Area02/01.tscn":      "A2 Wave-uri",
    "res://Levels/Area01/02_shop.tscn": "Shop",
    "res://Levels/Area02/02.tscn":      "A2 Levere",
    "res://Levels/Area01/04.tscn":      "Intrare Dungeon",
    "res://Levels/Dungeon01/01.tscn":   "D1 Statuie",
    "res://Levels/Dungeon01/02.tscn":   "D1 Hub",
    "res://Levels/Dungeon01/03.tscn":   "D1 Cheie",
    "res://Levels/Dungeon01/04.tscn":   "BOSS",
}

BUFF_NAMES = {
    "big_damage":    "BRUTE FORCE (+50% dmg)",
    "charge_master": "CHARGE MASTER (x4 charge)",
    "kill_stack":    "KILL STACKS (+2/kill)",
    "speed_boost":   "SWIFT FEET (+40% speed)",
    "extra_dash":    "SHADOW STEP (+1 dash)",
    "ability_power": "ARCANE SURGE (x2 ability)",
    "iron_will":     "IRON WILL (+2 inimi)",
    "glass_cannon":  "GLASS CANNON (+60% dmg)",
    "bloodlust":     "BLOODLUST (heal la kill)",
    "ghost_blade":   "GHOST BLADE (x6 charge)",
    "last_stand":    "LAST STAND (dmg la HP mic)",
    "momentum":      "MOMENTUM (speed/kill)",
    "double_strike": "DOUBLE STRIKE (post-dash)",
    "cheat_death":   "CHEAT DEATH (revive o data)",
    "frenzy":        "FRENZY (atk speed)",
}

# Milestones afisate in graficul de progresie — culori CONTRAST puternic
# (event_type, eticheta romana, culoare, grup: "early"/"late")
MILESTONE_CONFIG = [
    ("run_started",         "Quest luat (NPC)",     "#16a085", "early"),
    ("room_cleared",        "Camera curatata",      "#27ae60", "early"),
    ("ability_item_picked", "Abilitate luata",      "#2980b9", "early"),
    ("buff_picked",         "Buff ales",            "#8e44ad", "early"),
    ("waypoint_y0",         "A1/03 waypoint y=0",   "#f39c12", "early"),
    ("waypoint_y200",       "A1/03 waypoint y=-200","#d35400", "early"),
    ("trigger_line_crossed","A1/03 trigger line",   "#c0392b", "early"),
    ("partial_clear",       "50% kill target",      "#1abc9c", "early"),
    ("shop_purchase",       "Cumparat la shop",     "#3498db", "late"),
    ("puzzle_solved",       "Puzzle rezolvat",      "#9b59b6", "late"),
    ("key_collected",       "Cheie/flaut ridicat",  "#e74c3c", "late"),
    ("boss_door_opened",    "Usa boss deschisa",    "#c0392b", "late"),
]


# ── citire date ────────────────────────────────────────────────────────────────

def load_all_events(path: str) -> list:
    events = []
    if not os.path.exists(path):
        print(f"Fisierul {path} nu exista inca.")
        return events
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    return events


def load_episodes(all_events: list) -> list:
    return [e for e in all_events if e.get("event") == "episode_end"]


def group_events_by_episode(all_events: list) -> list:
    """Grupeaza toate evenimentele pe episoade (intre markeri episode_end)."""
    result = []
    current = []
    for e in all_events:
        current.append(e)
        if e.get("event") == "episode_end":
            result.append(current)
            current = []
    return result


# ── utilitare ─────────────────────────────────────────────────────────────────

def _moving_avg(values: list, window: int = 20) -> list:
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        result.append(float(np.mean(values[start:i+1])))
    return result


def _scene_depth(scene_path: str) -> int:
    return SCENE_DEPTH.get(scene_path, 0)


def _episode_deepest_depth(e: dict) -> int:
    rooms = e.get("rooms_visited", [])
    if rooms:
        return max((_scene_depth(r) for r in rooms), default=0)
    return _scene_depth(e.get("scene_path", ""))


def _depth_label(depth: int) -> str:
    for path, d in SCENE_DEPTH.items():
        if d == depth:
            return SCENE_LABEL.get(path, str(depth))
    return str(depth)


def _split_thirds(lst: list) -> tuple:
    n = len(lst)
    return lst[:n//3], lst[n//3:2*n//3], lst[2*n//3:]


# ── grafice de baza ────────────────────────────────────────────────────────────

def plot_rewards(episodes: list, out_dir: str):
    rewards  = [e.get("reward_total", 0) for e in episodes]
    outcomes = [e.get("outcome", "?")     for e in episodes]
    idx      = list(range(1, len(rewards) + 1))

    fig, ax = plt.subplots(figsize=(12, 5))

    wins  = [i for i, o in zip(idx, outcomes) if o == "win"]
    fails = [i for i, o in zip(idx, outcomes) if o == "fail"]
    rw    = [r for r, o in zip(rewards, outcomes) if o == "win"]
    rf    = [r for r, o in zip(rewards, outcomes) if o == "fail"]

    ax.scatter(fails, rf, color="#e74c3c", s=12, alpha=0.4, label="Fail")
    ax.scatter(wins,  rw, color="#2ecc71", s=18, alpha=0.6, label="Win")
    ax.plot(idx, _moving_avg(rewards, 20),
            color="#3498db", linewidth=2, label="Media mobila (20 ep.)")

    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Episod", fontsize=12)
    ax.set_ylabel("Reward total", fontsize=12)
    ax.set_title("Evolutia reward-ului per episod", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "reward_per_episod.png"), dpi=150)
    plt.close(fig)
    print("  Salvat: reward_per_episod.png")


def plot_winrate(episodes: list, out_dir: str, window: int = 50):
    """
    Win-rate in timp. Daca 0 wins, afiseaza in schimb breakdown outcomes (fail/timeout/etc).
    """
    outcomes = [1 if e.get("outcome") == "win" else 0 for e in episodes]
    n_wins = sum(outcomes)

    if n_wins == 0:
        # Placeholder util: arata distributia outcomes in loc
        outcome_counts = Counter(e.get("outcome", "necunoscut") or "necunoscut" for e in episodes)
        labels = list(outcome_counts.keys())
        counts = [outcome_counts[k] for k in labels]
        colors = {"fail": "#c0392b", "truncated_room": "#f39c12",
                  "truncated_global": "#e67e22", "win": "#27ae60",
                  "necunoscut": "#7f8c8d"}
        bar_colors = [colors.get(l, "#34495e") for l in labels]

        fig, ax = plt.subplots(figsize=(10, 4.5))
        bars = ax.bar(labels, counts, color=bar_colors, alpha=0.85)
        ax.bar_label(bars, fmt="%d", padding=4, fontsize=10)
        total = sum(counts)
        ax.set_title(f"Nicio victorie inca (0 / {total} ep.)\n"
                     "Distributie outcomes — fail = AI mort, truncated = timeout step limit",
                     fontsize=12)
        ax.set_ylabel("Numar episoade", fontsize=11)
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "winrate.png"), dpi=150)
        plt.close(fig)
        print(f"  Salvat: winrate.png (placeholder — 0 wins din {total} ep)")
        return

    if len(outcomes) < window:
        print(f"  Prea putine episoade pentru win-rate (minim {window}).")
        return

    wr  = _moving_avg(outcomes, window)
    idx = list(range(1, len(wr) + 1))

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(idx, [v * 100 for v in wr], color="#9b59b6", linewidth=2)
    ax.fill_between(idx, [v * 100 for v in wr], alpha=0.15, color="#9b59b6")
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f%%"))
    ax.set_ylim(0, 105)
    ax.set_xlabel("Episod", fontsize=12)
    ax.set_ylabel(f"Win-rate (media {window} ep.)", fontsize=12)
    ax.set_title(f"Win-rate in timp ({n_wins} wins)", fontsize=14)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "winrate.png"), dpi=150)
    plt.close(fig)
    print("  Salvat: winrate.png")


def plot_completion_time(episodes: list, out_dir: str):
    wins = [e for e in episodes if e.get("outcome") == "win"]
    if not wins:
        print("  Nicio victorie inca — graficul timpului de completare nu e disponibil.")
        return

    times  = [e.get("time", 0) for e in wins]
    ep_idx = [i+1 for i, e in enumerate(episodes) if e.get("outcome") == "win"]

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.scatter(ep_idx, times, color="#e67e22", s=20, alpha=0.6)
    ax.plot(ep_idx, _moving_avg(times, 10),
            color="#e67e22", linewidth=2, alpha=0.9, label="Media mobila (10 win-uri)")

    best_time = min(times)
    best_ep   = ep_idx[times.index(best_time)]
    ax.annotate(f"Record: {best_time:.0f}s\n(ep. {best_ep})",
                xy=(best_ep, best_time),
                xytext=(best_ep + max(1, len(ep_idx)//10), best_time + 15),
                fontsize=9, color="#c0392b",
                arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.2))

    ax.set_xlabel("Episod", fontsize=12)
    ax.set_ylabel("Timp (secunde)", fontsize=12)
    ax.set_title("Timp de completare la victorii  (scade = agent mai rapid)", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "timp_completare.png"), dpi=150)
    plt.close(fig)
    print("  Salvat: timp_completare.png")


def plot_kills(episodes: list, out_dir: str):
    kills = [e.get("kills", 0) for e in episodes]
    idx   = list(range(1, len(kills) + 1))

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(idx, kills, color="#1abc9c", alpha=0.5, width=1.0)
    ax.plot(idx, _moving_avg(kills, 20),
            color="#16a085", linewidth=2, label="Media mobila (20 ep.)")
    ax.set_xlabel("Episod", fontsize=12)
    ax.set_ylabel("Kill-uri per episod", fontsize=12)
    ax.set_title("Evolutia numarului de kill-uri", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "killuri.png"), dpi=150)
    plt.close(fig)
    print("  Salvat: killuri.png")


def plot_camera_atinsa(episodes: list, out_dir: str):
    depths = [_episode_deepest_depth(e) for e in episodes]
    if all(d == 0 for d in depths):
        print("  Camera atinsa: date indisponibile.")
        return

    idx = list(range(1, len(depths) + 1))
    avg = _moving_avg(depths, 20)
    all_depths = sorted(set(SCENE_DEPTH.values()))
    max_depth  = max(all_depths)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(idx, depths, color="#f39c12", s=10, alpha=0.35, zorder=2)
    ax.plot(idx, avg, color="#e67e22", linewidth=2, label="Media mobila (20 ep.)", zorder=3)
    ax.axhline(max_depth, color="#e74c3c", linestyle="--", linewidth=1.0,
               alpha=0.7, label=f"Boss (nivel {max_depth})")
    ax.set_ylim(0, max_depth + 0.8)
    ax.set_yticks(all_depths)
    ax.set_yticklabels([_depth_label(d) for d in all_depths], fontsize=9)
    ax.set_xlabel("Episod", fontsize=12)
    ax.set_ylabel("Camera maxima atinsa", fontsize=12)
    ax.set_title("Progresul agentului pe harta  (creste = ajunge mai departe)", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "camera_atinsa.png"), dpi=150)
    plt.close(fig)
    print("  Salvat: camera_atinsa.png")


def plot_damage_taken(episodes: list, out_dir: str):
    """
    Damage suferit per episod — SPLIT pe outcome:
    - fail (AI mort): damage 4-6 e normal
    - truncated (timeout): damage scazut e normal (AI a evitat sau nu a luptat)
    Mediile globale erau inselatoare — un AI care timeout-ueste fara combat pare "evita mai bine"
    """
    fail_pts   = []   # (idx, dmg) pentru fail
    trunc_pts  = []   # (idx, dmg) pentru truncated/etc
    fail_dmg_series, trunc_dmg_series = [], []
    fail_x, trunc_x = [], []
    for i, e in enumerate(episodes, start=1):
        d = e.get("damage_taken", 0)
        outcome = e.get("outcome", "")
        if outcome == "fail":
            fail_pts.append((i, d))
            fail_dmg_series.append(d); fail_x.append(i)
        elif outcome and outcome != "win":
            trunc_pts.append((i, d))
            trunc_dmg_series.append(d); trunc_x.append(i)

    if not fail_pts and not trunc_pts:
        print("  Damage luat: date insuficiente.")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 4.5),
                                    gridspec_kw={"width_ratios": [3, 1]})

    # Stanga: scatter + media mobila per categorie
    if fail_pts:
        xs, ys = zip(*fail_pts)
        ax1.scatter(xs, ys, color="#c0392b", s=14, alpha=0.4, label=f"Fail (n={len(fail_pts)})")
    if trunc_pts:
        xs, ys = zip(*trunc_pts)
        ax1.scatter(xs, ys, color="#f39c12", s=14, alpha=0.4, label=f"Truncated/timeout (n={len(trunc_pts)})")

    # Linii medii mobile, doar daca avem >=10 puncte
    def _avg_sparse(xs, ys, win=20):
        if len(ys) < win: return None, None
        ys_avg = _moving_avg(ys, win)
        return xs, ys_avg

    fx, fy = _avg_sparse(fail_x, fail_dmg_series)
    if fx: ax1.plot(fx, fy, color="#c0392b", linewidth=2.5, label="Medie fail (20 ep)")
    tx, ty = _avg_sparse(trunc_x, trunc_dmg_series)
    if tx: ax1.plot(tx, ty, color="#e67e22", linewidth=2.5, label="Medie timeout (20 ep)")

    ax1.set_xlabel("Episod", fontsize=12)
    ax1.set_ylabel("Damage suferit / episod", fontsize=12)
    ax1.set_title("Damage suferit — split fail vs timeout\n(fail mare = mort normal; timeout=0 = AI nu a fost in combat)", fontsize=12)
    ax1.legend(fontsize=10, loc="best")
    ax1.grid(True, alpha=0.3)

    # Dreapta: histograma distribuție damage
    all_dmgs = [d for _, d in fail_pts] + [d for _, d in trunc_pts]
    if all_dmgs:
        max_d = max(max(all_dmgs), 6)
        ax2.hist([[d for _, d in fail_pts], [d for _, d in trunc_pts]],
                 bins=range(0, max_d+2), color=["#c0392b", "#f39c12"],
                 alpha=0.75, label=["Fail", "Truncated"], stacked=True)
        ax2.set_xlabel("Damage", fontsize=11)
        ax2.set_ylabel("Numar ep", fontsize=11)
        ax2.set_title("Distributie damage", fontsize=12)
        ax2.legend(fontsize=9)
        ax2.grid(True, axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "damage_luat.png"), dpi=150)
    plt.close(fig)
    print("  Salvat: damage_luat.png")


def plot_buff_frequency(episodes: list, all_events: list, out_dir: str):
    buff_events = [e for e in all_events if e.get("event") == "buff_picked"]

    if buff_events:
        counter = Counter(e.get("buff_id", "?") for e in buff_events)
    else:
        counter = Counter()
        for ep in episodes:
            for bid in ep.get("buffs", []):
                counter[bid] += 1

    if not counter:
        print("  Frecventa buffs: niciun buff ales inca.")
        return

    ids, counts = zip(*sorted(counter.items(), key=lambda x: x[1]))
    labels = [BUFF_NAMES.get(bid, bid) for bid in ids]
    colors = plt.cm.RdYlGn(np.linspace(0.2, 0.85, len(ids)))

    fig, ax = plt.subplots(figsize=(11, max(4, len(ids) * 0.52)))
    bars = ax.barh(labels, counts, color=colors, edgecolor="white", linewidth=0.5)
    ax.bar_label(bars, fmt="%d", padding=4, fontsize=9)
    ax.set_xlabel("Numar de alegeri", fontsize=12)
    ax.set_title("Frecventa alegerii buff-urilor de catre agent", fontsize=14)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "frecventa_buffs.png"), dpi=150)
    plt.close(fig)
    print("  Salvat: frecventa_buffs.png")


SCENE_BOUNDS_DEATH = {
    "res://Levels/Area01/02.tscn":    (-50, 500, -100, 400),
    "res://Levels/Area01/01.tscn":    ( 50, 450,  -50, 380),
    "res://Levels/Area01/03.tscn":    (-50, 650, -650, 380),
    "res://Levels/Area02/01.tscn":    (-50, 700, -400, 1100),
    "res://Levels/Area02/02.tscn":    (-50, 700,  -50, 700),
    "res://Levels/Area01/04.tscn":    (-50, 500,  -50, 500),
    "res://Levels/Dungeon01/01.tscn": (-50, 500,  -50, 500),
    "res://Levels/Dungeon01/02.tscn": (-50, 700, -100, 700),
    "res://Levels/Dungeon01/03.tscn": (-50, 700,  -50, 700),
    "res://Levels/Dungeon01/04.tscn": (-50, 700,  -50, 700),
}


def plot_death_positions(episodes: list, out_dir: str):
    # Grupeaza mortile per scene
    deaths_by_scene: dict = {}
    for i, e in enumerate(episodes):
        if e.get("outcome") != "fail":
            continue
        if e.get("death_x") is None:
            continue
        scene = e.get("scene_path", "")
        if not scene:
            continue
        deaths_by_scene.setdefault(scene, []).append((e["death_x"], e["death_y"], i))

    if not deaths_by_scene:
        print("  Pozitie moarte: date indisponibile.")
        return

    # Sorteaza scenele dupa depth
    sorted_scenes = sorted(deaths_by_scene.keys(), key=lambda s: SCENE_DEPTH.get(s, 99))
    n = len(sorted_scenes)
    cols = min(3, n)
    rows = (n + cols - 1) // cols
    cmap = LinearSegmentedColormap.from_list("progress", ["#e74c3c", "#3498db"])

    fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 5*rows), squeeze=False)
    total_episodes = len(episodes)
    for idx, scene in enumerate(sorted_scenes):
        ax = axes[idx // cols][idx % cols]
        data = deaths_by_scene[scene]
        xs = [d[0] for d in data]
        ys = [-d[1] for d in data]
        ep_nums = [d[2] for d in data]
        sc = ax.scatter(xs, ys, c=ep_nums, cmap=cmap, s=28, alpha=0.7,
                        edgecolors="none", vmin=0, vmax=total_episodes)
        if scene in SCENE_BOUNDS_DEATH:
            xmin, xmax, ymin, ymax = SCENE_BOUNDS_DEATH[scene]
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(-ymax, -ymin)
        label = SCENE_LABEL.get(scene, scene.split("/")[-1])
        ax.set_title(f"{label}  ({len(data)} morti)", fontsize=11)
        ax.set_xlabel("X", fontsize=9)
        ax.set_ylabel("Y inversat", fontsize=9)
        ax.grid(True, alpha=0.3)

    # Asciunde axele goale
    for j in range(n, rows*cols):
        axes[j // cols][j % cols].axis("off")

    # Colorbar global
    cbar = fig.colorbar(sc, ax=axes, location="right", shrink=0.7,
                        pad=0.02, aspect=30)
    cbar.set_label("Ordinea ep. (rosu = inceput, albastru = final)", fontsize=10)
    fig.suptitle("Pozitia mortii agentului — separat per camera", fontsize=14, y=1.0)
    fig.savefig(os.path.join(out_dir, "pozitie_moarte.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  Salvat: pozitie_moarte.png ({n} camere)")


def plot_level_progression(episodes: list, out_dir: str):
    levels = [e.get("level", 0) for e in episodes]
    if all(lv == 0 for lv in levels):
        print("  Nivel final: date indisponibile.")
        return

    idx = list(range(1, len(levels) + 1))
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.scatter(idx, levels, color="#8e44ad", s=10, alpha=0.35)
    ax.plot(idx, _moving_avg(levels, 20), color="#9b59b6", linewidth=2,
            label="Media mobila (20 ep.)")
    ax.set_xlabel("Episod", fontsize=12)
    ax.set_ylabel("Nivel la sfarsitul run-ului", fontsize=12)
    ax.set_title("Nivelul playerului la finalul episodului  (creste = supravietuieste mai mult)", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "nivel_final.png"), dpi=150)
    plt.close(fig)
    print("  Salvat: nivel_final.png")


# ── grafice noi ────────────────────────────────────────────────────────────────

def plot_milestone_progression(all_events: list, out_dir: str, window: int = 50):
    """
    Doua panouri care arata cand invata agentul fiecare obiectiv cheie.
    Panoul de sus  = obiective din prima parte a jocului (camera curatata, buffs, abilitati).
    Panoul de jos  = obiective avansate (shop, puzzle, cheie, usa boss).
    Y = media evenimentelor per episod (medie mobila 50 ep.) — creste = face mai des.
    """
    by_ep = group_events_by_episode(all_events)
    if not by_ep:
        print("  Milestone progresie: date insuficiente.")
        return

    # Numara fiecare tip de eveniment per episod
    all_types = [cfg[0] for cfg in MILESTONE_CONFIG]
    counts_per_ep = {t: [] for t in all_types}
    for ep_events in by_ep:
        freq = {}
        for ev in ep_events:
            et = ev.get("event", "")
            if et in counts_per_ep:
                freq[et] = freq.get(et, 0) + 1
        for t in all_types:
            counts_per_ep[t].append(freq.get(t, 0))

    n_ep = len(by_ep)
    idx  = list(range(1, n_ep + 1))

    # Filtreaza milestone-uri cu CEL PUTIN 1 eveniment in tot antrenamentul
    def _has_data(t): return sum(counts_per_ep[t]) > 0
    early = [(t, lbl, col) for t, lbl, col, grp in MILESTONE_CONFIG if grp == "early" and _has_data(t)]
    late  = [(t, lbl, col) for t, lbl, col, grp in MILESTONE_CONFIG if grp == "late"  and _has_data(t)]

    if not early and not late:
        print("  Milestone progresie: niciun eveniment cheie inregistrat inca.")
        return

    n_panels = (1 if early else 0) + (1 if late else 0)
    fig, axes = plt.subplots(n_panels, 1, figsize=(14, 4.5*n_panels), sharex=True, squeeze=False)
    axes = [a[0] for a in axes]
    fig.suptitle(
        "Frecventa evenimentelor cheie pe parcursul antrenarii\n"
        "(medie mobila 50 ep — creste = agentul face mai des acel obiectiv)\n"
        "[liniile lipsa = obiective neatinse inca]",
        fontsize=13, fontweight="bold"
    )

    ai = 0
    if early:
        ax = axes[ai]; ai += 1
        for t, lbl, col in early:
            data = _moving_avg(counts_per_ep[t], window)
            # Adaug count total in eticheta
            total = sum(counts_per_ep[t])
            ax.plot(idx, data, color=col, linewidth=2.2, label=f"{lbl} (total: {total})")
            # Annotation primul ep cu eveniment
            first = next((i+1 for i, v in enumerate(counts_per_ep[t]) if v > 0), None)
            if first:
                ax.axvline(first, color=col, linestyle=":", alpha=0.4, linewidth=1)
        ax.set_ylabel("Evenimente / episod", fontsize=11)
        ax.set_title("Obiective timpurii  (NPC quest, combat, A1/03, partial clear)", fontsize=12)
        ax.legend(fontsize=9, loc="upper left", ncol=2)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)

    if late:
        ax = axes[ai]; ai += 1
        for t, lbl, col in late:
            data = _moving_avg(counts_per_ep[t], window)
            total = sum(counts_per_ep[t])
            ax.plot(idx, data, color=col, linewidth=2.2, label=f"{lbl} (total: {total})")
            first = next((i+1 for i, v in enumerate(counts_per_ep[t]) if v > 0), None)
            if first:
                ax.axvline(first, color=col, linestyle=":", alpha=0.4, linewidth=1)
        ax.set_ylabel("Evenimente / episod", fontsize=11)
        ax.set_xlabel("Episod", fontsize=12)
        ax.set_title("Obiective avansate  (dungeon, cheie, boss)", fontsize=12)
        ax.legend(fontsize=10, loc="upper left")
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)

    axes[-1].set_xlabel("Episod", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "milestone_progresie.png"), dpi=150)
    plt.close(fig)
    print(f"  Salvat: milestone_progresie.png ({len(early)} early + {len(late)} late milestones cu date)")


def plot_boss_hp(episodes: list, out_dir: str):
    """
    Arata cat de mult damage i-a facut agentul boss-ului in fiecare run unde l-a atins.
    Scade = mai bine (HP 500 = n-a ajuns, HP 0 = l-a omorat).
    Anoteaza cel mai bun rezultat.
    """
    boss_data = [
        (i + 1, e.get("boss_hp_min", -1))
        for i, e in enumerate(episodes)
        if e.get("boss_hp_min", -1) >= 0
    ]

    if not boss_data:
        print("  Boss HP: agentul nu a ajuns inca la boss.")
        return

    ep_nums = [x[0] for x in boss_data]
    hp_vals = [x[1] for x in boss_data]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(ep_nums, hp_vals, color="#e74c3c", s=20, alpha=0.45,
               label="HP boss la finalul run-ului", zorder=3)

    if len(hp_vals) >= 5:
        smooth = _moving_avg(hp_vals, min(10, len(hp_vals)))
        ax.plot(ep_nums, smooth, color="#c0392b", linewidth=2.5,
                label="Media mobila (10 run-uri cu boss)", zorder=4)

    ax.axhline(0,   color="#27ae60", linewidth=1.8, linestyle="--",
               alpha=0.8, label="Boss mort (HP = 0)  ← tinta")
    ax.axhline(500, color="gray",    linewidth=1.0, linestyle=":",
               alpha=0.5, label="HP initial boss (500)")

    min_hp = min(hp_vals)
    min_ep = ep_nums[hp_vals.index(min_hp)]
    offset_x = max(1, (max(ep_nums) - min(ep_nums)) // 12)
    ax.annotate(
        f"Cel mai bun: {min_hp} HP\n(episod {min_ep})",
        xy=(min_ep, min_hp),
        xytext=(min_ep + offset_x, min(min_hp + 60, 480)),
        fontsize=9, color="#c0392b",
        arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.3)
    )

    ax.set_ylim(-15, 520)
    ax.set_xlabel("Episod", fontsize=12)
    ax.set_ylabel("HP boss ramas la sfarsitul run-ului", fontsize=12)
    ax.set_title(
        f"Progres in lupta cu boss-ul  ({len(ep_nums)} run-uri cu boss atins)\n"
        "Scade = agentul ii face mai mult damage — tinta: HP = 0",
        fontsize=13
    )
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "boss_hp_progresie.png"), dpi=150)
    plt.close(fig)
    print("  Salvat: boss_hp_progresie.png")


def _compute_time_per_room(episodes_events: list) -> tuple:
    """
    Returneaza 2 dicturi:
      - room_times_exited:    durate cand AI A IESIT din camera (a trecut la urmatoarea)
      - room_times_terminated: durate cand AI A TERMINAT episodul in acea camera (moarte/timeout)
    """
    room_times_exited = {}
    room_times_terminated = {}
    for ep_events in episodes_events:
        room_enters = [
            (e["timestamp"], e.get("scene_path", ""))
            for e in ep_events
            if e.get("event") == "room_entered" and e.get("scene_path") and e.get("timestamp")
        ]
        ep_end = next((e for e in ep_events if e.get("event") == "episode_end"), None)

        for i, (ts, scene) in enumerate(room_enters):
            is_last = (i + 1 >= len(room_enters))
            if not is_last:
                duration = room_enters[i + 1][0] - ts
                bucket = room_times_exited
            elif ep_end and ep_end.get("timestamp"):
                duration = ep_end["timestamp"] - ts
                bucket = room_times_terminated
            else:
                continue

            if scene and 0 < duration < 600:
                bucket.setdefault(scene, []).append(duration)

    return room_times_exited, room_times_terminated


def plot_timp_per_camera(all_events: list, out_dir: str):
    """
    Bara dubla per camera: timp pentru VIZITE REUSITE (a iesit la urmatoarea camera)
    vs timp pentru VIZITE TERMINATE in acea camera (moarte/timeout).
    Asta evita iluzia ca "AI care moare rapid arata mai bun decat unul care joaca complet".
    """
    by_ep     = group_events_by_episode(all_events)
    exited, terminated = _compute_time_per_room(by_ep)

    ordered = sorted(SCENE_DEPTH.items(), key=lambda x: x[1])
    labels, means_ex, means_te, n_ex, n_te = [], [], [], [], []

    for scene, _ in ordered:
        t_ex = exited.get(scene, [])
        t_te = terminated.get(scene, [])
        if len(t_ex) + len(t_te) < 5:
            continue
        labels.append(SCENE_LABEL.get(scene, scene.split("/")[-1]))
        means_ex.append(np.mean(t_ex) if t_ex else 0)
        means_te.append(np.mean(t_te) if t_te else 0)
        n_ex.append(len(t_ex))
        n_te.append(len(t_te))

    if not labels:
        print("  Timp per camera: date insuficiente (minim 5 vizite per camera).")
        return

    x     = np.arange(len(labels))
    width = 0.38

    fig, ax = plt.subplots(figsize=(13, 5.5))
    bars_ex = ax.bar(x - width / 2, means_ex, width,
                     label="A iesit din camera (vizita reusita)", color="#2ecc71", alpha=0.85)
    bars_te = ax.bar(x + width / 2, means_te, width,
                     label="A terminat episodul aici (moarte/timeout)", color="#e74c3c", alpha=0.85)

    ax.bar_label(bars_ex, fmt="%.0fs", padding=3, fontsize=8, color="#1e8449")
    ax.bar_label(bars_te, fmt="%.0fs", padding=3, fontsize=8, color="#a82c1a")

    # Counts sub fiecare bara
    ymax = max(max(means_ex), max(means_te))
    for i, (cex, cte) in enumerate(zip(n_ex, n_te)):
        ax.text(i - width/2, -ymax * 0.05, f"n={cex}", ha="center", fontsize=7.5, color="#1e8449")
        ax.text(i + width/2, -ymax * 0.05, f"n={cte}", ha="center", fontsize=7.5, color="#a82c1a")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=10)
    ax.set_ylabel("Timp petrecut (secunde)", fontsize=12)
    ax.set_title(
        "Timp mediu per camera — SEPARAT pe outcome\n"
        "(verde = camera \"facuta\" + iesit; rosu = AI a murit/timeout aici)",
        fontsize=13
    )
    ax.legend(fontsize=10, loc="upper left")
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "timp_per_camera.png"), dpi=150)
    plt.close(fig)
    print("  Salvat: timp_per_camera.png")


# ── summary CSV ────────────────────────────────────────────────────────────────

def save_summary(episodes: list, all_events: list, out_dir: str):
    if not episodes:
        return

    total = len(episodes)
    wins  = [e for e in episodes if e.get("outcome") == "win"]
    fails = [e for e in episodes if e.get("outcome") == "fail"]
    wr    = len(wins) / total * 100

    rewards  = [e.get("reward_total", 0) for e in episodes]
    times_w  = [e.get("time", 0)         for e in wins]
    kills    = [e.get("kills", 0)         for e in episodes]
    dmg      = [e.get("damage_taken", 0)  for e in episodes]

    boss_eps  = [e for e in episodes if e.get("boss_hp_min", -1) >= 0]
    boss_hps  = [e["boss_hp_min"] for e in boss_eps]

    shop_purchases = [e for e in all_events if e.get("event") == "shop_purchase"]
    shop_counter   = Counter(e.get("item_name", "?") for e in shop_purchases)

    thirds = np.array_split(episodes, 3)
    def wr_third(ep_list):
        if not len(ep_list): return 0.0
        return sum(1 for e in ep_list if e.get("outcome") == "win") / len(ep_list) * 100

    summary = {
        "Data analiza":               datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Total episoade":             total,
        "Win-uri":                    len(wins),
        "Fail-uri":                   len(fails),
        "Win-rate overall":           f"{wr:.1f}%",
        "Win-rate prima treime":      f"{wr_third(thirds[0]):.1f}%",
        "Win-rate a doua treime":     f"{wr_third(thirds[1]):.1f}%",
        "Win-rate ultima treime":     f"{wr_third(thirds[2]):.1f}%",
        "Reward mediu":               f"{np.mean(rewards):.1f}",
        "Reward max":                 f"{max(rewards):.1f}",
        "Timp mediu win (s)":         f"{np.mean(times_w):.1f}"  if times_w  else "N/A",
        "Timp minim win (s)":         f"{min(times_w):.1f}"      if times_w  else "N/A",
        "Kill-uri medii/ep":          f"{np.mean(kills):.1f}",
        "Damage mediu/ep":            f"{np.mean(dmg):.1f}",
        "Episoade cu boss atins":     len(boss_eps),
        "HP boss minim atins":        f"{min(boss_hps)}" if boss_hps else "N/A",
        "Cumparaturi shop (total)":   len(shop_purchases),
        "Item cel mai cumparat":      shop_counter.most_common(1)[0][0] if shop_counter else "N/A",
    }

    csv_path = os.path.join(out_dir, "summary.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Metrica", "Valoare"])
        for k, v in summary.items():
            w.writerow([k, v])
    print(f"  Salvat: summary.csv")

    print("\n" + "=" * 54)
    print("  SUMMARY ANTRENARE AI")
    print("=" * 54)
    for k, v in summary.items():
        print(f"  {k:<36} {v}")
    print("=" * 54)

    # ── episoade.csv ──────────────────────────────────────────────────────────
    ep_csv = os.path.join(out_dir, "episoade.csv")
    with open(ep_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "episod", "outcome", "reward_total", "time_s",
            "kills", "damage_taken", "buff_count",
            "boss_reached", "boss_hp_min",
            "level", "hp_remaining", "gems",
            "camera_maxima", "scene_path",
        ])
        for i, e in enumerate(episodes, 1):
            depth = _episode_deepest_depth(e)
            w.writerow([
                i,
                e.get("outcome", "?"),
                round(e.get("reward_total", 0), 1),
                round(e.get("time", 0), 1),
                e.get("kills", 0),
                e.get("damage_taken", 0),
                e.get("buff_count", len(e.get("buffs", []))),
                1 if e.get("boss_reached") else 0,
                e.get("boss_hp_min", -1),
                e.get("level", 0),
                e.get("hp_remaining", 0),
                e.get("gems", 0),
                _depth_label(depth) if depth else "?",
                e.get("scene_path", ""),
            ])
    print(f"  Salvat: episoade.csv")


# ── observatii comportament ────────────────────────────────────────────────────

def generate_behavioral_observations(episodes: list, all_events: list, out_dir: str):
    if not episodes:
        return

    total = len(episodes)
    t1, t2, t3 = _split_thirds(episodes)

    def wr(ep_list):
        if not ep_list: return 0.0
        return sum(1 for e in ep_list if e.get("outcome") == "win") / len(ep_list) * 100

    def avg(ep_list, key):
        vals = [e.get(key, 0) for e in ep_list if e.get(key) is not None]
        return np.mean(vals) if vals else 0.0

    def avg_depth(ep_list):
        depths = [_episode_deepest_depth(e) for e in ep_list if _episode_deepest_depth(e) > 0]
        return np.mean(depths) if depths else 0.0

    def boss_rate(ep_list):
        if not ep_list: return 0.0
        return sum(1 for e in ep_list if e.get("boss_reached")) / len(ep_list) * 100

    def trend_text(a, c, threshold=5.0, inverted=False):
        diff = (c - a) if not inverted else (a - c)
        if diff > threshold:  return "CRESTERE CLARA"
        if diff < -threshold: return "SCADERE CLARA"
        return "RELATIV STABIL"

    buff_events  = [e for e in all_events if e.get("event") == "buff_picked"]
    buff_counter = Counter(e.get("buff_id", "?") for e in buff_events) if buff_events else Counter(
        bid for ep in episodes for bid in ep.get("buffs", [])
    )

    shop_events   = [e for e in all_events if e.get("event") == "shop_purchase"]
    shop_counter  = Counter(e.get("item_name", "?") for e in shop_events)

    boss_eps  = [e for e in episodes if e.get("boss_hp_min", -1) >= 0]
    boss_hps  = [e["boss_hp_min"] for e in boss_eps]
    boss_t1   = [e["boss_hp_min"] for e in t1 if e.get("boss_hp_min", -1) >= 0]
    boss_t3   = [e["boss_hp_min"] for e in t3 if e.get("boss_hp_min", -1) >= 0]

    wr1, wr2, wr3 = wr(t1), wr(t2), wr(t3)
    d1,  d2,  d3  = avg_depth(t1), avg_depth(t2), avg_depth(t3)
    dm1, dm2, dm3 = avg(t1, "damage_taken"), avg(t2, "damage_taken"), avg(t3, "damage_taken")
    k1,  k2,  k3  = avg(t1, "kills"), avg(t2, "kills"), avg(t3, "kills")
    br1, br2, br3 = boss_rate(t1), boss_rate(t2), boss_rate(t3)
    top_buffs     = buff_counter.most_common(5)

    sep = "=" * 64

    lines = [
        "OBSERVATII COMPORTAMENT AI",
        "Analiza automata generata de analyze_progress.py",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Total episoade analizate: {total}  "
        f"(treime1={len(t1)}, treime2={len(t2)}, treime3={len(t3)})",
        "",
        sep,
        "1. EVOLUTIA WIN-RATE",
        sep,
        f"   Prima treime  ({len(t1):4d} ep.) : {wr1:5.1f}%",
        f"   A doua treime ({len(t2):4d} ep.) : {wr2:5.1f}%",
        f"   Ultima treime ({len(t3):4d} ep.) : {wr3:5.1f}%",
        f"   Trend: {trend_text(wr1, wr3)}",
        f"   -> Agentul {'imbunatateste' if wr3 > wr1 + 5 else 'nu imbunatateste semnificativ'}"
        f" capacitatea de a castiga.",
        "",
    ]

    if d1 > 0 or d3 > 0:
        lines += [
            sep,
            "2. PROGRES PE HARTA  (scala 1-11, 11 = camera boss)",
            sep,
            f"   Prima treime  : {d1:.2f}  ({_depth_label(round(d1)) if d1 > 0 else '?'})",
            f"   A doua treime : {d2:.2f}  ({_depth_label(round(d2)) if d2 > 0 else '?'})",
            f"   Ultima treime : {d3:.2f}  ({_depth_label(round(d3)) if d3 > 0 else '?'})",
            f"   Trend: {trend_text(d1, d3, threshold=0.5)}",
            f"   Boss atins    : {br1:.0f}% -> {br2:.0f}% -> {br3:.0f}%",
            f"   -> Agentul {'progreseaza mai departe in joc' if d3 > d1 + 0.5 else 'stagneaza la aceeasi adancime'}.",
            "",
        ]

    lines += [
        sep,
        "3. DAMAGE SUFERIT / EPISOD  (scade = evita mai bine)",
        sep,
        f"   Prima treime  : {dm1:.1f} dmg/run",
        f"   A doua treime : {dm2:.1f} dmg/run",
        f"   Ultima treime : {dm3:.1f} dmg/run",
        f"   Trend: {trend_text(dm1, dm3, inverted=True)}",
        f"   -> Agentul {'invata sa evite atacurile' if dm3 < dm1 - 2 else 'nu imbunatateste semnificativ evitarea'}.",
        "",
        sep,
        "4. KILL-URI / EPISOD",
        sep,
        f"   Prima treime  : {k1:.1f} kill-uri",
        f"   A doua treime : {k2:.1f} kill-uri",
        f"   Ultima treime : {k3:.1f} kill-uri",
        f"   Trend: {trend_text(k1, k3, threshold=2.0)}",
        f"   -> {'Creste numarul de inamici eliminati.' if k3 > k1 + 2 else 'Numarul de kill-uri este relativ constant.'}",
        "",
    ]

    if boss_eps:
        lines += [
            sep,
            "5. PROGRES IN LUPTA CU BOSS-UL",
            sep,
            f"   Run-uri cu boss atins     : {len(boss_eps)} din {total} ({len(boss_eps)/total*100:.1f}%)",
            f"   HP boss minim atins       : {min(boss_hps)} / 500",
            f"   HP boss mediu             : {np.mean(boss_hps):.0f} / 500",
        ]
        if boss_t1 and boss_t3:
            lines += [
                f"   HP boss (prima treime)    : {np.mean(boss_t1):.0f}",
                f"   HP boss (ultima treime)   : {np.mean(boss_t3):.0f}",
                f"   Trend: {'CRESTERE CLARA' if np.mean(boss_t3) < np.mean(boss_t1) - 20 else 'RELATIV STABIL'}",
            ]
        lines += [
            f"   -> {'Agentul invata sa faca mai mult damage boss-ului.' if boss_t3 and boss_t1 and np.mean(boss_t3) < np.mean(boss_t1) - 20 else 'Agentul ajunge la boss dar nu i-a redus semnificativ HP-ul inca.'}",
            "",
        ]

    if top_buffs:
        lines += [
            sep,
            "6. PREFERINTE BUFF-URI",
            sep,
        ]
        for rank, (bid, count) in enumerate(top_buffs, 1):
            name = BUFF_NAMES.get(bid, bid)
            pct  = count / sum(buff_counter.values()) * 100 if buff_counter else 0
            lines.append(f"   {rank}. {name:<35} {count:4d} alegeri ({pct:.1f}%)")
        lines += [
            "",
            "   -> Preferintele reflecta stilul de lupta invatat.",
            "",
        ]

    if shop_counter:
        lines += [
            sep,
            "7. CUMPARATURI DE LA SHOP",
            sep,
        ]
        for item, cnt in shop_counter.most_common():
            pct = cnt / len(shop_events) * 100
            lines.append(f"   {item:<35} {cnt:4d} cumparari ({pct:.1f}%)")
        lines += [""]

    lines += [
        sep,
        "NOTE METODOLOGICE",
        sep,
        "   - Analiza imparte antrenarea in 3 treimi egale.",
        "   - 'Crestere clara' (win-rate) = diferenta > 5 pp intre treimi.",
        "   - 'Crestere clara' (adancime) = diferenta > 0.5 intre treimi.",
        "   - Graficele PNG din acelasi folder ofera detalii vizuale.",
        "   - Fisierul episoade.csv poate fi importat in Excel/SPSS.",
        "   - boss_hp_min = -1 in CSV inseamna ca agentul nu a ajuns la boss in acel run.",
    ]

    obs_path = os.path.join(out_dir, "observatii_comportament.txt")
    with open(obs_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Salvat: observatii_comportament.txt")

    for line in lines[:40]:
        print(line)
    if len(lines) > 40:
        print(f"  ... (restul in {obs_path})")


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"Citesc evenimentele din:\n  {EVENTS_FILE}\n")
    all_events = load_all_events(EVENTS_FILE)
    episodes   = load_episodes(all_events)

    if not episodes:
        print("Niciun episod gasit. Asigura-te ca jocul a rulat cu AI mode activ (F2).")
        return

    buff_picks   = sum(1 for e in all_events if e.get("event") == "buff_picked")
    room_evts    = sum(1 for e in all_events if e.get("event") == "room_entered")
    shop_buys    = sum(1 for e in all_events if e.get("event") == "shop_purchase")
    boss_reached = sum(1 for e in episodes  if e.get("boss_reached"))

    print(f"Episoade gasite   : {len(episodes)}")
    print(f"Buff picks         : {buff_picks}")
    print(f"Room entries       : {room_evts}")
    print(f"Shop purchases     : {shop_buys}")
    print(f"Episoade cu boss   : {boss_reached}")
    print(f"\nGenerez grafice in '{RESULTS_DIR}/'...\n")

    # Grafice de baza
    plot_rewards(episodes, RESULTS_DIR)
    plot_winrate(episodes, RESULTS_DIR)
    plot_completion_time(episodes, RESULTS_DIR)
    plot_kills(episodes, RESULTS_DIR)
    plot_camera_atinsa(episodes, RESULTS_DIR)
    plot_damage_taken(episodes, RESULTS_DIR)
    plot_buff_frequency(episodes, all_events, RESULTS_DIR)
    plot_death_positions(episodes, RESULTS_DIR)
    plot_level_progression(episodes, RESULTS_DIR)

    # Grafice noi
    plot_milestone_progression(all_events, RESULTS_DIR)
    plot_boss_hp(episodes, RESULTS_DIR)
    plot_timp_per_camera(all_events, RESULTS_DIR)

    print()
    save_summary(episodes, all_events, RESULTS_DIR)
    print()
    generate_behavioral_observations(episodes, all_events, RESULTS_DIR)

    print(f"\nGata! Deschide folderul '{RESULTS_DIR}/' pentru toate graficele si rapoartele.")


if __name__ == "__main__":
    main()
