"""
Antrenare PPO pentru Dark Wizard speedrun game — Run 6 (infrastructura imbunatatita).

Inainte de rulare:
  1. Deschide jocul in Godot si apasa Play (F5)
  2. In joc, apasa F2 ca sa activezi AI mode (time_scale 4x)
  3. Ruleaza: python train.py

IMBUNATATIRI fata de Run 5 (toate configurabile prin env vars, default-uri sigure):
  - GAMMA 0.99 -> 0.997 : orizont efectiv ~100 -> ~333 pasi. Recompensele de room-clear/exit
    se propaga inapoi pe trasee lungi; boss-ul devine vizibil din camerele anterioare.
  - VecNormalize(reward) : normalizeaza scala return-ului (0.05 .. 1000) -> value function
    stabil -> mai putina UITARE CATASTROFICA (problema #1 din toate runurile 5x).
    NU schimba structura relativa a reward-ului (doar rescaleaza) -> shaping-ul ramane valid.
  - Scaffolding PARALELISM (RUN6_N_ENVS) + FRAME-STACKING (RUN6_FRAME_STACK): OFF by default.
    Se activeaza cand partea Godot e pregatita (vezi README_run6.md).

Config prin env vars:
  RUN6_N_ENVS      (1)        instante paralele (necesita Godot per-instanta — vezi README_run6.md)
  RUN6_FRAME_STACK (1)        cate frame-uri stivuite (>1 da viteze implicite, dar FORTEAZA fresh)
  RUN6_GAMMA       (0.997)
  RUN6_ENT_COEF    (0.04)
  RUN6_NORM_REWARD (1)        normalizare reward (recomandat la run nou)
  RUN6_NORM_OBS    (0)        normalizare obs (obs e deja [-2,2] -> default off, safe la resume)
  RUN6_TOTAL_STEPS (2000000)
  RUN6_FRESH       (0)        1 = ignora checkpoint-urile, porneste din BC/scratch
  RUN6_CHECK_ENV   (0)        1 = ruleaza check_env (lent, necesita jocul pornit)
"""

import os
import glob

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import (
    DummyVecEnv, SubprocVecEnv, VecNormalize, VecFrameStack, VecMonitor,
)

from game_env import DarkWizardEnv

MODEL_DIR = "models"
LOG_DIR   = "logs"
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(LOG_DIR,   exist_ok=True)

# ── config din env vars ─────────────────────────────────────────────────────────
def _envf(name, default):  return float(os.environ.get(name, default))
def _envi(name, default):  return int(os.environ.get(name, default))
def _envb(name, default):  return os.environ.get(name, default) not in ("0", "", "false", "False")

N_ENVS      = _envi("RUN6_N_ENVS", 1)
FRAME_STACK = _envi("RUN6_FRAME_STACK", 1)
GAMMA       = _envf("RUN6_GAMMA", 0.997)        # Run6: 0.99 -> 0.997 (orizont lung)
ENT_COEF    = _envf("RUN6_ENT_COEF", 0.04)
NORM_REWARD = _envb("RUN6_NORM_REWARD", "1")
NORM_OBS    = _envb("RUN6_NORM_OBS", "0")
TOTAL_STEPS = _envi("RUN6_TOTAL_STEPS", 2_000_000)
FRESH       = _envb("RUN6_FRESH", "0")
CHECK_ENV   = _envb("RUN6_CHECK_ENV", "0")

# Baza pentru fisierele de IPC (ai_state/action/episode). Pentru paralelism, fiecare
# instanta primeste un dir propriu prin AI_STATE_DIR (vezi make_env + README_run6.md).
_AI_BASE = os.environ.get("AI_STATE_DIR") or os.path.join(
    os.environ["APPDATA"], "Godot", "app_userdata", "VERSIUNE FINALA")


def make_env(rank: int = 0):
    """Factory pentru un env. Pentru N_ENVS>1, fiecare instanta scrie/citeste in dir propriu."""
    def _init():
        if N_ENVS > 1:
            os.environ["AI_STATE_DIR"] = f"{_AI_BASE}_inst{rank}"
        return DarkWizardEnv()
    return _init


def _latest(pattern: str):
    """Cel mai recent fisier dupa mtime (nu dupa numar — checkpoint-urile reseteaza la 10000)."""
    files = glob.glob(os.path.join(MODEL_DIR, pattern))
    return max(files, key=os.path.getmtime) if files else None


