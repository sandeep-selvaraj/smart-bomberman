"""Command Line Interface for running the game"""
import os
from pathlib import Path
import fire  # type: ignore
from stable_baselines3 import PPO
# from stable_baselines3.common.logger import configure
from game.agent_enviornment.gym_environment import BombermanGameEnv

# from game.maingame import start_game
from game.menu import main_menu


def run_the_game(level: int = 1):
    """Main function to run the game"""
    os.chdir(Path(__file__).resolve().parent)
    main_menu(level)
    # start_game(level)


def train_the_agent():
    os.chdir(Path(__file__).resolve().parent)
    Log_path = os.path.join("Training", "Logs")
    model_path = os.path.join("Training", "Saved Models")
    env = BombermanGameEnv()
    # new_logger = configure(Log_path, ["stdout", "csv", "tensorboard"])
    # model = PPO("MlpPolicy", env, verbose=1, tensorboard_log=Log_path)
    model = PPO("MlpPolicy", env, verbose=1, tensorboard_log=Log_path)
    # model.set_logger(new_logger)
    model.learn(total_timesteps=250000)
    model.save(model_path)


if __name__ == "__main__":
    # fire.Fire(run_the_game)
    train_the_agent()
