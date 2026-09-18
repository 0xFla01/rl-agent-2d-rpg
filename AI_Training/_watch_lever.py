import json,os,time
base=os.path.join(os.environ['APPDATA'],'Godot','app_userdata','VERSIUNE FINALA')
sp=os.path.join(base,'ai_state.json')
t_end=time.time()+300; hit=False
while time.time()<t_end and not hit:
    try: s=json.load(open(sp,encoding='utf-8'))
    except: time.sleep(0.1); continue
    if 'Area02/02' in s.get('scene_path',''):
        lc=s.get('levers_current',0); lt=s.get('levers_total',0)
        ne=s.get('nearest_exit',{})
        if lt>0 and lc<lt:  # levere INCOMPLETE
            hit=True
            print(f'IN A2/02, levere {lc}/{lt} (incomplete)')
            print(f'  nearest_exit.found = {ne.get(\"found\")}  ', end='')
            if not ne.get('found'):
                print('-> SUPRIMAT ✓ (fix-ul merge, nu-l mai trage jos)')
            else:
                print(f'-> INCA found la ({ne.get(\"x\",0):.0f},{ne.get(\"y\",0):.0f}) — fix-ul NU s-a aplicat (Godot n-a reincarcat exporterul?)')
    time.sleep(0.1)
if not hit:
    print('n-am prins A2/02 cu levere incomplete in 5 min (agentul n-a fost acolo). Reincearca cand e in A2/02.')
