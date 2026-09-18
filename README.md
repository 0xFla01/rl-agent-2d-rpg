# Reinforcement Learning Agent for a 2D Action RPG

Bachelor's thesis project. A PPO agent learns to play a top down action RPG
built in Godot 4, starting from nothing and learning to fight, level up, use
items and progress through a dungeon.

The thesis itself is written in Romanian. This README is in English.

## What the problem is

The game is not a toy environment. It has real combat, traps, enemies with
different behaviours, consumable items, a shop, levers that open doors, and a
level progression the agent has to discover on its own. An episode can run for
thousands of steps, and the reward for reaching a new room arrives long after
the actions that made it possible.

That delay is the core difficulty. Most of the work in this project went into
making a sparse, long horizon reward learnable.

## How it works

```
  Godot 4 game  <-->  file based IPC  <-->  Python training loop
  (GDScript)                               (stable-baselines3 PPO)
```

The game writes its state to disk each step, the Python environment reads it,
returns an action, and the game applies it. `game_env.py` wraps that exchange
in a standard Gym interface so any stable-baselines3 algorithm can drive it.

Main techniques used:

- **PPO** with an MLP policy, linearly decaying learning rate, `n_steps=2048`
- **Behavioural cloning pretraining** from recorded human demonstrations, so
  the policy does not start from random flailing
- **Curriculum learning**, spawning the agent in later rooms with a controlled
  probability so it sees states that pure exploration would almost never reach
- **Reward shaping**, including anti farming penalties after the agent learned
  to grind safe combat instead of progressing
- **Reward normalisation** and a longer discount horizon (`gamma=0.997`) to
  fight the catastrophic forgetting that dominated early runs

## Results

Measured over full episodes, comparing the trained agent against scripted
baselines and against large language models playing the same game zero shot
through the same interface.

| Metric | random | scripted | Claude Haiku | trained agent |
|---|---|---|---|---|
| Episodes | 39 | 30 | 21 | 3959 |
| Avg kills per episode | 1.03 | 0.2 | 0.0 | **5.81** |
| Max depth reached | 2 | 2 | 2 | **8** |
| Buffs used (total) | 0 | 0 | 0 | **219** |
| Avg final level | 1.0 | 1.0 | 1.0 | **2.66** |
| Max final level | 1 | 1 | 1 | **5** |

The baselines never leave the second room, never level up and never use a
single item. The trained agent clears rooms, levels to 5, uses the item system
and reaches depth 8.

A Claude Opus run is included in the raw data but only covers a single episode,
so it is not quoted above.

Charts for every run are in `AI_Training/results_*`: learning curves, per room
heatmaps, death position maps, outcome breakdowns and cross run comparisons.

## Layout

```
Fla18/Licenta/      the Godot 4 game
AI_Training/
  train.py          PPO training loop
  game_env.py       Gym environment wrapping the game
  bc_pretrain.py    behavioural cloning from demonstrations
  claude_player.py  LLM zero shot baseline
  analyze_*.py      analysis and chart generation
  results_*/        charts and comparison tables per run
```

## Running it

```bash
pip install stable-baselines3 torch numpy matplotlib
python train.py
```

The game must be running so the training loop has something to talk to.

## What is not in this repo

Model checkpoints (about 1.4 GB) and raw per step episode telemetry (about
500 MB) are excluded. Everything shown in the charts is derived from that data
and the charts are committed.

## Credits

The Godot game is built on the open source
[2D Action Adventure RPG Tutorial](https://github.com/michaelmalaska) project
by michaelmalaska (Michael Games), used under the MIT licence, which is kept
at `Fla18/Licenta/LICENSE`. The game was extended for this thesis with the
state export, the agent control interface, the level and enemy changes and the
reward instrumentation.

Everything in `AI_Training/` is my own work.
