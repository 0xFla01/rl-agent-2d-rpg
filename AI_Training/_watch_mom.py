import json, os, time
base = os.path.join(os.environ['APPDATA'], 'Godot', 'app_userdata', 'VERSIUNE FINALA')
sp = os.path.join(base, 'ai_state.json')
prev = None
t_end = time.time() + 110
log = []
while time.time() < t_end:
    try:
        s = json.load(open(sp, encoding='utf-8'))
    except Exception:
        time.sleep(0.2); continue
    b = s.get('buffs', {})
    snap = (round(float(s.get('timer', 0)), 0), s.get('scene_path','').split('/')[-1],
            b.get('momentum_active'), b.get('momentum_stacks'), b.get('kill_stack_active'))
    if snap != prev:
        log.append(snap); prev = snap
    time.sleep(0.3)
print("timer | scena | mom_active | mom_stacks | kill_active")
for t, sc, ma, ms, ka in log[-25:]:
    print(f"  {t:7.0f} | {sc:12} | mom={ma} st={ms} | kill={ka}")
