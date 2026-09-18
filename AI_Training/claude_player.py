"""
Claude joaca Dark Wizard via Anthropic API — baseline LLM zero-shot.

Citeste ai_state.json (state complet de la global_ai_state_exporter.gd),
formateaza ca prompt natural, cere Claude actiune, scrie via env.step (MultiDiscrete).
System prompt e cached (~90% reducere cost de la al 2-lea apel).

Inainte de rulare:
  1. Setezi ANTHROPIC_API_KEY in env (PowerShell: $env:ANTHROPIC_API_KEY = "sk-ant-...")
  2. Godot deschis cu F5 (Play), F2 (AI mode ON)
  3. python claude_player.py [-n EPISODES] [--model opus|sonnet|haiku] [--max-steps N]

La final arhiveaza positions/ai_events in *_claude_<model>.jsonl. Curriculum spawn
e dezactivat automat (Claude porneste din A1/02 natural, ca random_baseline).

Pricing rough (~500 tok in cu cache + ~80 tok out per call):
  opus   (4.7): ~$0.005/call → 500 calls ≈ $2.50
  sonnet (4.6): ~$0.003/call → 500 calls ≈ $1.50
  haiku  (4.5): ~$0.001/call → 500 calls ≈ $0.50
"""

import argparse
import json
import os
import shutil
import sys
import time

import anthropic
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game_env import DarkWizardEnv  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
GODOT_USERDATA = os.path.join(
    os.environ.get("APPDATA", ""),
    "Godot", "app_userdata", "VERSIUNE FINALA",
)
STATE_FILE = os.path.join(GODOT_USERDATA, "ai_state.json")
ACTION_FILE = os.path.join(GODOT_USERDATA, "ai_action.json")
EVENTS_FILE = os.path.join(GODOT_USERDATA, "ai_events.jsonl")
POSITIONS_LOCAL = os.path.join(HERE, "positions.jsonl")
BASELINE_FLAG = os.path.join(GODOT_USERDATA, "baseline_mode.flag")


def write_idle_action():
    """Freeze player. Folosit intre env.step si Claude API call,
    ca player-ul sa nu continue actiunea anterioara timp de 1.5s real (6s game)."""
    payload = {
        "move_x": 0.0, "move_y": 0.0,
        "attack": False, "dash": False, "interact": False,
        "ability": False, "switch_ability": False,
        "reset": False, "reset_reason": "",
    }
    tmp = ACTION_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(payload, f)
        os.replace(tmp, ACTION_FILE)
    except Exception:
        pass

MODELS = {
    "opus":   "claude-opus-4-7",
    "sonnet": "claude-sonnet-4-6",
    "haiku":  "claude-haiku-4-5",
}

SYSTEM_PROMPT = """Joci Dark Wizard. Output: doar JSON, niciun text suplimentar.
FORMAT: {"direction":N,"interact":N,"ability":N,"dash":N,"attack":N,"switch_ability":N}

DIRECTII (single-axis, FARA diagonale): 0=idle, 1=N(y scade), 2=S(y creste), 3=W(x scade), 4=E(x creste). NU folosesti 5,6,7,8.

Te misti ~80px per turn. NPC interact range ≈ 40px.

ALGORITM (in ordine):

1. Daca scene = "Area01/02" SI quest_started = false:
   TINTA = NPC. NPC interact area e MICA (~6px radius) — trebuie sa intri IN el, nu langa.
   STRATEGIE: **MEARGA spre NPC SI apasa interact in acelasi timp** (in caz ca o atingi in trecere).
   - Daca |npc.dy| > |npc.dx|:
     - npc.dy < 0 → direction=1 (N), npc.dy > 0 → direction=2 (S)
   - Altfel:
     - npc.dx < 0 → direction=3 (W), npc.dx > 0 → direction=4 (E)
   - **interact=1 INTOTDEAUNA** in pasul asta (spam ok, NPC nu se sperie)
   Restul (ability, dash, attack, switch_ability) = 0.
   STOP — nu treci la pasul urmator.

2. Daca enemies nu e gol (combat):
   e = enemies[0]. dist_e = sqrt(e.dx² + e.dy²).
   - dist_e < 50: attack=1 + direction calculata catre e (single-axis ca mai sus).
   - dist_e >= 50: doar mergi spre e (attack=0).
   - hp < 5: dash=1 si mergi OPUS (semn invers).

3. Navigation:
   - scene = "Area01/02" SI quest_started=true: direction=1
   - scene = "Area01/01": daca enemies non-empty → vezi pas 2, altfel direction=1
   - scene = "Area01/03": direction=1
   - nearest_exit setat: mergi spre el (single-axis)
   - default: direction=1

NU spam interact in afara A1/02 fara quest. NU diagonale."""


