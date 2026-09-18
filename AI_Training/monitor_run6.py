# -*- coding: utf-8 -*-
"""
Monitor live pentru Run 6 — citeste ai_events.jsonl (scris de joc) si scoate:
  - Funnel (reach rate per camera) — global + ultimele N episoade
  - Unde MOR episoadele (distributie + outcome) — focus A1/03
  - Detector FORGETTING (reach A1/03 / A2/01 pe ferestre de timp)
  - Trend reward real (din tensorboard, daca exista)

Ruleaza:  python monitor_run6.py            (o singura data)
          python monitor_run6.py --watch 60 (reimprospateaza la 60s)
"""
import os, json, sys, glob, time, collections, statistics as stt

EVENTS = os.environ.get("AI_EVENTS") or os.path.join(
    os.environ["APPDATA"], "Godot", "app_userdata", "VERSIUNE FINALA", "ai_events.jsonl")

# camera -> (adancime cap-coada, nume scurt)
ROOM = {
    "res://Levels/Area01/02.tscn":     (1, "Start A1/02"),
    "res://Levels/Area01/01.tscn":     (2, "A1/01 goblini"),
    "res://Levels/Area01/03.tscn":     (3, "A1/03 BUFF"),
    "res://Levels/Area02/01.tscn":     (4, "A2/01 VALURI"),
    "res://Levels/Area01/02_shop.tscn":(5, "Shop"),
    "res://Levels/Area02/02.tscn":     (6, "A2/02 levere"),
    "res://Levels/Area01/04.tscn":     (7, "A1/04 entry"),
    "res://Levels/Dungeon01/01.tscn":  (8, "D01 dungeon"),
    "res://Levels/Dungeon01/02.tscn":  (9, "D01/02 hub"),
    "res://Levels/Dungeon01/03.tscn":  (10, "D01/03 wave"),
    "res://Levels/Dungeon01/04.tscn":  (11, "D01/04 BOSS"),
}
ORDER = [k for k, _ in sorted(ROOM.items(), key=lambda kv: kv[1][0])]


def parse_episodes(path):
    """Imparte event log-ul in episoade (intre run_started). Fiecare = rooms vizitate + final."""
    eps, cur = [], None
    if not os.path.exists(path):
        return eps
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            e = r.get("event")
            if e == "run_started":
                if cur is not None:
                    eps.append(cur)
                sp = r.get("spawn_scene", "") or "res://Levels/Area01/02.tscn"
                cur = {"rooms": set(), "outcome": None, "kills": 0, "time": 0.0,
                       "dmg": 0.0, "end": None, "spawn": sp,
                       "natural": "Area01/02" in sp}
            if cur is None:
                continue
            if e in ("room_entered", "milestone_room"):
                sp = r.get("scene_path", "")
                if sp in ROOM:
                    cur["rooms"].add(sp)
            elif e == "episode_end":
                cur["outcome"] = r.get("outcome", "?")
                cur["kills"] = r.get("kills", 0)
                cur["time"] = float(r.get("time", 0) or 0)
                cur["dmg"] = float(r.get("damage_taken", 0) or 0)
                cur["end"] = r.get("scene_path", "")
    if cur is not None:
        eps.append(cur)
    return eps


def depth(ep):
    return max((ROOM[s][0] for s in ep["rooms"]), default=0)


def funnel(eps, label):
    n = len(eps)
    if n == 0:
        print(f"  [{label}] 0 episoade"); return
    reach = collections.Counter()
    for ep in eps:
        for s in ep["rooms"]:
            reach[s] += 1
    print(f"  [{label}] N={n}")
    for s in ORDER:
        c = reach.get(s, 0)
        if c == 0 and ROOM[s][0] > 8:
            continue
        bar = "#" * int(40 * c / n)
        print(f"    {ROOM[s][1]:14} {100*c/n:5.1f}%  {c:5}  {bar}")


def deaths(eps):
    by = collections.defaultdict(lambda: collections.Counter())
    extra = collections.defaultdict(lambda: {"k": [], "t": [], "d": []})
    for ep in eps:
        room = ROOM.get(ep["end"], (0, ep["end"] or "?"))[1]
        by[room][ep["outcome"] or "?"] += 1
        extra[room]["k"].append(ep["kills"]); extra[room]["t"].append(ep["time"])
        extra[room]["d"].append(ep["dmg"])
    print("  Unde se TERMINA episoadele (outcome | avg kills/time/dmg):")
    rows = sorted(by.items(), key=lambda kv: -sum(kv[1].values()))
    for room, oc in rows:
        k = extra[room]["k"]; t = extra[room]["t"]; d = extra[room]["d"]
        am = lambda x: round(stt.mean(x), 1) if x else 0
        print(f"    {room:14} {dict(oc)} | k={am(k)} t={am(t)}s dmg={am(d)}")


