"""Command Line Interface for running the game"""
import os
from pathlib import Path
import fire  # type: ignore
from game.maingame import MainGame

# from game.maingame import start_game
from game.menu import main_menu


def run_the_game(level: int = 1, type='play'):
    """Main function to run the game"""
    os.chdir(Path(__file__).resolve().parent)
    if type == 'play':
        main_menu(level)
    elif type == 'train' or type == 'infer':
        MainGame(level).start_game(type)

    # start_game(level)


if __name__ == "__main__":
    fire.Fire(run_the_game)
