import os, json, time
base = os.path.join(os.environ['APPDATA'],'Godot','app_userdata','VERSIUNE FINALA')
ACT=os.path.join(base,'ai_action.json'); ST=os.path.join(base,'ai_state.json')
def rd(p):
    try: return json.load(open(p,encoding='utf-8'))
    except: return None
DUR=210; samples=[]; vx_seen=False; vx_example=None; scenes=set()
t_end=time.time()+DUR
while time.time()<t_end:
    a=rd(ACT); s=rd(ST); now=time.time()
    if a and s:
        age=now-float(a.get('t',now))
        p=s.get('player',{})
        samples.append((now,age,float(p.get('x',0)),float(p.get('y',0))))
        scenes.add(s.get('scene_path','?'))
        for k in ('trap_arrows','lich_projectiles','boss_orbs'):
            for e in s.get(k,[]):
                if 'vx' in e:
                    vx_seen=True
                    if vx_example is None: vx_example=(k,e.get('vx'),e.get('vy'))
    time.sleep(0.06)
# stall window
best=None;cur=None
for i,(t,age,x,y) in enumerate(samples):
    if age>0.5:
        cur=[i,i] if cur is None else [cur[0],i]
    else:
        if cur and (best is None or cur[1]-cur[0]>best[1]-best[0]): best=cur
        cur=None
if cur and (best is None or cur[1]-cur[0]>best[1]-best[0]): best=cur
print('=== VERIFICARE RUN 7 ===')
print('scene vizitate:', sorted(s.split('/')[-1] for s in scenes))
print('VITEZE in obs (exporter reincarcat?):', 'DA, vx live '+str(vx_example) if vx_seen else 'inca n-am vazut proiectile cu vx (n-a ajuns in A1/03 cu sageti active)')
if best:
    seg=samples[best[0]:best[1]+1]; dur=seg[-1][0]-seg[0][0]
    disp=max(((seg[k][2]-seg[0][2])**2+(seg[k][3]-seg[0][3])**2)**0.5 for k in range(len(seg)))
    print(f'STALL: pauza {dur:.2f}s, deplasare {disp:.1f}px -> ' + ('INGHETAT, cod nou ✓' if disp<8 else ('fuga, cod vechi ✗' if disp>30 else 'ambiguu')))
else:
    print('STALL: nicio pauza >0.5s prinsa in fereastra')
