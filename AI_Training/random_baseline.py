"""
Random baseline pentru comparatie cu PPO+BC.

Ruleaza acelasi environment ca train.py dar genereaza actiuni random uniform
peste action_space. Folositor pentru a arata in lucrare ca PPO+BC e fundamentat
statistic mai bun decat random, nu doar noroc.

Modes:
  --policy uniform   actiuni complet uniforme (toate butoanele 50% per frame) [DEFAULT]
  --policy realistic direction uniform; attack/dash/ability/interact rar (~5%/step)
                     (mai aproape de "jucator care apasa la intamplare")

La final, fisierele de log sunt arhivate automat:
  positions.jsonl  -> positions_<label>.jsonl
  ai_events.jsonl  -> ai_events_<label>.jsonl  (din user:// AppData)
  apoi originalele sunt truncate (gata pt urmatorul run).

Inainte de rulare:
  1. Deschide jocul in Godot, F5 (Play), F2 (AI mode ON)
  2. python random_baseline.py [--episodes N] [--policy realistic] [--label random]
"""

import argparse
import os
import shutil
import sys
import time

import numpy as np

# Permite import game_env din acelasi director
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game_env import DarkWizardEnv  # noqa: E402


HERE = os.path.dirname(os.path.abspath(__file__))
POSITIONS_LOCAL = os.path.join(HERE, "positions.jsonl")
GODOT_USERDATA = os.path.join(
    os.environ.get("APPDATA", ""),
    "Godot", "app_userdata", "VERSIUNE FINALA",
)
AI_EVENTS_USER = os.path.join(GODOT_USERDATA, "ai_events.jsonl")
# Flag care forteaza spawn natural (A1/02) — global_ai_controller.gd il verifica
# in get_curriculum_spawn() si bypass-uieaza CURRICULUM_SPAWNS cat timp exista.
BASELINE_FLAG = os.path.join(GODOT_USERDATA, "baseline_mode.flag")


def _sample_realistic(action_space, rng) -> np.ndarray:
    """Direction uniforma; restul rar (~5%) — mai aproape de baseline 'om confuz'."""
    # MultiDiscrete [9, 2, 2, 2, 2, 2] = [direction(9), interact, ability, dash, attack, extra]
    nvec = action_space.nvec
    a = np.zeros(len(nvec), dtype=np.int64)
    a[0] = rng.integers(0, nvec[0])  # direction uniform
    # restul binare: 5% sa fie 1
    for i in range(1, len(nvec)):
        a[i] = 1 if rng.random() < 0.05 else 0
    return a


def _archive_logs(label: str):
    """Copy positions.jsonl + ai_events.jsonl la nume _<label> si truncate originalele."""
    out_pos = os.path.join(HERE, f"positions_{label}.jsonl")
    out_evt = os.path.join(HERE, f"ai_events_{label}.jsonl")

    archived = []
    if os.path.exists(POSITIONS_LOCAL) and os.path.getsize(POSITIONS_LOCAL) > 0:
        shutil.copy(POSITIONS_LOCAL, out_pos)
        open(POSITIONS_LOCAL, "w", encoding="utf-8").close()
        archived.append(out_pos)
    if os.path.exists(AI_EVENTS_USER) and os.path.getsize(AI_EVENTS_USER) > 0:
        shutil.copy(AI_EVENTS_USER, out_evt)
        open(AI_EVENTS_USER, "w", encoding="utf-8").close()
        archived.append(out_evt)
    return archived


def run_random_baseline(num_episodes: int, max_steps_per_ep: int, policy: str, label: str, seed: int):
    # Forteaza spawn natural (A1/02) prin flag — global_ai_controller.gd bypass curriculum.
    try:
        open(BASELINE_FLAG, "w", encoding="utf-8").close()
        print(f"[random_baseline] flag creat: {BASELINE_FLAG}  (curriculum dezactivat pe durata)", flush=True)
    except Exception as e:
        print(f"[random_baseline] WARN: nu am putut crea flag-ul ({e})", flush=True)

    env = DarkWizardEnv()
    rng = np.random.default_rng(seed)
    print(f"[random_baseline] policy={policy}  label={label}  seed={seed}", flush=True)
    print(f"[random_baseline] action_space: {env.action_space}", flush=True)
    print(f"[random_baseline] obs_space.shape: {env.observation_space.shape}", flush=True)
    print(f"[random_baseline] target: {num_episodes} episoade, max {max_steps_per_ep} pasi/ep\n", flush=True)

    total_reward = 0.0
    t_start = time.time()

    try:
        for ep in range(num_episodes):
            obs, _ = env.reset()
            ep_reward = 0.0
            steps = 0
            done = False
            truncated = False
            while not (done or truncated) and steps < max_steps_per_ep:
                if policy == "uniform":
                    action = env.action_space.sample()
                else:
                    action = _sample_realistic(env.action_space, rng)
                obs, reward, done, truncated, _ = env.step(action)
                ep_reward += reward
                steps += 1
            total_reward += ep_reward
            elapsed = time.time() - t_start
            avg = total_reward / (ep + 1)
            print(f"[ep {ep+1:4d}/{num_episodes}]  steps={steps:4d}  rw={ep_reward:8.1f}  "
                  f"done={done}  trunc={truncated}  (avg rw/ep={avg:7.1f}, t={elapsed:.0f}s)", flush=True)
    finally:
        env.close()
        # Curata flag-ul indiferent de cum se termina (Ctrl+C, exceptie, end normal)
        try:
            if os.path.exists(BASELINE_FLAG):
                os.remove(BASELINE_FLAG)
                print(f"[random_baseline] flag sters: {BASELINE_FLAG}", flush=True)
        except Exception as e:
            print(f"[random_baseline] WARN: nu am putut sterge flag-ul ({e})", flush=True)

    print(f"\n[random_baseline] DONE — {num_episodes} ep, avg reward {total_reward/num_episodes:.1f}", flush=True)

    archived = _archive_logs(label)
    if archived:
        print(f"[random_baseline] arhivat:")
        for p in archived:
            print(f"   {p}")
        print("[random_baseline] positions.jsonl + ai_events.jsonl truncate (gata pt urmatorul run).")
    else:
        print("[random_baseline] WARN: nimic de arhivat (fisierele de log erau goale).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", "-n", type=int, default=50,
                        help="Numar de episoade (default 50)")
    parser.add_argument("--max-steps", type=int, default=3000,
                        help="Max steps per episode (default 3000)")
    parser.add_argument("--policy", choices=["uniform", "realistic"], default="uniform",
                        help="Politica random: uniform (default) sau realistic")
    parser.add_argument("--label", type=str, default=None,
                        help="Suffix pentru arhivare (default = policy name, ex: positions_uniform.jsonl)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    label = args.label or args.policy
    run_random_baseline(args.episodes, args.max_steps, args.policy, label, args.seed)
