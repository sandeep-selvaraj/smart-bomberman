"""Command line interface: play the game, or train / evaluate / watch AI agents.

smart-bomberman play --level 1
smart-bomberman train --maps map_2 --timesteps 300000
smart-bomberman evaluate runs/<run>/best.zip --maps map_2
smart-bomberman watch runs/<run>/best.zip --maps map_2
smart-bomberman versus --difficulty hard          # you vs Two-Fuse, Battle mode
smart-bomberman train-versus --timesteps 5000000
smart-bomberman duel models/two_fuse.zip heuristic
"""

import json
import os
from pathlib import Path

import fire  # type: ignore


def play(level: int = 1):
    """Play the game yourself (arrow keys to move, X to place a bomb)."""
    from game.menu import main_menu

    os.chdir(Path(__file__).resolve().parent)
    main_menu(level)


def train(**kwargs):
    """Train a PPO agent. See game.ai.train.train for all options."""
    from game.ai.train import train as _train

    run_dir = _train(**kwargs)
    print(f"saved run to {run_dir}")


def evaluate(model: str = "random", maps: str = "map_2", episodes: int = 100, deterministic: bool = False):
    """Evaluate a saved model (or 'random') and print outcome statistics."""
    from game.ai.train import evaluate as _evaluate

    print(json.dumps(_evaluate(model, maps, episodes, deterministic), indent=2))


def watch(
    model: str = "random",
    maps: str = "map_2",
    episodes: int = 3,
    fps: int = 8,
    deterministic: bool = False,
    save_frames: str = "",
):
    """Watch an agent play in a pygame window."""
    from game.ai.train import watch as _watch

    _watch(model, maps, episodes, deterministic, fps, save_frames or None)


def versus(
    arena: str = "arena_1",
    difficulty: str = "normal",
    model: str = "",
    rounds: int = 3,
    tps: int = 7,
    enemies: bool = True,
    player: str = "human",
    seed: int | None = None,
    save_gif: str = "",
):
    """Battle mode against Two-Fuse: arrow keys to move, X or Space to bomb, last one standing wins.

    difficulty: easy (scripted bot), normal (trained model, a little unpredictable) or hard.
    arena: arena_1, or any map_N. player: human, or heuristic/random/a model path to watch a bot play.
    """
    from game.ai.versus_game import play_versus
    from game.ai.versus_train import CHAMPION

    play_versus(arena, difficulty, model or str(CHAMPION), rounds, tps, enemies, player, seed, save_gif or None)


def train_versus(**kwargs):
    """Train Two-Fuse by league self-play. See game.ai.versus_train.train_versus for all options."""
    from game.ai.versus_train import train_versus as _train_versus

    run_dir = _train_versus(**kwargs)
    print(f"saved run to {run_dir}; champion: {run_dir / 'two_fuse.zip'}")


def duel(a: str, b: str = "heuristic", maps: str = "arena_1,map_2,map_3", games: int = 40, stochastic: bool = False):
    """Pit two Battle-mode policies against each other: model paths or heuristic, camper, wanderer, random."""
    from game.ai.policies import make_policy
    from game.ai.versus_train import duel as _duel

    record = _duel(make_policy(a, not stochastic, seed=1), make_policy(b, not stochastic, seed=2), maps, games)
    print(json.dumps(record, indent=2))


def main():
    """Entry point."""
    fire.Fire(
        {
            "play": play,
            "train": train,
            "evaluate": evaluate,
            "watch": watch,
            "versus": versus,
            "train-versus": train_versus,
            "duel": duel,
        }
    )


if __name__ == "__main__":
    main()
