import gym
# from gymnasium import spaces
import numpy as np
from pathlib import Path
from typing import List
import csv
import pygame
from .. import level
from ..settings import GameWindow
# from ..constants import ItemType

_SCREEN = pygame.display.set_mode((GameWindow.SCREEN_WIDTH.value, GameWindow.SCREEN_HEIGHT.value))
_MAP_FOLDER = "maps"
_CLOCK = pygame.time.Clock()
_TIMER_DURATION = 300
_WHITE_FONT_TEXT = (255, 255, 255)


class BombermanGameEnv(gym.Env):
    def __init__(self):
        self.level_maps = _get_all_levels()
        self.level = level.Level(self.level_maps[1 - 1], _SCREEN, 1)  # Create an instance of the Level class
        self.action_space = gym.spaces.Discrete(6)  # Example: Six possible actions
        # initial_observation = {
        #     "grid": np.zeros((13, 31, 1)),  # Initialize the grid with zeros
        #     "player_position": 0,  # Initialize the player position
        #     "bomb_status": 0,
        #     "enemy_positions": np.zeros((3, 0, 0))  # Initialize the enemy positions with zeros
        # }
        # initial_observation = gym.spaces.Dict({
        #     "grid": gym.spaces.Box(low=0, high=1, shape=(416,)),
        #     "player_position": gym.spaces.Box(low=0, high=1, shape=(2,)),
        #     "bomb_position": gym.spaces.Box(low=0, high=1, shape=(2,)),
        #     "enemy_positions": gym.spaces.Box(low=0, high=1, shape=(3,2,))
        # })
        # self.observation_space = initial_observation
        self.observation_space = gym.spaces.Box(low=0, high=255, shape=(416,), dtype=int)
        # self.seed()
        # self.reset()

    # def seed(self, seed=None):
    #     self.np_random, seed = seeding.np_random(seed)
    #     return [seed]

    def reset(self):
        # self.level.load_level()  # Load a new level
        self.level.reset()  # Reset the level
        # return self.level.initial_obs()
        return self.level.get_observation()  # Return the initial observation

    def step(self, action):
        # assert self.action_space.contains(action), "Invalid action"

        self.level.update_by_agent(action)  # Update the level based on the action
        reward = self.level.get_reward()  # Get the reward
        done = self.level.is_done()  # Check if the episode is done
        observation = self.level.get_observation()  # Get the new observation
        print(done)
        self.render()
        return observation, reward, done, {}

    def render(self, mode='human'):
        pygame.init()
        pygame.display.set_caption("Smart-Bomberman-Training")
        # level_maps = _get_all_levels()
        # self.level = level.Level(level_maps[1 - 1], _SCREEN, 1)
        font = pygame.font.Font(pygame.font.get_default_font(), 18)
        extra_time = 0
        # while True:
        time_remaining = 0
        # time_remaining = max(0, _TIMER_DURATION + extra_time - pygame.time.get_ticks() // 1000)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()

        enemies_alive = self.level.get_enemy_count()
        if self.level.player_hit_gateway:
            pygame.time.wait(1000)
            _endgame_screen(font, time_remaining, enemies_alive)
            pygame.display.update()
            # continue
        if self.level.player_hit_enemy or self.level.player_hit_explosion: # or time_remaining == 0:
            pygame.time.wait(1000)
            _endgame_screen(font, time_remaining, enemies_alive)
            pygame.display.update()
            # continue
        # if self.level.player_hit_item:
        #     if self.level.item_class == ItemType.EXTRA_TIME.value:
        #         extra_time += 50
        #     level_map.player_hit_item = False
        timer_text = font.render(f'Time Remaining: {time_remaining}', True, _WHITE_FONT_TEXT)
        _SCREEN.fill((128, 128, 128))  # fill bg with grey color
        _SCREEN.blit(timer_text, (10, 10))
        self.level.run()
        _CLOCK.tick(60)
        pygame.display.update()

    def close(self):
        pygame.quit()


def _get_all_levels() -> List:
    """Read  and store different maps."""
    map_path = Path.cwd().joinpath(_MAP_FOLDER)
    available_level_files = list(map_path.iterdir())
    all_maps = []
    for level_file in available_level_files:
        with open(level_file, newline='', encoding="utf-8-sig") as file:
            reader = csv.reader(file)
            all_maps.append(list(reader))
    return all_maps


def _endgame_screen(font, time_remaining, enemies_alive):
    """Endgame screen once player is killed."""
    _SCREEN.fill("black")
    # text_to_render = ""
    if enemies_alive > 0:
        text_to_render = "GAMEOVER"
    else:
        text_to_render = "You have killed all the enemies!! <3"
    gameover_text = font.render(text_to_render, True, _WHITE_FONT_TEXT)
    if time_remaining == 0:
        time_up_text = font.render("You ran out of time!", True, _WHITE_FONT_TEXT)
        _SCREEN.blit(time_up_text, (150, 200))
    _SCREEN.blit(gameover_text,  (150, 150))
