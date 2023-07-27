import gymnasium as gym
from gymnasium.envs.registration import register
import datetime
from stable_baselines3 import PPO, DQN
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.utils import get_device
from stable_baselines3.common.evaluation import evaluate_policy
from game.envs.smart_bomberman_env import SmartBombermanEnv
from .SaveBestModelCallback import SaveOnBestTrainingRewardCallback
from stable_baselines3.common.monitor import Monitor
import os
import optuna

from .train_agent_ppo_cl_rl import trainer

def initialize(game_ins):
    print(get_device())
    register(id="smart-bomberman-v0", entry_point=SmartBombermanEnv)
    #env = gym.make("smart-bomberman-v0", game=game_ins, render_mode="human")
    smart_bomberman_env = SmartBombermanEnv(game=game_ins)
    seed = 1
    env_args = {"game": game_ins}
    env = make_vec_env("smart-bomberman-v0", env_kwargs=env_args, n_envs=4, seed=seed)
    return env

def objective(trial, game_ins): 
    MODEL_SAVE_FOLDER_PATH = os.getcwd() + "/models"
    BASE_NAME = 'ppo_smart_bomberman'
    current_date_time = get_current_date_time()
    TENSORBOARD_LOG_NAME = f"./{BASE_NAME}_tensorboard"
    MODEL_SAVE_NAME = f"{BASE_NAME}_{current_date_time}"
    # Define the hyperparameters to be tuned
    learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-1, log=True)
    n_steps = trial.suggest_int('n_steps', 1024, 4096, log=True)
    batch_size = trial.suggest_int('batch_size', 64, 256, log=True)
    ent_coef = trial.suggest_float('ent_coef', 0.1, 0.99, log=True)
    n_epochs = trial.suggest_int('n_epochs', 5, 20, log=True)
    gamma = trial.suggest_float('gamma', 0.1, 0.99, log=True)
    gae_lambda = trial.suggest_float('gae_lambda', 0.1, 0.99, log=True)
    clip_range = trial.suggest_float('clip_range', 0.1, 0.99, log=True)
    vf_coef = trial.suggest_float('vf_coef', 0.1, 0.99, log=True)
    max_grad_norm = trial.suggest_float('max_grad_norm', 0.1, 0.99, log=True)

    # Set up the Gym environment
    env = initialize(game_ins)

    # Set up the Stable Baselines PPO agent with the hyperparameters
    model = PPO('MlpPolicy', env, 
                learning_rate=learning_rate, 
                n_steps=n_steps, 
                ent_coef=ent_coef,
                batch_size=batch_size,
                n_epochs=n_epochs,
                gamma=gamma,
                gae_lambda=gae_lambda,
                clip_range=clip_range,
                vf_coef=vf_coef,
                max_grad_norm=max_grad_norm,
                tensorboard_log=TENSORBOARD_LOG_NAME)

    # Train and evaluate the agent
    model.learn(total_timesteps=1000, tb_log_name=MODEL_SAVE_NAME)

    # Return the evaluation metric for optimization
    mean_reward, _ = evaluate_policy(model, env, n_eval_episodes=20)
    return mean_reward

