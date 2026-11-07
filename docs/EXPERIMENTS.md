# AI agent: revival experiments (Nov 2026)

This branch (`ai/clean-agent`) restarts the AI work from `feature/juhyun`, the
branch the 2023 README called the best working model. Its trained models were
never committed, and it could not train as written, so these trials start from
scratch.

## Why the 2023 setup could not learn

| Problem in `feature/juhyun` | Effect |
|---|---|
| The game only advanced inside `render()` | Training needed a visible window and ran at frame rate |
| Bomb fuses used `pygame.time.get_ticks()` (wall-clock seconds) | Steps per fuse depended on machine speed, so the dynamics were not stationary |
| Movement of 1-2 pixels per action | One tile took 16-32 actions, a very long horizon for credit assignment |
| Class-level state in `Level` (`level_bombs`, power-up flags) | Leaked between episodes |
| Observation was coordinates only (agent, door, bomb, enemies) | The policy could not see walls, flames or danger |
| `+0.05` on every step a bomb was on the map | Rewarded placing bombs and then dying to them |

## What changed

* `src/game/ai/engine.py`: a headless, tile-based engine with the same rules (maps,
  bomb range 1, one bomb at a time, wandering enemies at half the player's speed,
  door opens when all enemies are dead). Every timer counts steps.
  It runs at about 2-5k steps/s per process.
* `src/game/ai/env.py`: the Gymnasium env. It keeps Juhyun's `Dict` observation idea
  and adds a 9x9 local view (7 channels: solid, breakable, bomb fuse, flame,
  danger, enemy, door) plus a 19-dim state vector.
* Rewards: -0.01 per step, +1 per kill, +5 for reaching the open door, -2 for
  death, plus potential-based shaping on the walking distance to the target.
* PPO (Stable-Baselines3, `MultiInputPolicy`, 256x256 MLP), 4-5 parallel envs, CPU only.
* The human-playable pygame game is unchanged (restored to `master`).

## Trials

Each trial used a single seed. Evaluations during training used 30-40 episodes.
The final numbers use 200 episodes per map.

