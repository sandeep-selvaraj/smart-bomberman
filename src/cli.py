"""Command Line Interface for running the game"""
import fire

from game.maingame import start_game

def run_the_game():
    """Main function to run the game"""
    start_game()

fire.Fire(run_the_game)
