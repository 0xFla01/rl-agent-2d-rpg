"""
Compara metrici intre mai multe runuri (random baseline vs PPO+BC etc).

Citeste ai_events_*.jsonl arhivate si scoate:
  - console: tabel comparativ
  - CSV: results_v4/compare_runs.csv
  - Markdown: results_v4/compare_runs.md  (paste-able in lucrare)

Folosire:
  python compare_runs.py                # ruleaza pe RUNS_DEFAULT (de mai jos)
  python compare_runs.py --runs random=ai_events_random.jsonl ppo=ai_events_run5e.jsonl
"""

import argparse
import csv
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "results_v4")
os.makedirs(OUT_DIR, exist_ok=True)

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
A2_SCENE = "res://Levels/Area02/01.tscn"

# Runuri default — modifica daca redenumesti fisierele
RUNS_DEFAULT = [
    ("random_uniform",   "ai_events_uniform.jsonl"),
    ("random_realistic", "ai_events_realistic.jsonl"),
    ("PPO Run 3",        "ai_events_run3.jsonl"),
    ("PPO+BC Run 5c",    "ai_events_run5c.jsonl"),
    ("PPO+BC Run 5d",    "ai_events_run5d.jsonl"),
    ("PPO+BC Run 5e",    "ai_events_run5e.jsonl"),
]


def load_episodes(path: str) -> list:
    """Parseaza ai_events.jsonl si returneaza lista de dict-uri per episod
    cu metrici calculate (kills, depth_max, time, outcome, rooms, etc.)."""
    if not os.path.exists(path):
        return []
    eps = []
    cur = None
    waypoint_y350 = False
    trigger_cross = False
    buffs_in_ep = 0
    a2_reached = False
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            e = ev.get("event")
            if e == "run_started":
                cur = {"rooms": set()}
                waypoint_y350 = False
                trigger_cross = False
                buffs_in_ep = 0
                a2_reached = False
            elif cur is not None:
                if e == "room_entered":
                    scn = ev.get("scene_path")
                    cur["rooms"].add(scn)
                    if scn == A2_SCENE:
                        a2_reached = True
                elif e == "waypoint_y350":
                    waypoint_y350 = True
                elif e == "trigger_line_crossed":
                    trigger_cross = True
                elif e == "buff_picked":
                    buffs_in_ep += 1
                elif e == "episode_end":
                    cur["kills"] = ev.get("kills", 0)
                    cur["time"] = ev.get("time", 0.0)
                    cur["reward"] = ev.get("reward_total", 0.0)
                    cur["outcome"] = ev.get("outcome", "")
                    cur["damage_taken"] = ev.get("damage_taken", 0)
                    cur["level"] = ev.get("level", 1)
                    cur["buff_count"] = ev.get("buff_count", buffs_in_ep)
                    cur["depth_max"] = max(
                        (SCENE_DEPTH.get(r, 0) for r in cur["rooms"]), default=0
                    )
                    cur["a2_reached"] = a2_reached
                    cur["waypoint_y350"] = waypoint_y350
                    cur["trigger_cross"] = trigger_cross
                    cur["unique_rooms"] = len(cur["rooms"])
                    eps.append(cur)
                    cur = None
    return eps


def metrics_for_run(eps: list) -> dict:
    n = len(eps)
    if n == 0:
        return {"episodes": 0}
    kills = [e["kills"] for e in eps]
    rewards = [e["reward"] for e in eps]
    depths = [e["depth_max"] for e in eps]
    rooms = [e["unique_rooms"] for e in eps]
    times = [e["time"] for e in eps]
    dmg = [e["damage_taken"] for e in eps]
    a2 = sum(1 for e in eps if e["a2_reached"])
    trig = sum(1 for e in eps if e["trigger_cross"])
    wp350 = sum(1 for e in eps if e["waypoint_y350"])
    buffs = sum(e["buff_count"] for e in eps)
    outcomes = Counter(e["outcome"] for e in eps)
    return {
        "episodes":          n,
        "avg_kills":         sum(kills) / n,
        "max_kills":         max(kills),
        "avg_reward":        sum(rewards) / n,
        "avg_depth":         sum(depths) / n,
        "max_depth":         max(depths),
        "avg_unique_rooms":  sum(rooms) / n,
        "avg_time_s":        sum(times) / n,
        "avg_dmg":           sum(dmg) / n,
        "pct_reach_A2_01":   100 * a2 / n,
        "pct_trigger_cross": 100 * trig / n,
        "pct_waypoint_y350": 100 * wp350 / n,
        "buffs_total":       buffs,
        "outcome_fail":      outcomes.get("fail", 0),
        "outcome_trunc":     outcomes.get("truncated_room", 0) + outcomes.get("truncated_global", 0),
        "outcome_win":       outcomes.get("win", 0),
    }


