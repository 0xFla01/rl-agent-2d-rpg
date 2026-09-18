"""Analiza finala run 5k complet (865 ep) — statistici per quarter + salvare CSV.
Pentru PPT: comparatie 5k_v2 memoria (598 ep) vs 5k_final (865 ep).
"""
import json
import csv
import os
from collections import defaultdict

POS_FILE = "positions.jsonl"
OUT_DIR = "results_v4"
os.makedirs(OUT_DIR, exist_ok=True)

SCENES = {
    "res://Levels/Area01/02.tscn": "A1/02",
    "res://Levels/Area01/01.tscn": "A1/01",
    "res://Levels/Area01/03.tscn": "A1/03",
    "res://Levels/Area02/01.tscn": "A2/01",
    "res://Levels/Area02/02.tscn": "A2/02",
    "res://Levels/Area02/SHOP.tscn": "SHOP",
    "res://Levels/Dungeon01/01.tscn": "D01/01",
    "res://Levels/Dungeon01/02.tscn": "D01/02",
    "res://Levels/Dungeon01/03.tscn": "D01/03",
    "res://Levels/Dungeon01/04.tscn": "D01/04",
}

# Trigger y in A1/03 (din state_exporter.gd): y=-490
A103_TRIGGER_Y = -490

ep_scenes = defaultdict(set)              # ep -> {scene1, scene2, ...}
ep_a103_min_y = {}                        # ep -> minim y in A1/03 (cel mai nord)
ep_a201_samples = defaultdict(int)        # ep -> count samples in A2/01
ep_a202_samples = defaultdict(int)        # ep -> count samples in A2/02

with open(POS_FILE, "r") as f:
    for line in f:
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        ep = d["episode"]
        scene = d["scene"]
        y = d["y"]
        short = SCENES.get(scene, scene)
        ep_scenes[ep].add(short)
        if scene.endswith("Area01/03.tscn"):
            ep_a103_min_y[ep] = min(ep_a103_min_y.get(ep, 99999), y)
        if scene.endswith("Area02/01.tscn"):
            ep_a201_samples[ep] += 1
        if scene.endswith("Area02/02.tscn"):
            ep_a202_samples[ep] += 1

all_eps = sorted(ep_scenes.keys())
n_eps = len(all_eps)
print(f"Total unique episodes with positions: {n_eps}")
print(f"Last episode number: {max(all_eps)}")

# Imparte in 5 quarters de 173 ep (865/5)
TOTAL = max(all_eps) + 1
Q_SIZE = TOTAL // 5

quarters = []
for i in range(5):
    start = i * Q_SIZE
    end = (i + 1) * Q_SIZE if i < 4 else TOTAL
    qeps = [e for e in all_eps if start <= e < end]
    if not qeps:
        continue
    # Metrics
    n = len(qeps)
    reach_a102 = sum(1 for e in qeps if "A1/02" in ep_scenes[e])
    reach_a101 = sum(1 for e in qeps if "A1/01" in ep_scenes[e])
    reach_a103 = sum(1 for e in qeps if "A1/03" in ep_scenes[e])
    reach_a201 = sum(1 for e in qeps if "A2/01" in ep_scenes[e])
    reach_a202 = sum(1 for e in qeps if "A2/02" in ep_scenes[e])
    reach_shop = sum(1 for e in qeps if "SHOP" in ep_scenes[e])
    # Trigger A1/03: ep cu min_y < -490
    trigger_a103 = sum(1 for e in qeps if ep_a103_min_y.get(e, 99999) < A103_TRIGGER_Y)
    # A2/01 natural = ep care AU ajuns A2/01 SI NU AU trecut prin shop intai
    a201_nat = sum(1 for e in qeps if "A2/01" in ep_scenes[e] and "SHOP" not in ep_scenes[e])
    quarters.append({
        "Q": f"Q{i+1}",
        "ep_range": f"{start}-{end-1}",
        "n_eps_with_pos": n,
        "A1/02": reach_a102,
        "A1/01": reach_a101,
        "A1/03": reach_a103,
        "A2/01": reach_a201,
        "A2/01_nat": a201_nat,
        "A2/02": reach_a202,
        "SHOP": reach_shop,
        "trigger_A1/03": trigger_a103,
        "trigger_pct": f"{trigger_a103/n*100:.1f}%" if n else "0%",
        "A2/01_nat_pct": f"{a201_nat/n*100:.2f}%" if n else "0%",
    })

# Print tabel
print("\n=== STATISTICI PER QUARTER (165-173 ep/quarter) ===")
print(f"{'Q':3} {'range':10} {'n':4} {'A1/01':6} {'A1/03':6} {'trig':6} {'A2/01nat':9} {'A2/02':6}")
for q in quarters:
    print(f"{q['Q']:3} {q['ep_range']:10} {q['n_eps_with_pos']:4} {q['A1/01']:6} {q['A1/03']:6} {q['trigger_A1/03']:6} {q['A2/01_nat']:9} {q['A2/02']:6}")

# TOTAL
total = {
    "n": n_eps,
    "A1/03": sum(1 for e in all_eps if "A1/03" in ep_scenes[e]),
    "A2/01": sum(1 for e in all_eps if "A2/01" in ep_scenes[e]),
    "A2/01_nat": sum(1 for e in all_eps if "A2/01" in ep_scenes[e] and "SHOP" not in ep_scenes[e]),
    "A2/02": sum(1 for e in all_eps if "A2/02" in ep_scenes[e]),
    "trigger_A1/03": sum(1 for e in all_eps if ep_a103_min_y.get(e, 99999) < A103_TRIGGER_Y),
    "SHOP": sum(1 for e in all_eps if "SHOP" in ep_scenes[e]),
}
print(f"\n=== TOTAL RUN 5K (865 ep, {n_eps} cu pozitii) ===")
for k, v in total.items():
    pct = f" ({v/n_eps*100:.2f}%)" if k != "n" else ""
    print(f"  {k}: {v}{pct}")

# A2/02 ep details
print("\n=== EPISOADE CARE AU ATINS A2/02 ===")
a202_eps = [e for e in all_eps if "A2/02" in ep_scenes[e]]
for e in a202_eps:
    print(f"  ep {e}: {ep_a202_samples[e]} samples, traseu = {sorted(ep_scenes[e])}")

# Salvez CSV
csv_path = os.path.join(OUT_DIR, "run5k_final_quarters.csv")
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(quarters[0].keys()))
    w.writeheader()
    for q in quarters:
        w.writerow(q)
print(f"\n[saved] {csv_path}")

# Salvez summary JSON
summary_path = os.path.join(OUT_DIR, "run5k_final_summary.json")
with open(summary_path, "w") as f:
    json.dump({
        "run": "5k_final",
        "n_episodes_total": max(all_eps) + 1,
        "n_episodes_with_positions": n_eps,
        "last_write": "2026-05-22 03:32",
        "quarters": quarters,
        "totals": total,
        "a202_episodes": [{"ep": e, "samples": ep_a202_samples[e], "scenes": sorted(ep_scenes[e])} for e in a202_eps],
    }, f, indent=2)
print(f"[saved] {summary_path}")
