"""Tabel comparativ summary pentru toate runs arhivate."""
import json
import os
import csv

RUNS = {
    "5g":       "ai_events_run5g.jsonl",
    "5h_pilot": "ai_events_run5h_pilot.jsonl",
    "5h_v2":    "ai_events_run5h_v2.jsonl",
    "5j_post":  "ai_events_run5j_postshop_corrupt.jsonl",
    "5f":       "ai_events_run5f.jsonl",
}

A201 = "res://Levels/Area02/01.tscn"
A202 = "res://Levels/Area02/02.tscn"
A103 = "res://Levels/Area01/03.tscn"
SHOP = "res://Levels/Area01/02_shop.tscn"
A104 = "res://Levels/Area01/04.tscn"
D02  = "res://Levels/Dungeon01/02.tscn"
D03  = "res://Levels/Dungeon01/03.tscn"
D04  = "res://Levels/Dungeon01/04.tscn"

def load_eps(path):
    eps = []
    if not os.path.exists(path): return eps
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try: ev = json.loads(line)
            except: continue
            if ev.get("event") == "episode_end" and ev.get("max_hp"):
                eps.append(ev)
    return eps

def stats(eps):
    if not eps: return None
    n = len(eps)
    return {
        "ep_total": n,
        "kills_avg": round(sum(e.get("kills",0) for e in eps)/n, 2),
        "time_avg": round(sum(e.get("time",0) for e in eps)/n, 1),
        "reward_avg": round(sum(e.get("reward_total",0) for e in eps)/n, 1),
        "buffs_total": sum(e.get("buff_count",0) for e in eps),
        "a103_reach": sum(1 for e in eps if A103 in e.get("rooms_visited",[])),
        "a201_total": sum(1 for e in eps if A201 in e.get("rooms_visited",[])),
        "a201_spawn": sum(1 for e in eps if e.get("rooms_visited",[]) and e.get("rooms_visited",[])[0] == A201),
        "a201_natural": sum(1 for e in eps if A201 in e.get("rooms_visited",[]) and e.get("rooms_visited",[])[0] != A201),
        "a202": sum(1 for e in eps if A202 in e.get("rooms_visited",[])),
        "shop": sum(1 for e in eps if SHOP in e.get("rooms_visited",[])),
        "dungeon": sum(1 for e in eps if any(x in e.get("rooms_visited",[]) for x in [D02,D03,D04])),
        "boss_reached": sum(1 for e in eps if e.get("boss_reached")),
    }

results = {}
for name, path in RUNS.items():
    s = stats(load_eps(path))
    if s:
        results[name] = s
    else:
        print(f"  {name}: no data ({path})")

# Print tabel
print("\n" + "="*100)
print(f"{'Run':<10} | {'Ep':>5} | {'Kills':>6} | {'Time':>6} | {'A1/03':>6} | {'A2/01 nat':>9} | {'A2/02':>5} | {'Shop':>4} | {'Boss':>4}")
print("-"*100)
order = ["5f", "5g", "5h_pilot", "5h_v2", "5j_post"]
for name in order:
    if name not in results: continue
    r = results[name]
    pct_a103 = 100*r['a103_reach']/r['ep_total']
    pct_a201nat = 100*r['a201_natural']/r['ep_total']
    print(f"{name:<10} | {r['ep_total']:>5} | {r['kills_avg']:>6.2f} | {r['time_avg']:>6.1f} | "
          f"{r['a103_reach']:>3} ({pct_a103:>4.1f}%) | "
          f"{r['a201_natural']:>3} ({pct_a201nat:>4.1f}%) | "
          f"{r['a202']:>5} | {r['shop']:>4} | {r['boss_reached']:>4}")
print("="*100)

# Save CSV
csv_path = "results_v4/runs_summary_table.csv"
os.makedirs("results_v4", exist_ok=True)
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["run", "ep_total", "kills_avg", "time_avg", "reward_avg", "buffs_total",
                "a103_reach", "a201_total", "a201_spawn", "a201_natural",
                "a202", "shop", "dungeon", "boss_reached"])
    for name in order:
        if name not in results: continue
        r = results[name]
        w.writerow([name, r['ep_total'], r['kills_avg'], r['time_avg'], r['reward_avg'],
                    r['buffs_total'], r['a103_reach'], r['a201_total'], r['a201_spawn'],
                    r['a201_natural'], r['a202'], r['shop'], r['dungeon'], r['boss_reached']])
print(f"\nSaved CSV: {csv_path}")