# rand order pentru tabel (label, key, fmt)
COLS = [
    ("Episoade",           "episodes",          "{:.0f}"),
    ("Avg kills/ep",       "avg_kills",         "{:.2f}"),
    ("Max kills",          "max_kills",         "{:.0f}"),
    ("Avg reward/ep",      "avg_reward",        "{:.1f}"),
    ("Avg depth",          "avg_depth",         "{:.2f}"),
    ("Max depth",          "max_depth",         "{:.0f}"),
    ("Avg camere unice",   "avg_unique_rooms",  "{:.2f}"),
    ("Avg timp (s)",       "avg_time_s",        "{:.1f}"),
    ("Avg dmg luat",       "avg_dmg",           "{:.1f}"),
    ("% A2/01 reach",      "pct_reach_A2_01",   "{:.2f}"),
    ("% trigger cross",    "pct_trigger_cross", "{:.2f}"),
    ("% waypoint y=-350",  "pct_waypoint_y350", "{:.2f}"),
    ("Buffs total",        "buffs_total",       "{:.0f}"),
    ("Outcome fail",       "outcome_fail",      "{:.0f}"),
    ("Outcome trunc",      "outcome_trunc",     "{:.0f}"),
    ("Outcome win",        "outcome_win",       "{:.0f}"),
]


def format_table(runs: list) -> str:
    # runs = [(label, metrics), ...]
    labels = [r[0] for r in runs]
    headers = ["Metrica"] + labels
    rows = []
    for col_label, key, fmt in COLS:
        row = [col_label]
        for _, m in runs:
            v = m.get(key, 0)
            row.append(fmt.format(v) if isinstance(v, (int, float)) else str(v))
        rows.append(row)

    widths = [max(len(r[i]) for r in [headers] + rows) for i in range(len(headers))]
    sep = "+".join("-" * (w + 2) for w in widths)
    out = []
    def fmt_row(r):
        return "| " + " | ".join(r[i].ljust(widths[i]) for i in range(len(r))) + " |"
    out.append(fmt_row(headers))
    out.append("|" + sep + "|")
    for r in rows:
        out.append(fmt_row(r))
    return "\n".join(out)


def write_csv(runs: list, path: str):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Metrica"] + [r[0] for r in runs])
        for col_label, key, _ in COLS:
            w.writerow([col_label] + [r[1].get(key, "") for r in runs])


def write_markdown(runs: list, path: str):
    labels = [r[0] for r in runs]
    lines = []
    lines.append("# Comparatie runuri\n")
    lines.append("| Metrica | " + " | ".join(labels) + " |")
    lines.append("|" + "---|" * (len(labels) + 1))
    for col_label, key, fmt in COLS:
        cells = [col_label]
        for _, m in runs:
            v = m.get(key, 0)
            cells.append(fmt.format(v) if isinstance(v, (int, float)) else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", nargs="+", default=None,
                        help="Liste label=path (ex: random=ai_events_random.jsonl)")
    args = parser.parse_args()

    if args.runs:
        pairs = []
        for x in args.runs:
            if "=" not in x:
                print(f"SKIP (lipseste '='): {x}"); continue
            label, path = x.split("=", 1)
            pairs.append((label, path))
    else:
        pairs = RUNS_DEFAULT

    runs = []
    for label, fname in pairs:
        path = fname if os.path.isabs(fname) else os.path.join(HERE, fname)
        if not os.path.exists(path):
            print(f"[skip] {label}: {path} nu exista")
            continue
        eps = load_episodes(path)
        m = metrics_for_run(eps)
        runs.append((label, m))
        print(f"[ok]   {label}: {m.get('episodes',0)} ep din {os.path.basename(path)}")

    if not runs:
        print("\nNICIUN run de comparat. Verifica fisierele ai_events_*.jsonl.")
        return

    print("\n" + format_table(runs))

    csv_path = os.path.join(OUT_DIR, "compare_runs.csv")
    md_path = os.path.join(OUT_DIR, "compare_runs.md")
    write_csv(runs, csv_path)
    write_markdown(runs, md_path)
    print(f"\nCSV     : {csv_path}")
    print(f"Markdown: {md_path}")


if __name__ == "__main__":
    main()
