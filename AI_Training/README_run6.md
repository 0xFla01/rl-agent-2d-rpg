# Run 6 — îmbunătățiri de infrastructură (02.06.2026)

Diagnostic real (din date, nu din narațiunea lucrării):
- Agentul **moare în A1/03** (2480 morți), nu „nu trece de tranziție". Farmează combat ~76s
  și moare din daune acumulate (capcane+inamici) pe care **nu le poate evita**.
- Sistem **subantrenat**: ~85ms/pas, 1 instanță → cel mai bun run a ajuns la **450k din 2M** pași.
- **Fără info de viteză** în obs (doar poziții) → dodge imposibil de învățat.
- **Fără normalizare reward** + gamma mic → uitare catastrofică (problema #1 a tuturor runurilor).

## ✅ Aplicat acum (sigur, verificat fără joc) — `train.py` + `game_env.py`

| Schimbare | Efect | Cum |
|---|---|---|
| `gamma` 0.99 → **0.997** | orizont 100 → 333 pași (room-clear/exit se propagă înapoi) | `RUN6_GAMMA` |
| **VecNormalize(reward)** | normalizează scala return-ului → value function stabil → mai puțină uitare | `RUN6_NORM_REWARD=1` |
| Salvare/încărcare statistici VecNormalize | checkpoint complet (model + normalizare) | automat |
| `STEP_WAIT` + dir IPC configurabile | enabler pentru pas mai rapid și paralelism | `AI_STEP_WAIT`, `AI_STATE_DIR` |

Backup-uri: `train.py.bak_run5`, `game_env.py.bak_run5`. Default fără env vars = **identic cu Run 5**.

### Cum pornești Run 6 (recomandat: run nou din BC ca să profite curat de normalizare)
```powershell
# Godot: F5 (Play) apoi F2 (AI mode)
$env:RUN6_FRESH="1"; python train.py
```
`RUN6_FRESH=1` pornește din BC cu normalizare curată. Fără el, reia ultimul checkpoint
(merge, dar scala reward se readaptează din mers — vezi avertismentul din log).

---

## ⚠️ NECESITĂ jocul pornit ca să testăm împreună (NU le-am aplicat orb)

### 1. Pas de acțiune mai rapid (160ms în loc de 320ms → dodge POSIBIL + 2× viteză)
**De ce nu l-am aplicat orb:** `Engine.time_scale = 4.0` (controller linia 95) + `EXPORT_INTERVAL = 0.08`
(exporter linia 14) sunt **cuplate fin** la fps-ul real al jocului. Dacă înjumătățesc orbește, exporturile
pot depăși citirile Python → recompense (kills/milestones) scrise apoi suprascrise înainte de a fi citite.

**De testat împreună:** schimbă AMBELE și verifică în `step_timing.jsonl` că `state_valid` rămâne true și
că `ai_events.jsonl` are același raport milestone/kill:
- Godot `global_ai_state_exporter.gd` L14: `const EXPORT_INTERVAL := 0.04`
- Godot `global_ai_controller.gd` L42: `const DEMO_INTERVAL := 0.04`
- Python: `$env:AI_STEP_WAIT="0.04"`

### 2. Frame-stacking (viteze implicite pt dodge) — câștig mare, dar FORȚEAZĂ fresh
```powershell
$env:RUN6_FRAME_STACK="3"; python train.py   # obs 214 → 642, pornește din scratch
```
Alternativă mai curată (mai puțini parametri): exportă `vx,vy` pentru proiectile/inamici direct în
`global_ai_state_exporter.gd` și adaugă-le în `_state_to_obs`. Ambele schimbă dim obs → run nou.

### 3. Paralelism (4-6 instanțe → ~8h pt 2M, GRATIS pe cele 12 threads ale tale)
```powershell
$env:RUN6_N_ENVS="4"; python train.py
```
`train.py` e deja pregătit (`SubprocVecEnv` + `AI_STATE_DIR` per-instanță). **Lipsește partea Godot:**
fiecare instanță trebuie să scrie/citească în dir propriu. Godot folosește `user://` fix per proiect →
trebuie lansate 4 instanțe headless cu user-dir diferit:
```powershell
# pentru fiecare i in 0..3 (necesită un build/export al proiectului):
godot --headless --path "C:\LICENTA FINALA\Fla18\Licenta" --user-data-dir "..._inst$i"
```
Asta cere un export Linux/headless + verificare că `user://` se redirectează corect → **sesiune comună**.

---

## Ordinea recomandată
1. Rulează **Run 6 cum e acum** (gamma+normalizare, `RUN6_FRESH=1`) — vezi dacă morțile din A1/03 scad și dacă reward-ul nu mai colapsează (forgetting).
2. Dacă e stabil → adaugă **frame-stacking** (`RUN6_FRAME_STACK=3`) pentru dodge real.
3. Apoi **pas 40ms** + **paralelism** (sesiune cu jocul pornit) ca să ajungi efectiv la 2M pași.
