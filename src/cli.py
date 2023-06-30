"""Command Line Interface for running the game"""
import os
from pathlib import Path
from typing import Optional
# import datetime
import tqdm  # type: ignore
import fire  # type: ignore
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from game.agent_enviornment.gym_environment import BombermanGameEnv
from game.agent_enviornment import inference
from game.menu import main_menu


def run_the_game(level: int = 1):
    """Main function to run the game"""
    os.chdir(Path(__file__).resolve().parent)
    main_menu(level)
    # start_game(level)


class CustomCallback(BaseCallback):
    """Callback to receive internal neural network weights."""

    # pylint: disable=super-with-arguments
    def __init__(self, env, verbose=0):
        super(CustomCallback, self).__init__(verbose)
        self.env = env
        self.progress_bar = None

    def _on_training_start(self):
        self.progress_bar = tqdm.tqdm(total=self.locals['total_timesteps'])

    def _on_step(self) -> bool:
        """Get weights for each training step."""
        # Access the neural network of the policy model
        self.progress_bar.update(1)
        neural_network = self.model.policy
        parameters_per_layer = [param.cpu().data.numpy() for param in neural_network.parameters()]
        self.env.update_policy_parameters(parameters_per_layer)
        return True

    def _on_training_end(self):
        self.progress_bar.close()
        self.progress_bar = None

def train_the_agent(existing_model_name: Optional[str] = None):
    """
    Train the agent by creating a new model or load an existing model.

    existing_model_name: Name for existing model to extend training.
    """
    os.chdir(Path(__file__).resolve().parent)
    log_path = os.path.join("Training", "Logs")
    env = BombermanGameEnv()
    if existing_model_name is not None:
        model_path = os.path.join("Training", existing_model_name)
        model = PPO.load(model_path, device='cuda',
                         env=env, tensorboard_log=log_path, gamma=0.998,
                         learning_rate=0.0002, ent_coef=0.03)
    # new_logger = configure(log_path, ["stdout", "csv", "tensorboard"])
    else:
        model = PPO("MultiInputPolicy", env, verbose=1, tensorboard_log=log_path, ent_coef=0.01)
    callback = CustomCallback(env=env)
    model.learn(total_timesteps=100000, callback=callback)
    # now = datetime.datetime.now()
    model_path = os.path.join("Training", "Saved Models_Stone_Cold_Enemy_train_Dict_2")
    model.save(model_path)


def information_on_game():
    """More information on the game."""
    print("Smart Bomberman")
    print("Built as a project at Technical University of Dresden")


def main(args=None) -> None:
    """Run smart-bomberman CLI."""
    fire.Fire(
        {
            "info": information_on_game,
            "play": run_the_game,
            "train": train_the_agent,
            "inference": inference.run_inference
        },
        command=args,
    )


if __name__ == "__main__":
    train_the_agent()