def compact_state(state: dict) -> dict:
    """Reduce state-ul de la 214 floats la ce e relevant pentru Claude (~500 tokens)."""
    p = state.get("player", {})
    out = {
        "scene": state.get("scene_path", "?").replace("res://Levels/", "").replace(".tscn", ""),
        "player": {
            "x": round(p.get("x", 0), 1),
            "y": round(p.get("y", 0), 1),
            "hp": p.get("hp", 0),
            "max_hp": p.get("max_hp", 12),
            "facing": [round(p.get("facing_x", 0), 1), round(p.get("facing_y", 0), 1)],
        },
        "timer": round(state.get("timer", 0), 1),
        "in_dialog": state.get("in_dialog", False),
        "quest_started": state.get("quest_started", False),
        "kills_in_room": state.get("kills_in_room", 0),
        "kill_target": state.get("kill_target", 0),
        "gems": state.get("gems", 0),
    }

    enemies = state.get("enemies", [])
    if enemies:
        # top 3 cele mai apropiate
        def dist(e):
            return ((e.get("x", 0) - p.get("x", 0)) ** 2 +
                    (e.get("y", 0) - p.get("y", 0)) ** 2) ** 0.5
        top = sorted(enemies, key=dist)[:3]
        out["enemies"] = [
            {
                "dx": round(e.get("x", 0) - p.get("x", 0), 1),
                "dy": round(e.get("y", 0) - p.get("y", 0), 1),
                "hp": e.get("hp", 0),
                "type": e.get("type", "?"),
            }
            for e in top
        ]
    else:
        out["enemies"] = []

    ne = state.get("nearest_exit", {})
    if ne.get("found"):
        # ne.x/y sunt ABSOLUTE — convertesc la delta fata de player
        out["nearest_exit"] = {"dx": round(ne["x"] - p.get("x", 0), 1),
                               "dy": round(ne["y"] - p.get("y", 0), 1)}

    npc = state.get("npc_pos", {})
    if npc.get("found"):
        out["npc"] = {"dx": round(npc["x"] - p.get("x", 0), 1),
                      "dy": round(npc["y"] - p.get("y", 0), 1)}

    chests = state.get("item_chests", []) or state.get("available_chests", [])
    if chests:
        out["chest_nearby"] = True

    buffs = state.get("buffs", {})
    active = buffs.get("active_buff_ids", [])
    if active:
        out["active_buffs"] = active

    boss_hp = state.get("boss_hp", -1)
    if boss_hp > 0:
        out["boss_hp"] = boss_hp
        out["boss_phase"] = state.get("boss_phase", 0)

    return out


def parse_action(text: str) -> np.ndarray:
    """Extrage JSON din raspuns Claude, fallback la idle pe orice eroare.
    Ordinea trebuie sa fie EXACT cea din game_env._decode_action:
      [direction, attack, dash, ability, interact, switch_ability]
    """
    text = text.strip()
    s = text.find("{")
    e = text.rfind("}")
    if s < 0 or e <= s:
        return np.array([0, 0, 0, 0, 0, 0], dtype=np.int64)
    try:
        a = json.loads(text[s:e + 1])
        return np.array([
            max(0, min(8, int(a.get("direction", 0)))),
            1 if a.get("attack") else 0,
            1 if a.get("dash") else 0,
            1 if a.get("ability") else 0,
            1 if a.get("interact") else 0,
            1 if a.get("switch_ability") else 0,
        ], dtype=np.int64)
    except Exception:
        return np.array([0, 0, 0, 0, 0, 0], dtype=np.int64)


