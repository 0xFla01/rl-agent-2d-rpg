# -*- coding: utf-8 -*-
import json, os, time
base = os.path.join(os.environ['APPDATA'], 'Godot', 'app_userdata', 'VERSIUNE FINALA')
sp = os.path.join(base, 'ai_state.json')
t_end = time.time() + 300
hit = False
while time.time() < t_end and not hit:
    try:
        s = json.load(open(sp, encoding='utf-8'))
    except Exception:
        time.sleep(0.1); continue
    if 'Area02/02' in s.get('scene_path', ''):
        lc = s.get('levers_current', 0)
        lt = s.get('levers_total', 0)
        ne = s.get('nearest_exit', {})
        if lt > 0 and lc < lt:   # levere INCOMPLETE
            hit = True
            found = ne.get('found')
            print("IN A2/02, levere {}/{} (incomplete)".format(lc, lt))
            if not found:
                print("  nearest_exit.found = False -> SUPRIMAT OK (fix-ul merge)")
            else:
                print("  nearest_exit.found = True la ({:.0f},{:.0f}) -> fix-ul NU s-a aplicat".format(ne.get('x', 0), ne.get('y', 0)))
    time.sleep(0.1)
if not hit:
    print("n-am prins A2/02 cu levere incomplete in 5 min. Reincearca cand agentul e in A2/02.")
