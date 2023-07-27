
import gymnasium as gym
from gymnasium.envs.registration import register
from stable_baselines3 import PPO, DQN
from stable_baselines3.common.utils import get_device
from game.envs.smart_bomberman_env import SmartBombermanEnv
import os

def initialize(game_ins):
    print(get_device())
    register(id="smart-bomberman-v0", entry_point=SmartBombermanEnv)
    env = gym.make("smart-bomberman-v0", game=game_ins, render_mode="human")
    return env

def infer1(game_ins):
    env = initialize(game_ins)
    actions = [4, 1, 1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
    obs, _ = env.reset()
    for action in actions:
        obs, rewards, terminated, truncated, info = env.step(action)
        env.render()
        
def infermultiplayer(game_ins):
    MODEL_SAVE_FOLDER_PATH = os.getcwd() + "/models"
    env = initialize(game_ins)
    if not os.path.exists(MODEL_SAVE_FOLDER_PATH):
        raise FileNotFoundError(f"Folder: {MODEL_SAVE_FOLDER_PATH} not found")
    #model = DQN.load(get_latest_file(MODEL_SAVE_FOLDER_PATH))
    model = PPO.load(get_latest_file(MODEL_SAVE_FOLDER_PATH))
    while True:
        obs, _ = env.reset()
        while True:
            action, _states = model.predict(obs)
            obs, rewards, terminated, truncated, info = env.step(int(action.item()))
            if terminated or truncated:
                break
            #env.render()

def infer(game_ins):
    MODEL_SAVE_FOLDER_PATH = os.getcwd() + "/models"
    env = initialize(game_ins)
    if not os.path.exists(MODEL_SAVE_FOLDER_PATH):
        raise FileNotFoundError(f"Folder: {MODEL_SAVE_FOLDER_PATH} not found")
    #model = DQN.load(get_latest_file(MODEL_SAVE_FOLDER_PATH))
    model = PPO.load(get_latest_file(MODEL_SAVE_FOLDER_PATH))
    while True:
        obs, _ = env.reset()
        while True:
            action, _states = model.predict(obs)
            obs, rewards, terminated, truncated, info = env.step(int(action.item()))
            if terminated or truncated:
                break
            #env.render()

def get_latest_file(path):
    files = os.listdir(path)
    latest_file = None
    latest_timestamp = 0
    for file in files:
        file_path = os.path.join(path, file)
        if os.path.isfile(file_path):
            timestamp = os.path.getmtime(file_path)
            if timestamp > latest_timestamp:
                latest_timestamp = timestamp
                latest_file = file_path

    if latest_file is not None:
        return latest_file
    else:
        raise ValueError(f"No latest models found at {path}")
