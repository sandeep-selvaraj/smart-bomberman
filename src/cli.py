"""Command Line Interface for running the game"""
import os
from pathlib import Path
import fire  # type: ignore

# from game.maingame import start_game
from game.menu import main_menu
from game.BBM_env import BBMEnv
from game.train import run_train
from stable_baselines3.common.env_checker import check_env


def run_the_game(level: int = 1, mode: str = "play"):
    """Main function to run the game"""
    os.chdir(Path(__file__).resolve().parent)
    if mode == "play":
        main_menu(level)
    elif (mode == "train"):
        run_train(level)
    else:
        print("Invalid Mode")
    # start_game(level)


if __name__ == "__main__":
    fire.Fire(run_the_game)
