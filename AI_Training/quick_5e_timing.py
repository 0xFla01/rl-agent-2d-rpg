"""Find WHEN the 5 A2/01 hits + buffs happened in run 5e."""
import json, os
EVENTS = os.path.join(os.environ["APPDATA"], "Godot", "app_userdata", "VERSIUNE FINALA", "ai_events.jsonl")

ep_idx = 0
in_ep = False
hit_a2 = False
hit_buff = 0
for line in open(EVENTS, encoding="utf-8"):
    ev = json.loads(line)
    e = ev.get("event")
    if e == "run_started":
        ep_idx += 1
        in_ep = True
        hit_a2 = False
        hit_buff = 0
    elif e == "room_entered" and ev.get("scene_path") == "res://Levels/Area02/01.tscn":
        hit_a2 = True
    elif e == "buff_picked":
        hit_buff += 1
    elif e == "episode_end":
        if hit_a2 or hit_buff:
            tags = []
            if hit_a2: tags.append("A2/01")
            if hit_buff: tags.append(f"BUFF x{hit_buff}")
            print(f"  ep {ep_idx:4d}: {', '.join(tags)} | kills={ev.get('kills',0)} outcome={ev.get('outcome')}")
        in_ep = False

print(f"\nTotal episodes scanned: {ep_idx}")
