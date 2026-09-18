import json,os,time,collections
base=os.path.join(os.environ['APPDATA'],'Godot','app_userdata','VERSIUNE FINALA')
ev=os.path.join(base,'ai_events.jsonl')
t_end=time.time()+240
while time.time()<t_end:
    spawns=collections.Counter()
    try:
        for l in open(ev,encoding='utf-8'):
            try: r=json.loads(l)
            except: continue
            if r.get('event')=='run_started':
                sp=r.get('spawn_scene','')
                if 'Area01/02' in sp: spawns['NATURAL']+=1
                elif 'Area02/01' in sp: spawns['A2/01']+=1
                elif 'Area02/02' in sp: spawns['A2/02']+=1
                else: spawns['?']+=1
    except: pass
    tot=sum(spawns.values())
    curric=spawns['A2/01']+spawns['A2/02']
    # iesi devreme daca avem destule episoade SAU am vazut curriculum
    if tot>=18 or curric>=3:
        break
    time.sleep(3)
print(f'run_started: {tot}')
for k in ('NATURAL','A2/01','A2/02','?'):
    if spawns[k]: print(f'  {k}: {spawns[k]} ({100*spawns[k]/max(tot,1):.0f}%)  [tinta: NATURAL~50 A2/01~30 A2/02~20]')
print('VERDICT:', f'CURRICULUM ACTIV ✓ ({curric}/{tot} adanc)' if curric>0 else f'PROBLEMA: {tot} ep toate naturale -> Godot N-A reincarcat curriculum (Reload Project + restart)')