def train_opt(game_ins):
    MODEL_SAVE_FOLDER_PATH = os.getcwd() + "/models"
    BASE_NAME = 'ppo_smart_bomberman'
    TENSORBOARD_LOG_NAME = f"./{BASE_NAME}_tensorboard"
    current_date_time = get_current_date_time()
    MODEL_SAVE_NAME = f"{BASE_NAME}_{current_date_time}"
    # Set up Optuna study
    study = optuna.create_study(direction='maximize')

    # Define the objective function
    def objective_wrapper(trial):
        return objective(trial, game_ins)

    # Run the optimization
    study.optimize(objective_wrapper, n_trials=50)

    # Get the best hyperparameters
    best_params = study.best_trial.params
    print('Best hyperparameters:', best_params)

    # Set up the Gym environment
    env = initialize(game_ins)

    # Set up the Stable Baselines PPO agent with the best hyperparameters
    model = PPO('MlpPolicy', env, 
                learning_rate=best_params['learning_rate'], 
                n_steps=best_params['n_steps'],
                batch_size=best_params['batch_size'],
                ent_coef=best_params['ent_coef'],
                n_epochs=best_params['n_epochs'],
                gamma=best_params['gamma'],
                gae_lambda=best_params['gae_lambda'],
                clip_range=best_params['clip_range'],
                vf_coef=best_params['vf_coef'],
                max_grad_norm=best_params['max_grad_norm'],
                tensorboard_log=TENSORBOARD_LOG_NAME)

    # Train the agent with the best hyperparameters
    model.learn(total_timesteps=1000000, tb_log_name=MODEL_SAVE_NAME)

    # Save the trained model
    
    if not os.path.exists(MODEL_SAVE_FOLDER_PATH):
        os.makedirs(MODEL_SAVE_FOLDER_PATH)
    model.save(os.path.join(MODEL_SAVE_FOLDER_PATH, MODEL_SAVE_NAME))

#def train(game_ins):
#    trainer(game_ins)

def train(game_ins):
    log_dir = "tmp/"
    os.makedirs(log_dir, exist_ok=True)
    MODEL_SAVE_FOLDER_PATH = os.getcwd() + "/models"
    BASE_NAME = 'ppo_smart_bomberman'
    current_date_time = get_current_date_time()
    TENSORBOARD_LOG_NAME = f"./{BASE_NAME}_tensorboard"
    MODEL_SAVE_NAME = f"{BASE_NAME}_{current_date_time}"
    env = initialize(game_ins)
    #env = Monitor(env, log_dir)
    #eval_env = initialize(game_ins)
    #eval_callback = EvalCallback(eval_env, best_model_save_path="./logs/",
    #                        log_path="./logs/", eval_freq=500, deterministic=True, render=False)
    model_file = get_latest_file(MODEL_SAVE_FOLDER_PATH)
    if model_file is not None:
        print('retraining')
        #model = DQN.load(model_file, verbose=1, device='cuda')
        model = PPO.load(model_file, 
                         verbose=1, 
                         device='cuda',
                         learning_rate=0.0003, #0.0003 
                         n_steps=2048, 
                         batch_size=128, #64 
                         n_epochs=10, 
                         gamma=0.99, 
                         gae_lambda=0.95, 
                         clip_range=0.2,
                         ent_coef=0.0, 
                         vf_coef=0.5, 
                         max_grad_norm=0.5, 
                         use_sde=False, 
                         sde_sample_freq=-1)
        model.set_env(env)
    else:
        #model = DQN("MlpPolicy", env, verbose=1, device="cuda", tensorboard_log=TENSORBOARD_LOG_NAME)
        model = PPO("MlpPolicy", env, 
                    verbose=1, 
                    device="cuda", 
                    tensorboard_log=TENSORBOARD_LOG_NAME)
    #callback = SaveOnBestTrainingRewardCallback(check_freq=1000, log_dir=log_dir)
    model.learn(total_timesteps=1000000, tb_log_name=MODEL_SAVE_NAME)

    #mean_reward, std_reward = evaluate_policy(model, env, n_eval_episodes=100)
    #print(f"mean_reward:{mean_reward:.2f} +/- {std_reward:.2f}")
    if not os.path.exists(MODEL_SAVE_FOLDER_PATH):
        os.makedirs(MODEL_SAVE_FOLDER_PATH)

    model.save(os.path.join(MODEL_SAVE_FOLDER_PATH, MODEL_SAVE_NAME)) 
    #model.save(MODEL_SAVE_NAME)

def get_current_date_time():
    current_date_time = datetime.datetime.now()
    formatted_date_time = current_date_time.strftime("%Y-%m-%d_%H-%M-%S")
    return formatted_date_time

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
        return None