def archive_logs(label: str):
    out_pos = os.path.join(HERE, f"positions_{label}.jsonl")
    out_evt = os.path.join(HERE, f"ai_events_{label}.jsonl")
    archived = []
    if os.path.exists(POSITIONS_LOCAL) and os.path.getsize(POSITIONS_LOCAL) > 0:
        shutil.copy(POSITIONS_LOCAL, out_pos)
        open(POSITIONS_LOCAL, "w", encoding="utf-8").close()
        archived.append(out_pos)
    if os.path.exists(EVENTS_FILE) and os.path.getsize(EVENTS_FILE) > 0:
        shutil.copy(EVENTS_FILE, out_evt)
        open(EVENTS_FILE, "w", encoding="utf-8").close()
        archived.append(out_evt)
    return archived


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", "-n", type=int, default=10,
                        help="Numar episoade (default 10 — Claude costa bani)")
    parser.add_argument("--model", choices=list(MODELS), default="opus",
                        help="Model Claude (default opus = claude-opus-4-7)")
    parser.add_argument("--label", type=str, default=None)
    parser.add_argument("--max-steps", type=int, default=200,
                        help="Step cap per ep (default 200 → ~200 API calls/ep)")
    parser.add_argument("--max-cost", type=float, default=4.0,
                        help="Buget MAX in dolari (default $4). Scriptul se opreste daca depaseste.")
    parser.add_argument("--dry-run", action="store_true",
                        help="1 apel test fara joc (verifica API + parse)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("EROARE: ANTHROPIC_API_KEY nu e setat.", file=sys.stderr)
        print('  PowerShell: $env:ANTHROPIC_API_KEY = "sk-ant-..."', file=sys.stderr)
        sys.exit(1)

    label = args.label or f"claude_{args.model}"
    model_id = MODELS[args.model]
    client = anthropic.Anthropic()

    # Dry-run: doar test API + parse
    if args.dry_run:
        print(f"[dry-run] model={model_id}", flush=True)
        test_state = {
            "scene": "Area01/02", "player": {"x": 360, "y": 180, "hp": 12, "max_hp": 12, "facing": [1, 0]},
            "timer": 0, "kills_in_room": 0, "enemies": [], "npc": {"dx": -180, "dy": -10},
        }
        resp = client.messages.create(
            model=model_id, max_tokens=150,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": f"State: {json.dumps(test_state)}\n\nActiune (JSON):"}],
        )
        txt = next((b.text for b in resp.content if b.type == "text"), "")
        print(f"[dry-run] response:\n{txt}", flush=True)
        action = parse_action(txt)
        print(f"[dry-run] parsed: {action.tolist()}", flush=True)
        print(f"[dry-run] usage: in={resp.usage.input_tokens} out={resp.usage.output_tokens} "
              f"cache_create={resp.usage.cache_creation_input_tokens} cache_read={resp.usage.cache_read_input_tokens}",
              flush=True)
        return

    # Flag pentru spawn natural A1/02 (la fel ca random_baseline)
    try:
        open(BASELINE_FLAG, "w").close()
        print(f"[claude_player] flag baseline_mode creat", flush=True)
    except Exception as e:
        print(f"[claude_player] WARN flag: {e}", flush=True)

    env = DarkWizardEnv()
    print(f"[claude_player] model={model_id}  episodes={args.episodes}  max_steps={args.max_steps}  max_cost=${args.max_cost:.2f}", flush=True)

    total_calls = 0
    total_in = total_out = total_cache_read = total_cache_create = 0
    t_start = time.time()
    # Tarif aici ca sa-l folosim si in loop pentru cost cap
    prices = {  # (input/1M, output/1M, cache_read/1M, cache_write/1M)
        "claude-opus-4-7":   (5.00, 25.00, 0.50, 6.25),
        "claude-sonnet-4-6": (3.00, 15.00, 0.30, 3.75),
        "claude-haiku-4-5":  (1.00,  5.00, 0.10, 1.25),
    }[model_id]
    def current_cost():
        return (total_in * prices[0] + total_out * prices[1]
                + total_cache_read * prices[2] + total_cache_create * prices[3]) / 1_000_000

    try:
        for ep in range(args.episodes):
            ep_start = time.time()
            obs, _ = env.reset()
            steps = 0
            done = False
            truncated = False
            initial_scene_seen = False  # track first non-start scene to detect respawn

            while not (done or truncated) and steps < args.max_steps:
                # Cost cap GLOBAL — opreste totul daca depaseste bugetul
                cost_now = current_cost()
                if cost_now >= args.max_cost:
                    print(f"  [COST CAP] ${cost_now:.2f} >= ${args.max_cost:.2f} — opresc.", flush=True)
                    raise KeyboardInterrupt

                # Citeste state complet din fisier (game_env.obs e doar 214 floats normalized)
                try:
                    with open(STATE_FILE, "r", encoding="utf-8") as f:
                        state = json.load(f)
                except Exception:
                    state = {}

                # Daca state e gol (Godot freeze / file lock) → skip API call (eviti waste)
                if not state or not state.get("player"):
                    print(f"  [skip] state gol — idle, fara API call", flush=True)
                    action = np.array([0, 0, 0, 0, 0, 0], dtype=np.int64)
                    obs, reward, done, truncated, _ = env.step(action)
                    steps += 1
                    continue

                state_compact = compact_state(state)

                # Apel Claude (system cached)
                try:
                    resp = client.messages.create(
                        model=model_id, max_tokens=120,
                        system=[{"type": "text", "text": SYSTEM_PROMPT,
                                 "cache_control": {"type": "ephemeral"}}],
                        messages=[{"role": "user",
                                   "content": f"State: {json.dumps(state_compact, separators=(',', ':'))}\n\nActiune (JSON):"}],
                    )
                    total_calls += 1
                    total_in += resp.usage.input_tokens
                    total_out += resp.usage.output_tokens
                    total_cache_read += resp.usage.cache_read_input_tokens
                    total_cache_create += resp.usage.cache_creation_input_tokens
                except anthropic.RateLimitError:
                    print("  [rate limit] sleep 30s...", flush=True)
                    time.sleep(30)
                    continue
                except Exception as e:
                    print(f"  [api error]: {e} — idle action", flush=True)
                    action = np.array([0, 0, 0, 0, 0, 0], dtype=np.int64)
                else:
                    txt = next((b.text for b in resp.content if b.type == "text"), "")
                    action = parse_action(txt)

                obs, reward, done, truncated, _ = env.step(action)
                steps += 1

                # Detectie death/respawn — Godot done flag rateaza in race condition.
                try:
                    with open(STATE_FILE, "r", encoding="utf-8") as f:
                        s_check = json.load(f)
                    p_check = s_check.get("player", {})
                    scene_check = s_check.get("scene_path", "")
                    hp_now = p_check.get("hp", 0)
                    max_hp = p_check.get("max_hp", 12)
                    # (a) Death imediat: HP <= 0
                    if hp_now <= 0 and not done:
                        print(f"  [death detect] HP=0 step={steps} — opresc ep", flush=True)
                        done = True
                    # (b) Respawn dupa death: HP=max in A1/02 dupa ce am vazut alta scena
                    elif (steps > 5 and not done and
                          scene_check == "res://Levels/Area01/02.tscn" and
                          hp_now == max_hp and initial_scene_seen):
                        print(f"  [respawn detect] step={steps} — opresc ep", flush=True)
                        done = True
                    elif scene_check and scene_check != "res://Levels/Area01/02.tscn":
                        initial_scene_seen = True
                except Exception:
                    pass

                # Lasa actiunea sa propage 0.2s real (~0.8s game = ~80px miscare)
                time.sleep(0.2)
                # Freeze player cat timp Claude gandeste next turn (eviti overshoot)
                write_idle_action()

                if steps % 2 == 0 or done:
                    print(f"  [ep {ep+1} step {steps}] act={action.tolist()} hp={p_check.get('hp','?')} "
                          f"scene={scene_check.split('/')[-1].replace('.tscn','') if scene_check else '?'} "
                          f"done={done} cost=${current_cost():.3f}", flush=True)

            ep_elapsed = time.time() - ep_start
            print(f"[ep {ep+1}/{args.episodes}] DONE: {steps} steps, {ep_elapsed:.1f}s real, "
                  f"calls={total_calls}, cost=${current_cost():.3f}", flush=True)

    finally:
        env.close()
        try:
            if os.path.exists(BASELINE_FLAG):
                os.remove(BASELINE_FLAG)
                print(f"[claude_player] flag sters", flush=True)
        except Exception:
            pass

        archived = archive_logs(label)
        if archived:
            print(f"[claude_player] arhivat:")
            for p in archived:
                print(f"  {p}", flush=True)

        # Cost final
        cost = (total_in * prices[0] + total_out * prices[1]
                + total_cache_read * prices[2] + total_cache_create * prices[3]) / 1_000_000

        print(f"\n[claude_player] SUMMARY ({time.time() - t_start:.1f}s):")
        print(f"  calls: {total_calls}")
        print(f"  tokens: in={total_in}  out={total_out}  cache_read={total_cache_read}  cache_create={total_cache_create}")
        print(f"  cost estimate: ${cost:.3f}")


if __name__ == "__main__":
    main()
