"""Command Line Interface for running the game"""
import fire  # type: ignore

from game.maingame import start_game


def run_the_game(level: int = 1):
    """Main function to run the game"""
    start_game(level)


if __name__ == "__main__":
    fire.Fire(run_the_game)