| Round | Change | Map | Steps | Win rate | Notes |
|---|---|---|---|---|---|
| baseline | random policy | 1 / 2 / 3 | - | 0 / 0 / 0 % | dies in 100% of episodes, mostly to its own bombs |
| 1 | local view + shaping | 3 | 1M | **100%** | map 3 has an open path to the door, so no bombing is needed |
| 1 | | 2 | 1M | 0% | learned to kill (1.8 of 3 enemies) but never finished the level |
| 1 | | 1 | 1M | 0% | 0 kills |
| 2 | + escape features, threat bonus | 2 | 1M | **57% / 64.5%** (stoch / det, 200 ep) | kills started at 200k steps instead of 500k |
| 2 | | 1 | 1M | 0% | collapsed to a passive policy (about 73% no-op), hiding from enemies |
| 3a | round 2 map 2 model, fine-tuned on maps 1+2 | 1 | +1.5M | **79.5% / 91%** (stoch / det, 200 ep) | transfer solved the maze |
| 3a | | 2 | +1.5M | **73.5% / 79.5%** (stoch / det, 200 ep) | |
| 3a | | 3 | - | 0% | never trained on it; times out (doesn't navigate to the door) |
| 3b | maps 1+2 from scratch | 1+2 | 1.5M | 0% | 1.6 kills per episode by the end; slow without the map 2 warm start |

### Takeaways

1. **The environment was the blocker, not the algorithm.** Once the game had
   grid-step actions and step-counted timers, plain PPO learned map 2 within
   about 1M steps on a laptop CPU.
2. **Escape-route features matter.** "Can I drop a bomb here and still get
   out?" plus an escape compass for each move roughly halved the time to the
   first kills.
3. **A curriculum (transfer from map 2) was the deciding factor for the maze.**
   From scratch, map 1 settles on a passive policy. Starting from the map 2
   agent, it reaches 91% wins.

### Caveats

* One seed per configuration. The 3a vs 3b gap is large, but seeds should be
  repeated before treating it as a firm result.
* The engine simplifies the game: no power-ups, no bombs hidden in walls, and
  enemies are random walkers. A trained agent plays the grid engine, not the
  pixel-based pygame game.
* Map 3 needs to be included in training (or have its open path closed) to
  become a real bombing task.

## Reproduce

```bash
uv run smart-bomberman train --maps map_2 --timesteps 1000000 --n_envs 5 --run_name r2_map_2
uv run smart-bomberman train --maps map_1,map_2 --timesteps 1500000 --n_envs 4 \
    --init_from runs/r2_map_2/best.zip --run_name r3a_transfer
uv run smart-bomberman evaluate runs/r3a_transfer/best.zip --maps map_1 --episodes 200 --deterministic
```

Round 1 ran before the escape features existed (13-dim state, no threat
bonus, enemy standoff 2), so it can't be reproduced exactly from this
commit without removing those features.

## Battle mode: training Two-Fuse

Two-Fuse is the Battle-mode agent (`src/game/ai/versus_*.py`, `policies.py`).
Two fighters share an arena with the map's wandering enemies, and the last
one standing wins. From step 150 (step 200 in human games) sudden death
closes one cell per step, spiralling inwards, so every match ends.

### Setup

* **Observation.** Extends the single-player one rather than replacing it.
  The first 7 planes and 19 state values keep their meaning, with the
  opponent as "the target" and also marked in the enemy plane. Two planes
  are added (opponent, closing cells) and five state values (opponent's bomb
  available, opponent's distance to safety, sudden-death flag, time to sudden
  death, closing urgency on the agent's own cell). The engine counts cells
  about to close as hazards, so the danger map and escape features cover the
  shrinking arena.
* **Warm start.** `warm_start_policy` copies the single-player agent's
  weights into the larger network. Old inputs map to their new columns, and
  new inputs start at zero weight. A test checks that the result picks
  exactly the same actions as the original. Out of the box it beats random
  every time and wins about 20% against the scripted bot.
* **League self-play.** A snapshot is saved every 250k steps. Each training
  match faces the latest snapshot 50% of the time, an older one 30%, and a
  scripted bot 20%. Snapshots play greedy or sampled with equal odds.
  Starting corners are a coin flip.
* **Rewards.** Win +5, loss -5, dying together -2. Small terms for walls and
  enemies destroyed, distance shaping toward the opponent (standoff 3), and a
  +0.2 bonus for a bomb placed near the opponent with a way out.
* **Champion.** A round robin between the last 8 snapshots, the scripted bot
  and random, 12 games per pair, fitted to Elo (Bradley-Terry).

### Results (run `two_fuse_v1`: 5M steps, 10 envs, about 75 minutes)

Eval vs the scripted bot (30 games every 250k steps) was flat around 30-50%
for the first 3.5M steps, then rose to 57-83% from 4M. The tournament put the
final snapshot first, at 1149 Elo. The scripted bot rated 1084 and random 41.

Over 200 games vs the scripted bot (arena_1, map_2, map_3):

| Policy | Win | Loss | Draw |
|---|---|---|---|
| warm start, no versus training | ~20% | ~80% | 0% |
| `snap_004500000`, greedy | 60% | 39% | 1% |
| champion (`models/two_fuse.zip`), greedy | **66%** | 30.5% | 3.5% |
| champion, sampled | 59% | 37% | 4% |

### Caveats and next steps

* The late snapshots were still beating the earlier ones, so a longer run
  should be stronger: `train-versus --init_from models/two_fuse.zip` picks up
  from the champion.
* 12 games per pair is a coarse tournament. Elo gaps under ~50 points between
  snapshots are within noise.
* The scripted bot is the only fixed yardstick. Playing human testers would
  be a better one.