def build():
    """Construieste (model, env, callback). Separat de learn() ca sa poata fi verificat fara joc."""
    # 1) vec env (Dummy single-process sau Subproc pentru paralelism real)
    if N_ENVS > 1:
        venv = SubprocVecEnv([make_env(i) for i in range(N_ENVS)])
    else:
        venv = DummyVecEnv([make_env(0)])

    # 2) frame stacking (viteze implicite pt dodge) — FORTEAZA fresh (schimba dim obs)
    if FRAME_STACK > 1:
        venv = VecFrameStack(venv, n_stack=FRAME_STACK)

    # VecMonitor: inregistreaza return-ul real per episod -> ep_rew_mean apare in tensorboard
    # (cu VecEnv, SB3 nu mai adauga Monitor automat). Inainte de VecNormalize = reward brut real.
    venv = VecMonitor(venv)

    incompatible = FRESH or FRAME_STACK > 1   # nu putem incarca modele 214-d peste obs stivuit
    latest_model = None if incompatible else _latest("ppo_darkwizard_*_steps.zip")
    bc_path      = os.path.join(MODEL_DIR, "bc_pretrained.zip")

    # 3) VecNormalize: incarca statisticile salvate daca reluam, altfel porneste curat
    vecnorm_pkl = None if incompatible else _latest("ppo_darkwizard_vecnormalize_*.pkl")
    if vecnorm_pkl:
        env = VecNormalize.load(vecnorm_pkl, venv)
        env.norm_reward, env.norm_obs = NORM_REWARD, NORM_OBS
        print(f"VecNormalize reluat din: {vecnorm_pkl}")
    else:
        env = VecNormalize(venv, norm_obs=NORM_OBS, norm_reward=NORM_REWARD,
                           clip_reward=10.0, gamma=GAMMA)
        if latest_model:
            print("ATENTIE: reiau un model FARA statistici VecNormalize salvate. "
                  "Scala reward se readapteaza din mers (poate destabiliza pe termen scurt). "
                  "Pentru beneficiu curat, ruleaza cu RUN6_FRESH=1 (run nou din BC).")

    custom = {"ent_coef": ENT_COEF, "gamma": GAMMA}
    model = None
    # incearca checkpoint, apoi BC; daca obs dim s-a schimbat (214->238 viteze) load-ul pica -> scratch
    candidates = [("checkpoint", latest_model)]
    if os.path.exists(bc_path) and FRAME_STACK == 1:
        candidates.append(("BC pretrained", bc_path))
    for src, path in candidates:
        if not path:
            continue
        try:
            model = PPO.load(path, env=env, tensorboard_log=LOG_DIR, custom_objects=custom)
            print(f"Pornesc din {src}: {path}")
            break
        except (ValueError, RuntimeError, AssertionError, KeyError) as e:
            print(f"  nu pot incarca {src} ({type(e).__name__}) — probabil obs dim schimbat. Trec mai departe.")
    if model is None:
        print(f"Pornesc de la ZERO (model nou, obs {env.observation_space.shape}).")
        model = PPO(
            "MlpPolicy", env, verbose=1,
            learning_rate=lambda pr: 3e-4 * (0.1 + 0.9 * pr),
            n_steps=2048, batch_size=64, n_epochs=10,
            gamma=GAMMA, gae_lambda=0.95, clip_range=0.2, ent_coef=ENT_COEF,
            tensorboard_log=LOG_DIR, policy_kwargs=dict(net_arch=[256, 256]),
        )

    # 4) checkpoint la fiecare 10k pasi — salveaza SI statisticile VecNormalize
    callback = CheckpointCallback(
        save_freq=max(10_000 // N_ENVS, 1),   # save_freq e per-env la VecEnv
        save_path=MODEL_DIR, name_prefix="ppo_darkwizard",
        save_vecnormalize=True,
    )
    return model, env, callback


def main():
    if CHECK_ENV:
        from stable_baselines3.common.env_checker import check_env
        print("Verificare environment (necesita jocul pornit)...")
        check_env(DarkWizardEnv(), warn=True)
        print("Environment OK.\n")

    print(f"Config Run6: N_ENVS={N_ENVS} FRAME_STACK={FRAME_STACK} GAMMA={GAMMA} "
          f"ENT_COEF={ENT_COEF} NORM_REWARD={NORM_REWARD} NORM_OBS={NORM_OBS} FRESH={FRESH}")
    model, env, callback = build()

    print(f"Incep antrenarea ({TOTAL_STEPS} pasi). Tensorboard: tensorboard --logdir {LOG_DIR}\n")
    model.learn(total_timesteps=TOTAL_STEPS, callback=callback,
                progress_bar=True, reset_num_timesteps=True)

    model.save(os.path.join(MODEL_DIR, "ppo_darkwizard_final"))
    env.save(os.path.join(MODEL_DIR, "ppo_darkwizard_vecnormalize_final.pkl"))
    print("\nAntrenare terminata. Model salvat in:", MODEL_DIR)
    env.close()


if __name__ == "__main__":
    main()
