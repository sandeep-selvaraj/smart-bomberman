"""For inference of the model."""
import os
from stable_baselines3 import PPO
from .gym_environment import BombermanGameEnv

def run_inference(model):
    """
    Run inference to check how well your model works.

    Parameters:
        model: Path to Model ZIP file.
    """
    # Load the saved model
    model = PPO.load(f"src/Training/{model}")
    os.chdir("src")
    # Set up the environment
    env = BombermanGameEnv()

    # Run the inference loop
    done = False
    obs, _ = env.reset()

    while not done:
        action, _ = model.predict(obs)
        obs, *_, done, _ = env.step(action)
        env.render()

    # Visualize or analyze the results
    env.close()
