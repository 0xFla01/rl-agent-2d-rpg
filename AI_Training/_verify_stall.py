# -*- coding: utf-8 -*-
"""Observator read-only: detecteaza pauze Python (actiune stale >0.5s) si verifica
daca jucatorul INGHEATA (cod nou) sau CONTINUA sa se miste (cod vechi)."""
import os, json, time
LIVE = os.path.join(os.environ["APPDATA"], "Godot", "app_userdata", "VERSIUNE FINALA")
ACT = os.path.join(LIVE, "ai_action.json"); ST = os.path.join(LIVE, "ai_state.json")
DUR = 200.0; THRESH = 0.5
def rd(p):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return None
samples = []
t_end = time.time() + DUR
while time.time() < t_end:
    a = rd(ACT); s = rd(ST); now = time.time()
    if a and s:
        age = now - float(a.get("t", now))
        p = s.get("player", {})
        samples.append((now, age, float(p.get("x", 0)), float(p.get("y", 0))))
    time.sleep(0.06)
# analiza: gaseste cea mai lunga fereastra cu age>THRESH
best = None; cur = None
for i,(t,age,x,y) in enumerate(samples):
    if age > THRESH:
        if cur is None: cur = [i,i]
        else: cur[1] = i
    else:
        if cur and (best is None or (cur[1]-cur[0])>(best[1]-best[0])): best = cur
        cur = None
if cur and (best is None or (cur[1]-cur[0])>(best[1]-best[0])): best = cur
max_age = max((s[1] for s in samples), default=0)
print(f"samples={len(samples)} | varsta_max_actiune={max_age:.2f}s (>0.5 = pauza Python detectata)")
if best:
    seg = samples[best[0]:best[1]+1]
    dur = seg[-1][0]-seg[0][0]
    xs=[s[2] for s in seg]; ys=[s[3] for s in seg]
    disp = max(((xs[k]-xs[0])**2+(ys[k]-ys[0])**2)**0.5 for k in range(len(seg)))
    print(f"PAUZA gasita: durata={dur:.2f}s, deplasare_jucator={disp:.1f}px in timpul pauzei")
    if disp < 8:
        print(">>> VERDICT: jucatorul a INGHETAT in timpul pauzei -> COD NOU ACTIV (fix merge) ✓")
    elif disp > 30:
        print(">>> VERDICT: jucatorul a CONTINUAT sa se miste -> cod vechi (fix NU e activ) ✗")
    else:
        print(f">>> VERDICT: deplasare mica/ambigua ({disp:.1f}px) — probabil idle, dar neclar")
else:
    print(">>> Nicio pauza >0.5s in fereastra — nu am prins un update PPO. Reruleaza mai lung.")
