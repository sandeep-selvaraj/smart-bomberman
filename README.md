<p align="center">
  <img src="src/graphics/bomberman_title.png" width="350" alt="Smart-Bomberman">
</p>

# smart-bomberman ![GitHub release](https://img.shields.io/github/release/sandeep-selvaraj/smart-bomberman?include_prereleases=&sort=semver&color=blue) [![ruff](https://img.shields.io/github/actions/workflow/status/sandeep-selvaraj/smart-bomberman/ruff.yml?branch=master&label=ruff)](https://github.com/sandeep-selvaraj/smart-bomberman/actions/workflows/ruff.yml) [![mypy](https://img.shields.io/github/actions/workflow/status/sandeep-selvaraj/smart-bomberman/mypy.yml?branch=master&label=mypy)](https://github.com/sandeep-selvaraj/smart-bomberman/actions/workflows/mypy.yml) [![tests](https://img.shields.io/github/actions/workflow/status/sandeep-selvaraj/smart-bomberman/tests.yml?branch=master&label=tests)](https://github.com/sandeep-selvaraj/smart-bomberman/actions/workflows/tests.yml)
<a href="https://github.com/sandeep-selvaraj/smart-bomberman/blob/master/LICENSE">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-yellow">
</a>
<a href="https://tu-dresden.de/?set_language=en">
  <img alt="Static Badge" src="https://img.shields.io/badge/Technical University-Dresden-blue">
</a>

<a href="https://imld.de/en/">
  <img alt="Static Badge" src="https://img.shields.io/badge/Faculty-IMLD-green">
</a>

**Visual Computing Team Project 2023**

Released under [MIT](/LICENSE).

## Table of contents

- [Installation](#installation)
- [Run the game](#run-the-game)
- [Game controls](#game-controls)
- [AI agent](#ai-agent)
- [AI agents from the 2023 project](#ai-agents-from-the-2023-project)
- [Notes](#notes)
- [Documentation](#documentation)

## Installation

The project uses [uv](https://docs.astral.sh/uv/) ([install it](https://docs.astral.sh/uv/getting-started/installation/) first).
uv installs the right Python (3.11 by default, 3.10+ supported) and the exact dependency versions from `uv.lock`:

```bash
uv sync
```

## Run the game

```bash
uv run smart-bomberman play
```

## Game controls

- Arrow keys to move
- 'X' to place bomb

## AI agent

<p align="center">
  <img src="docs/agent_map_1.gif" width="600" alt="PPO agent clearing map 1">
</p>

This version picks up the `feature/juhyun` work and makes the agent actually train.
The original setup could not learn: the game only advanced inside `render()`,
bomb fuses ran on wall-clock time, and one tile of movement took 16-32 actions.
`src/game/ai/` now holds a headless, tile-based engine with the same rules
and a Gymnasium env. A PPO agent trained on it wins:

| Map | Win rate (deterministic, 200 episodes) | Random policy |
|---|---|---|
| map_1 (maze, 3 enemies) | **91%** | 0% |
| map_2 (open grid, 3 enemies) | **79.5%** | 0% |

```bash
uv run smart-bomberman watch models/ppo_map1_map2.zip --maps map_1 --deterministic   # watch the trained agent
uv run smart-bomberman evaluate models/ppo_map1_map2.zip --maps map_2 --episodes 200 --deterministic
uv run smart-bomberman train --maps map_2 --timesteps 1000000    # about 7 minutes on a laptop CPU
```

See [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) for what was wrong, what changed, and the
results of each round of trials. Tests and checks: `uv run pytest`, `uv run ruff check`, `uv run mypy src`.

## AI agents from the 2023 project

Each team member's original approach lives on its own branch. They predate the agent above and
need their own setup (pinned `gymnasium` and `stable-baselines3` versions), so follow the
instructions on each branch.

- _feature/divyendu_: PPO and NEAT models with multiple observation spaces
- _feature/ken_: PPO with multiple observation spaces and a curriculum-learning path
- _feature/juhyun_: Dict observation space, the starting point for the current agent
- _feature/sandeep_: Box observation space (superseded)
- _training/sandeep_: Multiplayer mode for visual benchmarking and visualizing training

## Notes

- **PyTorch builds**: on Linux and Windows, `pyproject.toml` installs the CPU-only PyTorch wheels
  (PyPI's default ones bundle several GB of CUDA). The agents here train fine on a CPU. To train on an
  NVIDIA GPU, change the `pytorch-cpu` index URL in `pyproject.toml` to a CUDA one from
  [pytorch.org](https://pytorch.org/get-started/locally/) (e.g. `https://download.pytorch.org/whl/cu126`)
  and run `uv lock && uv sync`. On macOS the default wheels are used.

## Documentation

Please check out the [official documentation](https://cloudstore.zih.tu-dresden.de/index.php/s/f5Dr3pppn6ySrcp)
pertaining all the key aspects of research and development of the smart-bomberman.

The [unofficial documentation](docs/EXPERIMENTS.md) covers the later AI work: why the 2023 training
setup could not learn, how it was rebuilt, and the results of each round of trials.