def forgetting(eps, nwin=4):
    n = len(eps)
    if n < nwin * 5:
        print("  (prea putine episoade pt analiza ferestre)"); return
    win = n // nwin
    print(f"  Reach rate pe {nwin} ferestre (cate ~{win} ep) — SCADERE = forgetting:")
    keys = ["res://Levels/Area01/03.tscn", "res://Levels/Area02/01.tscn",
            "res://Levels/Area02/02.tscn"]
    hdr = "    fereastra  " + "".join(f"{ROOM[k][1]:>14}" for k in keys) + "   avg_depth"
    print(hdr)
    for w in range(nwin):
        seg = eps[w*win:(w+1)*win] if w < nwin-1 else eps[w*win:]
        if not seg:
            continue
        rates = []
        for k in keys:
            c = sum(1 for ep in seg if k in ep["rooms"])
            rates.append(f"{100*c/len(seg):12.1f}%")
        ad = stt.mean([depth(ep) for ep in seg])
        print(f"    W{w+1} (n={len(seg):4}) " + "".join(rates) + f"   {ad:8.2f}")


def reward_trend():
    try:
        from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
        dirs = glob.glob(os.path.join(os.path.dirname(__file__) or ".", "logs", "PPO_*"))
        if not dirs:
            return
        # foloseste folderul RUNULUI CURENT = cel mai mare numar PPO_N (nu cadea pe runuri vechi!)
        def _num(d):
            try: return int(os.path.basename(d).split("_")[1])
            except Exception: return -1
        latest = max(dirs, key=_num)
        ea = EventAccumulator(latest); ea.Reload()
        sc = ea.Scalars("rollout/ep_rew_mean") if "rollout/ep_rew_mean" in ea.Tags().get("scalars", []) else []
        if not sc:
            print(f"  (runul curent {os.path.basename(latest)}: inca fara reward — asteapta primul rollout la 2048 pasi)"); return
        vals = [s.value for s in sc]
        print(f"  ep_rew_mean ({os.path.basename(latest)}): start={vals[0]:.0f} "
              f"min={min(vals):.0f} max={max(vals):.0f} acum={vals[-1]:.0f}")
        tail = vals[-6:]
        print("    ultimele 6 rollout-uri:", [round(v) for v in tail])
        if len(vals) > 4 and vals[-1] < 0.55 * max(vals):
            print("    !! ALERTA: reward-ul a scazut >45% fata de peak -> posibil forgetting")
    except Exception as e:
        print(f"  (tensorboard indisponibil: {e})")


def report():
    eps = parse_episodes(EVENTS)
    print("=" * 64)
    print(f"MONITOR Run6 | {time.strftime('%H:%M:%S')} | episoade: {len(eps)}")
    print(f"  events: {EVENTS}")
    print("=" * 64)
    nat = [e for e in eps if e.get("natural")]
    cur_eps = [e for e in eps if not e.get("natural")]
    print(f"\n[1] FUNNEL  (natural: {len(nat)} | curriculum-spawn: {len(cur_eps)})")
    funnel(eps, "TOT (incl. spawn)")
    if nat:
        funnel(nat, "DOAR NATURAL")          # transferul real — ce conteaza
        if len(nat) > 150:
            funnel(nat[-150:], "natural ult.150")
    if cur_eps:
        funnel(cur_eps, "doar curriculum-spawn")  # cat de bine CLEAR-uieste camerele spawnate
    print("\n[2] MORTI / TERMINARI")
    deaths(eps)
    print("\n[3] FORGETTING (ferestre temporale)")
    forgetting(eps)
    print("\n[4] REWARD REAL (tensorboard)")
    reward_trend()
    print()


def main():
    watch = 0
    if "--watch" in sys.argv:
        i = sys.argv.index("--watch")
        watch = int(sys.argv[i+1]) if i+1 < len(sys.argv) else 60
    if watch:
        while True:
            os.system("cls" if os.name == "nt" else "clear")
            report()
            print(f"(refresh la {watch}s — Ctrl+C pt stop)")
            time.sleep(watch)
    else:
        report()


if __name__ == "__main__":
    main()
