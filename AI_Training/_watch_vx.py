import json,os,time
base=os.path.join(os.environ['APPDATA'],'Godot','app_userdata','VERSIUNE FINALA')
sp=os.path.join(base,'ai_state.json')
t_end=time.time()+720; found=None; a103=False
while time.time()<t_end and not found:
    try: s=json.load(open(sp,encoding='utf-8'))
    except: time.sleep(0.05); continue
    if 'Area01/03' in s.get('scene_path',''): a103=True
    for k in ('trap_arrows','lich_projectiles','boss_orbs'):
        for e in s.get(k,[]):
            if 'vx' in e and (e.get('vx') or e.get('vy')):
                found=(k,e.get('vx'),e.get('vy')); break
        if found: break
    time.sleep(0.05)
if found:
    print(f'CONFIRMAT: viteze live in obs -> {found[0]} vx={found[1]:.0f} vy={found[2]:.0f}. Dodge fix ACTIV, Run7 valid. ✓')
else:
    print(f'In 12 min n-am prins proiectil cu viteza (a ajuns in A1/03: {a103}). Daca a103=True dar 0 vx -> exporter neîncarcat. Daca a103=False -> n-a ajuns destul.')
