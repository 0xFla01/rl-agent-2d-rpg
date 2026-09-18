"""
Behavior Cloning pretraining pentru Dark Wizard.

Citeste demo-urile umane (user://demos/session_*.jsonl), le converteste in
(obs, action) pairs si antreneaza policy-ul PPO supervised cu cross-entropy.
Salveaza modelul ca `models/bc_pretrained.zip` care poate fi incarcat de train.py.

Run: python bc_pretrain.py
  (Godot NU trebuie sa ruleze — datele sunt pe disk)
"""

import os
import glob
import json
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from stable_baselines3 import PPO

from game_env import DarkWizardEnv, DIRECTIONS

DEMO_DIR = os.path.join(
    os.environ["APPDATA"], "Godot", "app_userdata", "VERSIUNE FINALA", "demos"
)
MODEL_DIR = "models"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

EPOCHS = 30
BATCH_SIZE = 256
LR = 3e-4
VAL_SPLIT = 0.1
WEIGHT_CAP = 20.0   # cap per-class weight, evita overfit pe clase ultra-rare


def encode_direction(mx: float, my: float) -> int:
    best_i, best_d = 0, 1e9
    for i, (dx, dy) in enumerate(DIRECTIONS):
        d = (dx - mx) ** 2 + (dy - my) ** 2
        if d < best_d:
            best_d = d
            best_i = i
    return best_i


