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
smart-bomberman train --maps map_2 --timesteps 1000000 --n_envs 5 --run_name r2_map_2
smart-bomberman train --maps map_1,map_2 --timesteps 1500000 --n_envs 4 \
    --init_from runs/r2_map_2/best.zip --run_name r3a_transfer
smart-bomberman evaluate runs/r3a_transfer/best.zip --maps map_1 --episodes 200 --deterministic
```

Round 1 ran before the escape features existed (13-dim state, no threat
bonus, enemy standoff 2), so it can't be reproduced exactly from this
commit without removing those features.
