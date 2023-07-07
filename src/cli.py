"""Command Line Interface for running the game"""
import os
from pathlib import Path
import fire  # type: ignore
# from game.maingame import start_game
from typing import Optional
# import datetime
import numpy as np
import tqdm  # type: ignore
import fire  # type: ignore
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.results_plotter import load_results, ts2xy
from game.agent_enviornment.gym_environment import BombermanGameEnv
from game.agent_enviornment import inference
from game.menu import main_menu
from game.multiplayer import multiplayer_game


def run_the_game(level: int = 1):
    """Main function to run the game"""
    os.chdir(Path(__file__).resolve().parent)
    main_menu(level)
    # start_game(level)


class CustomCallback(BaseCallback):
    """Callback to receive internal neural network weights."""

    # pylint: disable=super-with-arguments
    def __init__(self, env, log_dir, check_freq, verbose=0):
        super(CustomCallback, self).__init__(verbose)
        self.env = env
        self.progress_bar = None
        self.log_dir = log_dir
        self.save_path = os.path.join(log_dir, "best_model_render_1")
        self.best_mean_reward = -np.inf
        self.check_freq = check_freq

    def _init_callback(self) -> None:
        # Create folder if needed
        if self.save_path is not None:
            os.makedirs(self.save_path, exist_ok=True)

    def _on_training_start(self):
        self.progress_bar = tqdm.tqdm(total=self.locals['total_timesteps'])

    def _on_step(self) -> bool:
        """Get weights for each training step."""
        # Access the neural network of the policy model
        self.progress_bar.update(1)
        neural_network = self.model.policy
        parameters_per_layer = [param.cpu().data.numpy() for param in neural_network.parameters()]
        self.env.update_policy_parameters(parameters_per_layer)
        if self.n_calls % self.check_freq == 0:

            # Retrieve training reward
            x, y = ts2xy(load_results(self.log_dir), "timesteps")
            if len(x) > 0:
                # Mean training reward over the last 100 episodes
                mean_reward = np.mean(y[-100:])
                if self.verbose >= 1:
                    print(f"Num timesteps: {self.num_timesteps}")
                    print(
                        f"Best mean reward: {self.best_mean_reward:.2f} - Last mean reward per episode: {mean_reward:.2f}")

                # New best model, you could save the agent here
                if mean_reward > self.best_mean_reward:
                    self.best_mean_reward = mean_reward
                    # Example for saving best model
                    if self.verbose >= 1:
                        print(f"Saving new best model to {self.save_path}")
                    self.model.save(self.save_path)
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
    env = Monitor(env, log_path)
    if existing_model_name is not None:
        model_path = os.path.join("Training", existing_model_name)
        model = PPO.load(model_path, device='cuda',
                         env=env, tensorboard_log=log_path,
                         learning_rate=0.0002, ent_coef=0.2, clip_range=0.7)
    # new_logger = configure(log_path, ["stdout", "csv", "tensorboard"])
    else:
        model = PPO("MultiInputPolicy", env, verbose=1, tensorboard_log=log_path, ent_coef=0.15, n_steps=5)
        # model = DQN("MultiInputPolicy", env, learning_rate=1e-3, tensorboard_log=log_path)
        # model = PPO("MlpPolicy", env, verbose=1, tensorboard_log=log_path, ent_coef=0.1)
    callback = CustomCallback(env=env, check_freq=1000, log_dir=log_path)
    model.learn(total_timesteps=200000, callback=callback)
    # now = datetime.datetime.now()
    model_path = os.path.join("Training", "Saved Models_Stone_Cold_16_new_obs_ent_0_2")
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


# if __name__ == "__main__":
#     # fire.Fire(run_the_game)
#     # train_the_agent()
#     os.chdir(Path(__file__).resolve().parent)
#     multiplayer_game.start_game_multiplayer(1,
#                                             "Saved Models_Stone_Cold_7_no_render_8obs_ent0_2",
#                                             "Saved Models_Stone_Cold_16_new_obs_ent_0_2")
