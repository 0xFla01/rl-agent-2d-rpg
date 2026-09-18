"""
Ruleaza agentul antrenat (fara antrenare).
Foloseste modelul salvat de train.py.

Rulare: python play.py
        python play.py --model models/ppo_darkwizard_100000_steps
"""

import argparse
import os
from stable_baselines3 import PPO
from game_env import DarkWizardEnv

DEFAULT_MODEL = os.path.join("models", "ppo_darkwizard_final")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help="Calea catre modelul salvat")
    parser.add_argument("--episodes", type=int, default=10,
                        help="Numarul de episoade de rulat")
    args = parser.parse_args()

    print(f"Incarc modelul: {args.model}")
    model = PPO.load(args.model)

    env = DarkWizardEnv()
    ep_rewards = []

    for ep in range(1, args.episodes + 1):
        obs, _ = env.reset()
        total_reward = 0.0
        steps = 0

        while True:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(action)
            total_reward += reward
            steps += 1

            if terminated or truncated:
                break

        ep_rewards.append(total_reward)
        print(f"Episod {ep:3d} | Steps: {steps:4d} | Reward total: {total_reward:8.1f}")

    print(f"\nMedie reward: {sum(ep_rewards)/len(ep_rewards):.1f}")
    env.close()


if __name__ == "__main__":
    main()