def load_demos():
    env = DarkWizardEnv()
    obs_list, act_list = [], []
    files = sorted(glob.glob(os.path.join(DEMO_DIR, "session_*.jsonl")))
    if not files:
        raise RuntimeError(f"No demo files found in {DEMO_DIR}")
    print(f"Loading {len(files)} demo sessions from {DEMO_DIR}\n")

    for f in files:
        count, skipped = 0, 0
        with open(f, "r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    skipped += 1
                    continue
                state = rec.get("state", {})
                action = rec.get("action", {})
                if not state or "player" not in state:
                    skipped += 1
                    continue
                try:
                    obs = env._state_to_obs(state)
                except Exception:
                    skipped += 1
                    continue
                dir_idx = encode_direction(
                    float(action.get("move_x", 0.0)),
                    float(action.get("move_y", 0.0)),
                )
                act_vec = [
                    dir_idx,
                    int(bool(action.get("attack", False))),
                    int(bool(action.get("dash", False))),
                    int(bool(action.get("ability", False))),
                    int(bool(action.get("interact", False))),
                    int(bool(action.get("switch_ability", False))),
                ]
                obs_list.append(obs)
                act_list.append(act_vec)
                count += 1
        print(f"  {os.path.basename(f)}: {count} steps ({skipped} skipped)")

    env.close()
    return (
        np.asarray(obs_list, dtype=np.float32),
        np.asarray(act_list, dtype=np.int64),
    )


class DemoDataset(Dataset):
    def __init__(self, obs, actions):
        self.obs = torch.from_numpy(obs)
        self.actions = torch.from_numpy(actions)

    def __len__(self):
        return len(self.obs)

    def __getitem__(self, idx):
        return self.obs[idx], self.actions[idx]


def build_fresh_ppo(env):
    return PPO(
        "MlpPolicy",
        env,
        learning_rate=lambda pr: 3e-4 * (0.1 + 0.9 * pr),
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.10,
        policy_kwargs=dict(net_arch=[256, 256]),
        device=DEVICE,
        verbose=0,
    )


def forward_dist(policy, obs):
    """Forward obs through PPO policy, return MultiCategoricalDistribution."""
    features = policy.extract_features(obs)
    if policy.share_features_extractor:
        latent_pi, _latent_vf = policy.mlp_extractor(features)
    else:
        pi_features, _ = features
        latent_pi = policy.mlp_extractor.forward_actor(pi_features)
    return policy._get_action_dist_from_latent(latent_pi)


def compute_class_weights(actions: np.ndarray) -> list:
    """Returneaza weight tensor per head bazat pe inverse-frequency cu cap."""
    head_sizes = [9, 2, 2, 2, 2, 2]
    weights = []
    n = len(actions)
    for i, k in enumerate(head_sizes):
        counts = np.bincount(actions[:, i], minlength=k).astype(np.float32)
        # avoid div by 0: classes never seen → weight = WEIGHT_CAP
        freqs = counts / max(n, 1)
        w = np.where(counts > 0, 1.0 / np.maximum(freqs, 1e-6), WEIGHT_CAP * 100.0)
        # normalizeaza astfel incat weight-ul minim = 1.0
        w = w / w.min()
        w = np.minimum(w, WEIGHT_CAP)
        weights.append(torch.tensor(w, dtype=torch.float32, device=DEVICE))
    return weights


def epoch_pass(policy, loader, optimizer, train: bool, class_weights=None):
    if train:
        policy.train()
    else:
        policy.eval()
    total_loss, total_n = 0.0, 0
    correct = [0] * 6
    pos_correct = [0] * 6   # accuracy doar pe clase NON-zero (relevant pentru binary)
    pos_total = [0] * 6
    ctx = torch.enable_grad() if train else torch.no_grad()
    with ctx:
        for batch_obs, batch_act in loader:
            batch_obs = batch_obs.to(DEVICE)
            batch_act = batch_act.to(DEVICE)
            dist = forward_dist(policy, batch_obs)
            loss = torch.zeros((), device=DEVICE)
            for i, sub in enumerate(dist.distribution):
                logits = sub.logits
                w = class_weights[i] if class_weights is not None else None
                loss = loss + F.cross_entropy(logits, batch_act[:, i], weight=w)
                preds = logits.argmax(dim=-1)
                correct[i] += (preds == batch_act[:, i]).sum().item()
                # positive-class accuracy: corect prezis cand target != 0
                mask = batch_act[:, i] != 0
                pos_total[i] += int(mask.sum().item())
                if pos_total[i] > 0:
                    pos_correct[i] += int((preds[mask] == batch_act[mask, i]).sum().item())
            if train:
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(policy.parameters(), 0.5)
                optimizer.step()
            total_loss += loss.item() * batch_obs.size(0)
            total_n += batch_obs.size(0)
    accs = [c / total_n for c in correct]
    pos_accs = [(pos_correct[i] / pos_total[i]) if pos_total[i] > 0 else 0.0 for i in range(6)]
    return total_loss / total_n, accs, pos_accs


def main():
    print(f"Device: {DEVICE}")
    obs, actions = load_demos()
    n = len(obs)
    print(f"\nTotal steps loaded: {n}")
    print(f"Direction histogram: {np.bincount(actions[:, 0], minlength=9).tolist()}")
    print(
        f"Binary actions: attack={int(actions[:,1].sum())} dash={int(actions[:,2].sum())} "
        f"ability={int(actions[:,3].sum())} interact={int(actions[:,4].sum())} "
        f"switch={int(actions[:,5].sum())}"
    )

    rng = np.random.default_rng(42)
    idx = rng.permutation(n)
    n_val = int(n * VAL_SPLIT)
    val_idx, train_idx = idx[:n_val], idx[n_val:]

    train_ds = DemoDataset(obs[train_idx], actions[train_idx])
    val_ds = DemoDataset(obs[val_idx], actions[val_idx])
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    print(f"Train: {len(train_ds)}, Val: {len(val_ds)}\n")

    env = DarkWizardEnv()
    model = build_fresh_ppo(env)
    policy = model.policy.to(DEVICE)
    optimizer = torch.optim.Adam(policy.parameters(), lr=LR)

    # Class weights pentru toate cele 6 heads (inverse frequency capped)
    train_actions = actions[train_idx]
    class_weights = compute_class_weights(train_actions)
    print("Class weights per head (capped la WEIGHT_CAP=%g):" % WEIGHT_CAP)
    head_names = ["dir", "atk", "dsh", "abl", "int", "sw"]
    for name, w in zip(head_names, class_weights):
        print(f"  {name}: {w.cpu().numpy().round(2).tolist()}")
    print()

    best_val = float("inf")
    os.makedirs(MODEL_DIR, exist_ok=True)
    out_path = os.path.join(MODEL_DIR, "bc_pretrained.zip")

    for epoch in range(1, EPOCHS + 1):
        tr_loss, tr_acc, tr_pos = epoch_pass(policy, train_loader, optimizer, train=True, class_weights=class_weights)
        val_loss, val_acc, val_pos = epoch_pass(policy, val_loader, optimizer, train=False, class_weights=class_weights)
        # afiseaza positive-class accuracy (cat de bine prinde frame-urile rare)
        pos_str = " ".join(
            f"{name}={p*100:.0f}%" for name, p in zip(head_names, val_pos)
        )
        marker = ""
        if val_loss < best_val:
            best_val = val_loss
            model.save(out_path)
            marker = "  [saved]"
        print(
            f"Epoch {epoch:02d}/{EPOCHS}  "
            f"train_loss={tr_loss:.4f}  val_loss={val_loss:.4f}  pos_acc[{pos_str}]"
            f"{marker}"
        )

    print(f"\nBest val_loss={best_val:.4f}, model saved to: {out_path}")
    print("Next: archive any old `models/ppo_darkwizard_*_steps.zip`, then run train.py")
    env.close()


if __name__ == "__main__":
    main()
