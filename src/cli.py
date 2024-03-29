"""Command Line Interface for running the game"""
import os
from pathlib import Path
import fire  # type: ignore

# from game.maingame import start_game
from game.menu import main_menu


def run_the_game(level: int = 1):
    """Main function to run the game"""
    os.chdir(Path(__file__).resolve().parent)
    main_menu(level)
    # start_game(level)


if __name__ == "__main__":
    fire.Fire(run_the_game)
