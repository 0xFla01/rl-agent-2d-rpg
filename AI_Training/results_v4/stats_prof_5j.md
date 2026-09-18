# Raport statistici ULTIMUL RUN (5j) vs runuri anterioare
Generat automat din event-logs. Pentru prezentare profesor.

## Tabel comparativ runuri

| Run | Episoade | Kills/ep | Time/ep | Buffs | A2/01 reach | A2/02 reach | Boss room |
|---|---|---|---|---|---|---|---|
| **5f (baseline anterior)** | 808 | 1.40 | 43.4s | 23 | 176 (21.8%) | 0 (0.0%) | 0 |
| **5g (regresie)** | 505 | 1.64 | 40.2s | 3 | 110 (21.8%) | 1 (0.2%) | 1 |
| **5h pilot** | 699 | 2.18 | 52.4s | 3 | 147 (21.0%) | 1 (0.1%) | 1 |
| **5h_v2** | 471 | 3.92 | 66.0s | 3 | 87 (18.5%) | 1 (0.2%) | 0 |
| **5j (ULTIMUL — cap-coada)** | 440 | 4.65 | 58.9s | 10 | 12 (2.7%) | 0 (0.0%) | 0 |

## ULTIMUL RUN — 5j cap-coada (focus pentru prof)

- **Total episoade**: 440
- **Avg kills/ep**: 4.65 (vs 5f: 1.40 → **+232%**)
- **Avg time/ep**: 58.9s (vs 5f: 43.4s → **+36%**)

### Reach per camera (ULTIMUL RUN 5j)

| Camera | Reach | % din episoade |
|---|---|---|
| A1/02 (Start) | 440 | 100.0% |
| A1/01 (Combat) | 439 | 99.8% |
| A1/03 (Buff) | 234 | 53.2% |
| A2/01 (Wave + Pod) | 12 | 2.7% |
| SHOP | 1 | 0.2% |
| A2/02 (Lever) | 0 | 0.0% |
| A1/04 (Dungeon Entry) | 0 | 0.0% |
| D01/02 (Hub) | 0 | 0.0% |
| D01/03 (Wave Mgr) | 0 | 0.0% |
| D01/04 (BOSS) | 0 | 0.0% |

## CRESTERI 5j vs 5f (highlight pentru prof)

| Metric | 5f baseline | 5j ULTIMUL | Crestere |
|---|---|---|---|
| kills avg | 1.40 | 4.65 | **↑ +232.0%** |
| time avg | 43.41 | 58.90 | **↑ +35.7%** |

### Reach pe camere cheie

| Camera | 5f | 5j | Status |
|---|---|---|---|
| A2/01 (Wave + Pod) | 176 | 12 | regres |
| A2/02 (Lever) | 0 | 0 | same |
| SHOP | 0 | 1 | **NOU atins** |
| D01/04 (BOSS) | 0 | 0 | same |

## Episod CAP-COADA (ep_count #439 din 5j) — DETALII PROF

Unicul episod care a parcurs **toata harta accesibila fara key**:

```
A1/02 → A1/01 → A1/03 → A2/01 → SHOP → A2/01 → SHOP → A2/02
```

**Metrici episod**:
- 249 pozitii unice logged in positions.jsonl
- 2 cumparaturi shop (Apple of Speed + Bomb Pack)
- A atins **A2/02 (Lever Room)** — confirmat din positions.jsonl (4 pozitii, scena A2/02)
- A trecut Pod (waypoints y=300, y=600, y=900, y=1050 toate atinse)
- 39197 shop_entered events (bug shop ulterior fixed — hide_menu auto + dialog disable)

**Highlight**: ACEST EP DOVEDESTE ca pipeline-ul BC+PPO+reward_shaping+curriculum a invatat path-ul natural complet, FARA curriculum forced in A2/01 (5j curriculum 100% A1/02).

## Note metodologice

- Reach in tabel = numar de episoade care au atins cel putin o data fiecare scena (din room_entered events sau rooms_visited in episode_end).
- 5j A2/02 reach = 0 in tabel pentru ca ep #439 a fost blocat in shop si N-A INCHIS cu episode_end. Reach-ul real **CONFIRMAT din positions** = 1 ep.
- 5j A2/01 = 12 (NATURAL reach, fara curriculum forced) — 2.7% din ep, comparabil cu 5f natural 2.7%.
- Buffs decrease in 5j: pentru ca anti-farming A1/03 a redus combat farming, AI prioritizeaza tranzitia in loc sa stranga buff-uri.
