import gymnasium as gym
from gymnasium import spaces
import pygame
import sys
import csv
from typing import List
from pathlib import Path
import numpy as np
from . import level
from .settings import GameWindow
from .constants import ItemType

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

_SCREEN = pygame.display.set_mode((GameWindow.SCREEN_WIDTH.value, GameWindow.SCREEN_HEIGHT.value))
_MAP_FOLDER = "maps"
_ITEM_COLOR = [(0, 0, 255), (255, 0, 0), (255, 255, 0)]

class BBMEnv(gym.Env):
  """Custom Environment that follows gym interface"""
  metadata = {'render_modes': ['human'], "render_fps": 4}

  def __init__(self, render_mode=None, level_mode: int = 1):
    super(BBMEnv, self).__init__()
    # Define action and observation space

    self.level_mode = level_mode

    self.action_space = spaces.Discrete(6)
    self.observation_space = spaces.Dict(
            {
                "agent": spaces.Box(0, 33, shape=(2,), dtype=int),
                "target": spaces.Box(0, 33,shape=(2,), dtype=int),
                "num_enemies" : spaces.Box(0, 3, dtype=int),
                "bomb" : spaces.Box(0, 1, dtype=int),
                "bomb_loc" : spaces.Box(0, 33, shape=(2,), dtype=int),
                "agent_idle" : spaces.Box(0, 1, dtype=int),
                "enemies_loc" : spaces.Box(0, 33, shape=(3,2), dtype=int),
            }
        )
    
    assert render_mode is None or render_mode in self.metadata["render_modes"]
    self.render_mode = render_mode



  def _get_obs(self):
        #return {"agent": self._agent_location, "target": self._target_location, "num_enemies": self._num_enemies, "bomb": self._bomb, "bomb_loc": self._bomb_loc, "agent_idle": self._idle}
        return {"agent": self._agent_location, "target": self._target_location, "num_enemies": self._num_enemies, "bomb": self._bomb, "bomb_loc": self._bomb_loc, "agent_idle": self._idle, "enemies_loc":self._enemies_loc}
  


  def _get_info(self):
        return {}



  def step(self, action):
    
    reward = 0.0
    terminated = False
    truncated = False
    self.level_map.enemy_damage == False
    self.level_map.player_hit_explosion = False
    self.level_map.player_hit_enemy = False
    self.level_map.player_hit_hor = False
    self.level_map.player_hit_ver = False
    self.level_map.set_train_in(action)

    if self.render_mode == "human":
       self.render()

    self._num_enemies = np.array([self.level_map.get_enemy_count()])
    self._bomb = np.array([self.level_map.check_bomb_in_map()])
    self._bomb_loc = np.array([self.level_map.get_bomb_loc()[0], self.level_map.get_bomb_loc()[1]])
    self._idle = np.array([self.level_map.check_idle()])

    if len(self.level_map.get_enemies_location()) == 0:
        ene_np = np.array([[0,0],[0,0],[0,0]])
    if len(self.level_map.get_enemies_location()) == 1:
        ene_np = np.array([[self.level_map.get_enemies_location()[0][0],self.level_map.get_enemies_location()[0][1]],[0,0],[0,0]])
    if len(self.level_map.get_enemies_location()) == 2:
        ene_np = np.array([[self.level_map.get_enemies_location()[0][0],self.level_map.get_enemies_location()[0][1]],[self.level_map.get_enemies_location()[1][0],self.level_map.get_enemies_location()[1][1]],[0,0]])
    if len(self.level_map.get_enemies_location()) == 3:
        ene_np = np.array([[self.level_map.get_enemies_location()[0][0],self.level_map.get_enemies_location()[0][1]],[self.level_map.get_enemies_location()[1][0],self.level_map.get_enemies_location()[1][1]],[self.level_map.get_enemies_location()[2][0],self.level_map.get_enemies_location()[2][1]]])
    self._enemies_loc = ene_np

    if self._bomb == 1:
        reward += 0.05 # 0.02

    if self.level_map.player_hit_explosion:
            # reward -= 0.1
            terminated = True

    if self.level_map.player_hit_enemy:
            reward -= 0.1
            terminated = True
    


    # if self.level_map.player_hit_hor:
    #         reward -= 0.001

    # if self.level_map.player_hit_ver:
    #         reward -= 0.001

    if self.times % 8000 == 0:
        truncated = True

    # if self.times > 500:
    #     reward += 0.001
    # if self.times > 1000:
    #     reward += 0.005
    # if self.times > 2500 and self.times < 2700:
    #     reward += 0.01
    # if self.times > 5000 and self.times < 5200:
    #     reward += 0.02
    
    if self.level_map.enemy_damage == True:
        reward += 10.0

    # if self._num_enemies == 2:
    #     reward += 0.001
    
    # if self._num_enemies == 1:
    #     reward += 0.002

    # if self._num_enemies == 0:
    #     reward += 0.003


    if self._idle == 1:
        reward -= 0.5

    self._agent_location = np.array([self.level_map.get_player_location_on_map()[0], self.level_map.get_player_location_on_map()[1]])
    self.dist_to_bomb = np.linalg.norm(np.subtract(self._agent_location, self._bomb_loc), ord=1)

    if self.dist_to_bomb == 2.0:
        reward -= 0.025
    if self.dist_to_bomb <= 1.0:
        reward -= 0.05

    for i in range(3):
        dist_enemy = np.linalg.norm(np.subtract(self._agent_location, self._enemies_loc[i]), ord=1)
        if dist_enemy == 4.0:
            reward += 0.0125
        if dist_enemy == 3.0:
            reward += 0.025
        if dist_enemy == 2.0:
            reward += 0.05
        if dist_enemy <= 1.0:
            reward -= 0.05

    # self.dist = np.linalg.norm(np.subtract(self._agent_location, self._target_location), ord=1)
    # if self.dist < 25.00 and self.dist > 20.00:
    #     reward += 0.05
    # if self.dist < 20.00 and self.dist > 15.00:
    #     reward += 0.1
    # if self.dist < 15.00 and self.dist > 10.00:
    #     reward += 0.2
    # if self.dist < 10.00 and self.dist > 5.00:
    #     reward += 0.5
    # if self.dist < 5.00 and self.dist > 2.00:
    #     reward += 0.6
    # if self.dist < 2.00 and self.dist > 1.00:
    #     reward += 0.8

    # if (np.equal(self._agent_location, self._target_location)[0] == True) and (np.equal(self._agent_location, self._target_location)[1] == True):
    #     reward += 1.0
    #     terminated = True

    # if self.level_map.get_enemy_count() == 0:
    #     self._agent_location = np.array([self.level_map.get_player_location_on_map()[0], self.level_map.get_player_location_on_map()[1]])

    #     self.dist = np.linalg.norm(np.subtract(self._agent_location, self._target_location), ord=1)
        
    #     # if self.dist < 25.00 and self.dist > 20.00:
    #     #     reward += 0.05
    #     # if self.dist < 20.00 and self.dist > 15.00:
    #     #     reward += 0.1
    #     # if self.dist < 15.00 and self.dist > 10.00:
    #     #     reward += 0.2
    #     # if self.dist < 10.00 and self.dist > 5.00:
    #     #     reward += 0.5
    #     # if self.dist < 5.00 and self.dist > 1.00:
    #     #     reward += 0.6
    #     # if self.dist < 1.00:
    #     #     reward += 0.8

    #     if (np.equal(self._agent_location, self._target_location)[0] == True) and (np.equal(self._agent_location, self._target_location)[1] == True):
    #         reward += 1.0
    #         terminated = True

    # print(reward)

    observation = self._get_obs()
    info = self._get_info()

    return observation, reward, terminated, truncated, info





  def reset(self, seed=None, options =None):

    super().reset(seed=seed,options=options)
    # Reset the state of the environment to an initial state

    pygame.init()
    pygame.display.set_caption("Smart-Bomberman")
    self.times = 0

    self.font = pygame.font.Font(pygame.font.get_default_font(), 18)
    self.extra_time = 0
    self.item_start = [0, 0, 0, 0]
    self.item_seconds = [0, 0, 0, 0]
    self.item_text = [self.font.render('', True, 0), self.font.render('', True, 0), self.font.render('', True, 0)]
    self.item_duration = 15
    self.level_maps = _get_all_levels()
    
    assert len(self.level_maps[self.level_mode - 1]) == 13 and len(self.level_maps[self.level_mode - 1][0]) == 32

    self.level_map = level.Level(self.level_maps[self.level_mode - 1], _SCREEN, self.level_mode)
    self.dist= np.int64(0)

    self._agent_location = np.array([self.level_map.get_player_location_on_map()[0], self.level_map.get_player_location_on_map()[1]])
    self._target_location = np.array([self.level_map.get_gateway_index()[0]/32, self.level_map.get_gateway_index()[1]/32])
    self._num_enemies = np.array([self.level_map.get_enemy_count()])
    self._bomb = np.array([self.level_map.check_bomb_in_map()])
    self._bomb_loc = np.array([self.level_map.get_bomb_loc()[0], self.level_map.get_bomb_loc()[1]])
    self._idle = np.array([self.level_map.check_idle()])
    ene_np = np.array([[self.level_map.get_enemies_location()[0][0],self.level_map.get_enemies_location()[0][1]],[self.level_map.get_enemies_location()[1][0],self.level_map.get_enemies_location()[1][1]],[self.level_map.get_enemies_location()[2][0],self.level_map.get_enemies_location()[2][1]]])
    self._enemies_loc = ene_np

    observation = self._get_obs()
    info = self._get_info()

    if self.render_mode == "human":
        self.render()

    return observation, info    




  def render(self):
    # Render the environment to the screen
    self.times += 1
    self.level_map.enemy_damage = False

    if self.level_map.player_hit_item:
        if self.level_map.item_class == ItemType.EXTRA_TIME.value:
            self.extra_time += 30
        for i in ItemType:
            if self.level_map.item_class == i.value:
                self.item_start[i.value] = pygame.time.get_ticks()
            elif self.level_map.item_class == ItemType.EXTRA_TIME.value:
                continue
        self.level_map.player_hit_item = False
        
    self.timer_text = self.font.render(f'Time Remaining: 0', True, (255, 255, 255))
    for i in ItemType:
        if i.value == ItemType.EXTRA_TIME.value:
            continue
        self.item_seconds[i.value] = (pygame.time.get_ticks() - self.item_start[i.value])  // 1000
        if self.item_start[i.value] == 0:
            self.item_text[i.value] = self.font.render('', True, 0)
        else:
            if self.item_seconds[i.value] > self.item_duration:
                if i.value == ItemType.SKATE.value:
                    level.Level.player_hit_skate = False
                elif i.value == ItemType.BOMB.value:
                    level.Level.player_hit_bomb_length = False
                elif i.value == ItemType.INVINCIBLE.value:
                    self.level_map.player_hit_invincible = False
                self.item_start[i.value] = 0
            remain = self.item_duration - self.item_seconds[i.value]
            self.item_text[i.value] = self.font.render(f'{i.name}: {remain}', True, _ITEM_COLOR[i.value])
    _SCREEN.fill((128, 128, 128)) #fill bg with grey color
    _SCREEN.blit(self.timer_text, (10, 10))
    for i in ItemType:
        if i.value == ItemType.EXTRA_TIME.value:
            continue
        _SCREEN.blit(self.item_text[i.value], (220 + 120*i.value, 10))

    self.level_map.run()
    pygame.display.update()


    