import pygame
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from ..settings import Game
from ..constants import PlayerAction, GameFinalState
import math

class SmartBombermanEnv(gym.Env):
    #metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 120}
    
    def __init__(self, game, render_mode=None):
        self.game = game
        self.observation_space = spaces.Box(low=0, high=15,
                                            shape=(self.game.level_map.num_cols*self.game.level_map.num_rows, ), 
                                            dtype=int) 
        #self.observation_space = spaces.Dict(
        #    {
        #        "player_1": spaces.Box(0, self.game.level_map.num_cols - 1, shape=(2,), dtype=int),
        #        "enemy": spaces.Box(0, self.game.level_map.num_cols - 1, shape=(2,), dtype=int)
        #    }
        #)

        self.action_space = spaces.Discrete(6)
        self.action_to_playeraction = {
            0 : PlayerAction.UP,
            1 : PlayerAction.DOWN,
            2 : PlayerAction.LEFT,
            3 : PlayerAction.RIGHT,
            5 : PlayerAction.BOMB,
            4 : PlayerAction.WAIT
        }

        #stuff needed to render frame
        self.font = pygame.font.Font(pygame.font.get_default_font(), 18)
        self.extra_time = 0
        self.item_start = [0, 0, 0]
        self.item_seconds = [0, 0, 0]
        self.item_text = [self.font.render('', True, 0), self.font.render('', True, 0), self.font.render('', True, 0)]
        self.item_duration = 15
        self.stuck_step_counter = 0
        self.player_stuck = False

    def _get_obs(self):
        #print(self.game.level_map.abstract_map_data)
        #player_position = np.argwhere(np.isin(self.game.level_map.abstract_map_data, [4, 11, 13, 14, 15]))[0]
        #print(player_position)
        #self.game.level_map.abstract_map_data_flatten =  self.game.level_map.abstract_map_data.flatten()
        #player_pos = np.where(self.game.level_map.abstract_map_data_flatten == 4)[0][0]

        #subset_start = max(0, player_pos - 10)
        #subset_end = min(player_pos + 11, len(self.game.level_map.abstract_map_data_flatten))

        # Extract the subset
        #subset_data = self.game.level_map.abstract_map_data_flatten[subset_start:subset_end]
        #min_value = np.min(self.game.level_map.abstract_map_data_flatten)
        #max_value = np.max(self.game.level_map.abstract_map_data_flatten)
        #print(self.game.level_map.abstract_map_data_window)
        #normalized_observation_space = (self.game.level_map.abstract_map_data_flatten - min_value) / (max_value - min_value)
        #enemy = self.game.level_map.bomberman_enemy.sprites()[0]
        #obs = { 
        #        "player_1" : self.game.level_map.get_abstract_player_location_on_map(), 
        #        "enemy": self.game.level_map. get_abstract_location_on_map(enemy.abstract_rect)
        #      }
        obs = self.game.level_map.abstract_map_data.flatten()
        #print(self.game.level_map.abstract_map_data) 
        return obs
    
    def reset(self, seed=None, options=None):
        self.stuck_step_counter = 0
        super().reset(seed=seed)
        #print("reset")
        self.game.reset_game()
        self.render()
        observation = self._get_obs()
        self.player_stuck = False
        return observation, dict()
    
    def step(self, action):
        #print(self.action_to_playeraction[action])
        self.stuck_step_counter += 1
        terminated = False
        truncated = False
        reward = 0
        self.game.level_map.bomberman_player.sprite.perform_player_input_for_AI_agent(self.action_to_playeraction[action])
        self.render()
        if self.game.level_map.is_player_out_of_bounds:
            truncated = True
        #if action != 4 and action != 5:
        #    if self.game.level_map.horizontal_collision() or self.game.level_map.vertical_collision():
        #       reward -= 10

        if self.game.level_map.horizontal_collision() or self.game.level_map.vertical_collision():
            self.stuck_step_counter += 1
        else:
            self.stuck_step_counter = 0
        
        #reward structure for placing bombs only near breakable walls
        #for bomb in self.game.level_map.bomberman_player.sprite.bombs:
        #    #print(bomb.sprite.number_of_breakable_walls_in_expl_range)
        #    #an example of delayed reward as in the rewards are given not when the bomb is placed but when it explodes
        #    #the below condition will also ensure that if player places a bomb near a breakable tile but the bomb hasnt
        #    #exploded we dont negatively reward the agent (that would be wrong)
        #        print(bomb.sprite.number_of_breakable_walls_in_expl_range)
        #        if bomb.sprite.number_of_breakable_walls_in_expl_range == 0:
        #            reward -= 100 #penalize if a bomb is not placed near a breakable wall
        #        else:
        #           #increase reward is bomb is placed near more breakable walls
        #           reward += bomb.sprite.number_of_breakable_walls_in_expl_range*30
            
        """ if action == 4:
            for bomb in self.game.level_map.bomberman_player.sprite.bombs:
                if bomb.sprite.number_of_breakable_walls_in_expl_range == 0:
                    reward -= 250 #penalize if a bomb is not placed near a breakable wall
                else:
                    #increase reward is bomb is placed near more breakable walls
                    reward += bomb.sprite.number_of_breakable_walls_in_expl_range*90 """

        #reward structure for player moving towards enemies
        current_player_pos = self.game.level_map.get_abstract_player_location_on_map()
        is_player_in_bomb_danger = self.game.level_map.is_player_in_bomb_range()
        if not is_player_in_bomb_danger:
            shortest_distance_to_enemies = self.game.level_map.find_shortest_path_to_enemies_from_player()
            if len(shortest_distance_to_enemies) != 0:
                nearest_enemy_dist = min(shortest_distance_to_enemies)
                #print(nearest_enemy_dist)
                if action == 4:
                    reward = -90
                elif self.stuck_step_counter > 50:
                    #print('derewarding because in same position')
                    reward = -80
                else:
                    if nearest_enemy_dist != 0:
                        reward = int((1/(nearest_enemy_dist+1e-6))*2000)
                        #reward = 200
                    else:
                        reward = 500
                        #reward = -int(nearest_enemy_dist)
                    #elif nearest_enemy_dist <= 2:
                    #    if action == 4:
                    #        reward += 500
        
        #reward for placing bombs to kill enemies
        #more enemies killed with a bomb, better the reward
        """ is_player_in_bomb_danger = self.game.level_map.is_player_in_bomb_range()
        if not is_player_in_bomb_danger:
            number_of_enemies_in_expl_range = self.get_number_of_enemies_in_expl_range()
            #print(number_of_enemies_in_expl_range)
            for num_enemies in number_of_enemies_in_expl_range:
                reward += num_enemies*50 """

        #reward structure for player moving away from bombs
        #is_player_in_bomb_danger = self.game.level_map.is_player_in_bomb_range()
        #if is_player_in_bomb_danger:
        is_player_in_bomb_danger = self.game.level_map.is_player_in_bomb_range()
        if action != 5 and is_player_in_bomb_danger:
            if len(self.game.level_map.get_distance_of_player_from_bombs()) != 0:
                closest_bomb_distance = min(self.game.level_map.get_distance_of_player_from_bombs())
                #print(closest_bomb_distance)
                if closest_bomb_distance == 0:
                    reward -= 200
                else:
                    reward = 0
                    reward -= int((1/closest_bomb_distance)*1000)
                    #reward += closest_bomb_distance*10
        
        if self.game.game_final_state == GameFinalState.WIN:
            terminated = True
            #reward += 100
        elif self.game.game_final_state == GameFinalState.LOSE:
            terminated = True
            reward -= 200

        observation = self._get_obs()
        print(f'reward: {reward}')
        return observation, reward, terminated, truncated, dict()
    
    def get_number_of_enemies_in_expl_range(self):
        number_of_enemies_in_expl_range_of_all_bombs = []
        top_tile_check = True
        bottom_tile_check = True
        left_tile_check = True
        right_tile_check = True
        bomb_range = self.game.level_map.bomberman_player.sprite.bomb_range
        for bomb in self.game.level_map.bomberman_player.sprite.bombs:
            num_enemies_in_one_bomb_range = 0
            if bomb.sprite.has_bomb_exploded:
                bomb_pos = [bomb.sprite.rect.x, bomb.sprite.rect.y]
                for i in range(1, bomb_range+1):
                    # top explosion tile
                    if ( top_tile_check and
                        self._can_explosion_happen_on_tile([bomb_pos[0]-i*Game.TILE_SIZE.value,bomb_pos[1]])):
                        if self._is_explosion_on_enemy([bomb_pos[0]-i*Game.TILE_SIZE.value,bomb_pos[1]]):
                            num_enemies_in_one_bomb_range += 1
                    else:
                        top_tile_check = False
                    # bottom explosion tile
                    if ( bottom_tile_check and
                        self._can_explosion_happen_on_tile([bomb_pos[0]+i*Game.TILE_SIZE.value,bomb_pos[1]])):
                        if self._is_explosion_on_enemy([bomb_pos[0]+i*Game.TILE_SIZE.value,bomb_pos[1]]):
                            num_enemies_in_one_bomb_range += 1
                    else:
                        bottom_tile_check = False
                    # right explosion tile
                    if ( right_tile_check and
                        self._can_explosion_happen_on_tile([bomb_pos[0],bomb_pos[1]+i*Game.TILE_SIZE.value])):
                        if self._is_explosion_on_enemy([bomb_pos[0],bomb_pos[1]+i*Game.TILE_SIZE.value]):
                            num_enemies_in_one_bomb_range += 1
                    else:
                        right_tile_check = False
                    # left explosion tile
                    if ( left_tile_check and
                        self._can_explosion_happen_on_tile([bomb_pos[0],bomb_pos[1]-i*Game.TILE_SIZE.value])):
                        if self._is_explosion_on_enemy([bomb_pos[0],bomb_pos[1]-i*Game.TILE_SIZE.value]):
                            num_enemies_in_one_bomb_range += 1
                    else:
                        left_tile_check = False
                number_of_enemies_in_expl_range_of_all_bombs.append(num_enemies_in_one_bomb_range)
        return number_of_enemies_in_expl_range_of_all_bombs
    
    def _can_explosion_happen_on_tile(self, explosion_pos):
        for wall in self.game.level_map.walls:
            if wall.rect.x == explosion_pos[0] and wall.rect.y == explosion_pos[1]:
                if wall.destroyable:
                    return True
        return False 
    
    def _is_explosion_on_enemy(self, explosion_pos):
        for enemy in self.game.level_map.bomberman_enemy:
            if (((enemy.rect.x-explosion_pos[0])**2) + ((enemy.rect.y-explosion_pos[1])**2)) <= 1:
                return True
        return False


    
    def render(self):
        self.game.render_frame(self.font, self.extra_time, self.item_start, 
                               self.item_seconds, self.item_text, self.item_duration)