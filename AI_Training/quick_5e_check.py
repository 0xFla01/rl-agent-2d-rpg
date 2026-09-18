"""Quick check Run 5e: spawn distribution + max depth + truncate stats."""
import json, os
from collections import Counter, defaultdict

EVENTS = os.path.join(
    os.environ["APPDATA"],
    "Godot", "app_userdata", "VERSIUNE FINALA", "ai_events.jsonl"
)

SCENE_DEPTH = {
    "res://Levels/Area01/02.tscn": 1,
    "res://Levels/Area01/01.tscn": 2,
    "res://Levels/Area01/03.tscn": 3,
    "res://Levels/Area02/01.tscn": 4,
    "res://Levels/Area02/02.tscn": 5,
    "res://Levels/Area01/04.tscn": 6,
    "res://Levels/Dungeon01/02.tscn": 7,
    "res://Levels/Dungeon01/03.tscn": 8,
    "res://Levels/Dungeon01/04.tscn": 9,
}
DEPTH_NAME = {1:"A1/02", 2:"A1/01", 3:"A1/03", 4:"A2/01", 5:"A2/02",
              6:"A1/04", 7:"D01/02", 8:"D01/03", 9:"D01/04"}

episodes = []
cur = None
for line in open(EVENTS, encoding="utf-8"):
    ev = json.loads(line)
    e = ev.get("event")
    if e == "run_started":
        cur = {
            "spawn": ev.get("spawn_scene"),
            "rooms": set(),
            "ts_start": ev.get("timestamp"),
            "kills": 0,
            "outcome": None,
            "time": None,
            "trunc": False,
            "buffs": [],
            "waypoints": [],
            "trigger_crossed": False,
        }
    elif cur is not None:
        if e == "room_entered":
            cur["rooms"].add(ev.get("scene_path"))
        elif e == "waypoint_y350":
            cur["waypoints"].append("y350")
        elif e == "trigger_line_crossed":
            cur["trigger_crossed"] = True
        elif e == "buff_picked":
            cur["buffs"].append(ev.get("buff", "?"))
        elif e == "episode_end":
            cur["outcome"] = ev.get("outcome")
            cur["kills"] = ev.get("kills", 0)
            cur["time"] = ev.get("time", 0)
            cur["buff_count"] = ev.get("buff_count", 0)
            cur["max_depth"] = max((SCENE_DEPTH.get(r, 0) for r in cur["rooms"]), default=0)
            episodes.append(cur)
            cur = None

n = len(episodes)
print(f"Episode total: {n}\n")

# spawn distribution
spawn_dist = Counter(DEPTH_NAME.get(SCENE_DEPTH.get(e["spawn"], 0), "?") for e in episodes)
print("SPAWN DISTRIBUTION:")
for k, v in sorted(spawn_dist.items(), key=lambda x: -x[1]):
    print(f"  {k:8s}: {v:4d} ({100*v/n:.1f}%)")

# max depth
depth_counter = Counter(e["max_depth"] for e in episodes)
print("\nMAX DEPTH REACHED:")
for d in sorted(depth_counter):
    name = DEPTH_NAME.get(d, "?")
    cnt = depth_counter[d]
    print(f"  depth {d} ({name:8s}): {cnt:4d} ({100*cnt/n:.1f}%)")

# A2/01 reach
reached_a2 = sum(1 for e in episodes if e["max_depth"] >= 4)
print(f"\nA2/01 reached: {reached_a2}/{n} ({100*reached_a2/n:.2f}%) — TARGET >10%")

# trigger line + waypoints
trig = sum(1 for e in episodes if e["trigger_crossed"])
wp350 = sum(1 for e in episodes if "y350" in e["waypoints"])
print(f"\nA1/03 progress: trigger_crossed={trig} ({100*trig/n:.1f}%), waypoint_y350={wp350} ({100*wp350/n:.1f}%)")

# kills
total_kills = sum(e["kills"] for e in episodes)
avg_kills = total_kills / n if n else 0
print(f"\nKills: total={total_kills}, avg/ep={avg_kills:.3f}")

# buffs
total_buffs = sum(e["buff_count"] for e in episodes)
print(f"Buffs picked: {total_buffs}")

# outcomes
outcomes = Counter(e["outcome"] for e in episodes)
print(f"\nOutcomes: {dict(outcomes)}")

# last 100 ep window
last = episodes[-100:] if n >= 100 else episodes
last_depth = Counter(e["max_depth"] for e in last)
last_a2 = sum(1 for e in last if e["max_depth"] >= 4)
print(f"\nLAST {len(last)} EPISODES (recent trend):")
print(f"  A2/01: {last_a2} ({100*last_a2/len(last):.1f}%)")
print(f"  avg kills: {sum(e['kills'] for e in last)/len(last):.3f}")
print(f"  buffs: {sum(e['buff_count'] for e in last)}")
for d in sorted(last_depth):
    print(f"  depth {d} ({DEPTH_NAME.get(d,'?'):8s}): {last_depth[d]}")

# A1/02 truncation proxy: ended in A1/02 only with time near limit
a102_only = [e for e in episodes if e["max_depth"] == 1]
print(f"\nA1/02-only episodes: {len(a102_only)} ({100*len(a102_only)/n:.1f}%)")
if a102_only:
    times = [e["time"] for e in a102_only]
    print(f"  time min/avg/max: {min(times):.1f} / {sum(times)/len(times):.1f} / {max(times):.1f} s")
