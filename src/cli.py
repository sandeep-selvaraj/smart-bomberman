"""Command line interface: play the game, or train / evaluate / watch AI agents.

    smart-bomberman play --level 1
    smart-bomberman train --maps map_2 --timesteps 300000
    smart-bomberman evaluate runs/<run>/best.zip --maps map_2
    smart-bomberman watch runs/<run>/best.zip --maps map_2
"""
import json
import os
from pathlib import Path

import fire  # type: ignore


def play(level: int = 1):
    """Play the game yourself (arrow keys to move, X to place a bomb)."""
    from game.menu import main_menu  # pylint: disable=import-outside-toplevel

    os.chdir(Path(__file__).resolve().parent)
    main_menu(level)


def train(**kwargs):
    """Train a PPO agent. See game.ai.train.train for all options."""
    from game.ai.train import train as _train  # pylint: disable=import-outside-toplevel

    run_dir = _train(**kwargs)
    print(f"saved run to {run_dir}")


def evaluate(model: str = "random", maps: str = "map_2", episodes: int = 100,
             deterministic: bool = False):
    """Evaluate a saved model (or 'random') and print outcome statistics."""
    from game.ai.train import evaluate as _evaluate  # pylint: disable=import-outside-toplevel

    print(json.dumps(_evaluate(model, maps, episodes, deterministic), indent=2))


def watch(model: str = "random", maps: str = "map_2", episodes: int = 3, fps: int = 8,
          deterministic: bool = False, save_frames: str = ""):
    """Watch an agent play in a pygame window."""
    from game.ai.train import watch as _watch  # pylint: disable=import-outside-toplevel

    _watch(model, maps, episodes, deterministic, fps, save_frames or None)


def main():
    """Entry point."""
    fire.Fire({"play": play, "train": train, "evaluate": evaluate, "watch": watch})


if __name__ == "__main__":
    main()
