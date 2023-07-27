import gymnasium as gym
from .BBM_env import BBMEnv
import time, os
import datetime
from .custom_callback import SaveOnBestTrainingRewardCallback

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.monitor import Monitor


def run_train(level_mode):
    BASE_NAME = 'ppo_bomberman'
    MAP_NUM = 'map_3'
    current_date_time = get_current_date_time()
    # MODEL_SAVE_NAME = f"{BASE_NAME}_{MAP_NUM}_{current_date_time}"
    MODEL_SAVE_NAME = f"ppo_bomberman_map_3_2023-07-26_18-08-09"
    # MODEL_SAVE_NAME = f"ppo_bomberman_map_3_2023-06-30_13-40-16"
    # MODEL_SAVE_NAME = f"ppo_bomberman_map_3_2023-06-30_15-22-43"
    MODEL_SAVE_NAME_BEST = f"{MODEL_SAVE_NAME}_Best"

    # Create log dir
    log_dir = MODEL_SAVE_NAME_BEST
    os.makedirs(log_dir, exist_ok=True)

    vec_env = BBMEnv(render_mode="human", level_mode= level_mode)
    # vec_env = Monitor(vec_env, log_dir)
    
    # model = PPO.load(MODEL_SAVE_NAME_BEST+"/best_model.zip", vec_env, verbose=1, tensorboard_log="../training/ppo_tensorboard/", seed=0, learning_rate=0.00015)#,  learning_rate=0.0001)
    # # model = PPO("MultiInputPolicy", vec_env, verbose=1, tensorboard_log="../training/ppo_tensorboard/", seed=0)
    # callback = SaveOnBestTrainingRewardCallback(check_freq=5000, log_dir=log_dir)
    # model.learn(total_timesteps=3000000, callback=callback)

    # del model # remove to demonstrate saving and loading

    model = PPO.load(MODEL_SAVE_NAME_BEST+"/best_model.zip")
    # model = PPO.load(MODEL_SAVE_NAME)

    print("infer")

    for _ in range(5):
        obs, info = vec_env.reset()
        test = True
        while test:
            action, _states = model.predict(obs)
            obs, rewards, dones, trunc, info = vec_env.step(action)
            if dones or trunc:
                test = False
            # vec_env.render()




# def run_train(level_mode):
#     env = BBMEnv(render_mode="human", level_mode= level_mode)
#     observation, info = env.reset()
#     print(observation, info)

#     for _ in range(1000):
#         action = env.action_space.sample()  # agent policy that uses the observation and info
#         observation, reward, terminated, truncated, info = env.step(action)
#         # print(observation, reward, info, terminated, truncated)
#         # time.sleep(0.1)

#         if terminated or truncated:
#             observation, info = env.reset()
#             print(observation, reward, info, terminated, truncated)

#     env.close()


def get_current_date_time():
    current_date_time = datetime.datetime.now()
    formatted_date_time = current_date_time.strftime("%Y-%m-%d_%H-%M-%S")
    return formatted_date_time


