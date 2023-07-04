"""Setting up the players,obstacles and enemies in different maps."""
from typing import List
import random
import math
from collections import deque

import numpy as np
import pygame
from . import tile
from . import player
from . import enemy
from . import item
from . import gateway
from .settings import Game
from .constants import Camera, PlayerBomberman, ItemType, TileType
from .constants import Camera, PlayerBomberman, ItemType
import math

class Level:
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods
    """
    Storing and graphically setting up the map for each level.

    """

    player_hit_skate = False
    level_bombs: pygame.sprite.Group = pygame.sprite.Group()

    def __init__(self, level_data: List, surface: pygame.Surface, level_number: int):
        """
        Parameters
        ----------
        level_data: List
            The Map layout for a level
        """
        self.display_surface = surface
        self.map_data = level_data
        self.level_number = level_number
        self.setup_level(level_data)
        self.player_hit_enemy = False
        self.player_hit_item = False
        self.player_hit_explosion = False
        self.player_hit_gateway = False
        self.gateway_flag = False
        self.level_shift = (0,0)
        self.shift_accumulated = [0,0]
        self.item_class = 0
        # store data for resetting level
        self.initial_surface = surface
        self.initial_map_data = level_data
        self.initial_level_number = level_number
        # agent action
        self.agent_action = 5  # initial action is WAIT
        # collision detection for rewards
        self.agent_collided_horizontal = False
        self.agent_collided_vertical = False
        self.player_location_track = deque()
        self.bombing_possibility = 0.0
        self.all_positions_of_player = {}
        for i in range(32):
            for j in range(14):
                self.all_positions_of_player[tuple((i,j))] = 0

    def setup_level(self, layout: List):
        """
        Setup up the map for a level.

        Parameters
        ----------
        layout: List
            The Map layout

        """
        self.walls: pygame.sprite.Group = pygame.sprite.Group()
        self.bomberman_player: pygame.sprite.GroupSingle = pygame.sprite.GroupSingle()
        self.bomberman_enemy: pygame.sprite.Group = pygame.sprite.Group()
        self.items: pygame.sprite.Group = pygame.sprite.Group()
        self.gateway: pygame.sprite.GroupSingle = pygame.sprite.GroupSingle()
        locations_for_enemy = self.get_locations_for_enemy(layout)
        location_for_player = self.get_location_for_player(layout)
        self.unavailable_locations = self.unavailable_locations_for_enemy(layout)
        # TODO: Remove after training
        ctr_flg = 1  # For enenmy to be 1, need to be removed
        locations_for_gateway = self.get_locations_for_gateway(layout)
        self.gateway_index = []
        for row_index, row in enumerate(layout):
            for column_index, column in enumerate(row):
                y_position = row_index * Game.TILE_SIZE.value
                x_position = column_index * Game.TILE_SIZE.value
                if column in ('W', '#'):
                    wall = tile.Tile((x_position, y_position), False, TileType.NONE)
                    self.walls.add(wall)
                #if column == 'B':
                if column.startswith('B'):
                    tile_type = column.split('_')[1]
                    if tile_type == '1':
                        wall = tile.Tile(
                                            (x_position, y_position),
                                            True,
                                            TileType.ONE_EXPLOSION_BOMB
                                         )
                    elif tile_type == '2':
                        wall = tile.Tile((x_position, y_position), True, TileType.TWO_EXPLOSION)
                    self.walls.add(wall)
                if column == 'I':
                    prob = random.random()
                    if prob < 0.5:
                        powerup = item.Item((x_position, y_position), ItemType.EXTRA_TIME.value)
                    else:
                        powerup = item.Item((x_position, y_position), ItemType.SKATE.value)
                    self.items.add(powerup)
                    wall = tile.Tile((x_position, y_position), True, TileType.ONE_EXPLOSION_NO_BOMB)
                    self.walls.add(wall)
                # TODO: Remove for random spawning
                # if column == 'P':
                if (row_index, column_index) == location_for_player:
                    self.bomberman_player.add(player.Player(
                                                                (x_position, y_position),
                                                                self.walls,
                                                                self.display_surface
                                                            ))
                if (row_index, column_index) in locations_for_enemy and ctr_flg < 3:
                    self.bomberman_enemy.add(enemy.Enemy((x_position, y_position),
                                                         self.level_number))
                    ctr_flg += 1
                if (row_index, column_index) in locations_for_gateway:
                    self.gateway_index.append(x_position)
                    self.gateway_index.append(y_position)

    def scroll(self):
        """
        Simulates the camera movement via level scrolling mechanism
        """
        bomberman_player = self.bomberman_player.sprite
        player_x = bomberman_player.rect.centerx
        direction_x = bomberman_player.direction.x
        player_y = bomberman_player.rect.centery
        direction_y = bomberman_player.direction.y
        is_scroll_to_be_added = False

        if player_x < Camera.CAMERA_X_LIMIT_LEFT.value and direction_x < 0:
            #if player has reached left end of screen and wants to keep moving left
            self.level_shift = (PlayerBomberman.SPEED.value,0)
            bomberman_player.speed = 0
            is_scroll_to_be_added = True
        elif player_x > Camera.CAMERA_X_LIMIT_RIGHT.value and direction_x > 0:
            #if player has reached right end of screen and wants to keep moving right
            self.level_shift = (-PlayerBomberman.SPEED.value,0)
            bomberman_player.speed = 0
            is_scroll_to_be_added = True
        elif player_y < Camera.CAMERA_Y_LIMIT_TOP.value and direction_y < 0:
            #if player has reached top end of screen and wants to keep moving top
            self.level_shift = (0,PlayerBomberman.SPEED.value)
            bomberman_player.speed = 0
            is_scroll_to_be_added = True
        elif player_y > Camera.CAMERA_Y_LIMIT_BOTTOM.value and direction_y > 0:
            #if player has reached bottom end of screen and wants to keep moving down
            self.level_shift = (0,-PlayerBomberman.SPEED.value)
            bomberman_player.speed = 0
            is_scroll_to_be_added = True
        else:
            #if the player is within limits of screen - no scroll needed
            self.level_shift = (0,0)
            bomberman_player.speed = PlayerBomberman.SPEED.value
            is_scroll_to_be_added = False
        if is_scroll_to_be_added:
            bomberman_player.level_shifted[0] += self.level_shift[0]
            bomberman_player.level_shifted[1] += self.level_shift[1]

    def horizontal_collision(self):
        """
        Handles player collision in horizontal direction
        """
        bomberman_player = self.bomberman_player.sprite

        #move the player horizontally
        bomberman_player.rect.x += bomberman_player.direction.x * bomberman_player.speed

        #detect collision with all game tiles in horizontal direction
        for sprite in self.walls.sprites():
            if sprite.rect.colliderect(bomberman_player.rect):
                if bomberman_player.direction.x < 0:
                    #if player collides with a tile and was moving left,
                    #set the player to right of collider
                    bomberman_player.rect.left = sprite.rect.right
                    self.agent_collided_horizontal = True
                elif bomberman_player.direction.x > 0:
                    #if player collides with a tile and was moving right,
                    #set the player to left of collider
                    bomberman_player.rect.right = sprite.rect.left
                    self.agent_collided_horizontal = True

    def vertical_collision(self):
        """
        Handles player collision in vertical direction
        """
        bomberman_player = self.bomberman_player.sprite

        #move the player vertically
        bomberman_player.rect.y += bomberman_player.direction.y * bomberman_player.speed

        #detect collision with all game tiles in vertical direction
        for sprite in self.walls.sprites():
            if sprite.rect.colliderect(bomberman_player.rect):
                if bomberman_player.direction.y < 0:
                    #if player collides with a tile and was moving top,
                    #set the player to bottom of collider
                    bomberman_player.rect.top = sprite.rect.bottom
                    self.agent_collided_vertical = True
                elif bomberman_player.direction.y > 0:
                    #if player collides with a tile and was moving down,
                    #set the player to top of collider
                    bomberman_player.rect.bottom = sprite.rect.top
                    self.agent_collided_vertical = True

    def player_collides_with_explosion(self):
        """Check for player collision with explosion"""
        for bomb in self.bomberman_player.sprite.bombs:
            for explosion in bomb.sprite.explosions:
                if explosion.sprite.rect.colliderect(self.bomberman_player.sprite.rect):
                    self.player_hit_explosion = True
        for bomb in Level.level_bombs:
            for explosion in bomb.explosions:
                if explosion.sprite.rect.colliderect(self.bomberman_player.sprite.rect):
                    self.player_hit_explosion = True


    def enemy_collides_with_explosion(self):
        """Check if any enemy is hit by the explosion"""
        for bomb in self.bomberman_player.sprite.bombs:
            for explosion in bomb.sprite.explosions:
                for enemy_sprite in self.bomberman_enemy.sprites():
                    if explosion.sprite.rect.colliderect(enemy_sprite) and \
                            not enemy_sprite.is_paused():
                        enemy_sprite.enemy_hit_by_bomb()
                        enemy_sprite.set_pause(30)

    def enemy_collision_reverse(self):
        """Redirect enemy after collision with wall."""
        for enemy_sprite in self.bomberman_enemy.sprites():
            if pygame.sprite.spritecollide(enemy_sprite,
                                           self.walls.sprites(),
                                           False):
                enemy_sprite.enemy_collision()

    def enemy_collides_with_player(self):
        """Check for enemy collision with player."""
        for enemy_sprite in self.bomberman_enemy.sprites():
            if enemy_sprite.rect.colliderect(self.bomberman_player.sprite.rect):
                self.player_hit_enemy = True

    def unavailable_locations_for_enemy(self, mapdata):
        """Extract spots on the map where enemy cannot be placed."""
        unavaiable_locations = []
        for row_index, row in enumerate(mapdata):
            for column_index, column in enumerate(row):
                if column in ('W', '#', 'B_1', 'B_2', 'I', 'P'):
                    unavaiable_locations.append((row_index, column_index))
        return unavaiable_locations

    def unavailable_locations_for_player(self, mapdata):
        """Extract spots on the map where enemy cannot be placed."""
        unavaiable_locations = []
        for row_index, row in enumerate(mapdata):
            for column_index, column in enumerate(row):
                if column in ('W', '#', 'B_1', 'B_2', 'I', 'E'):
                    unavaiable_locations.append((row_index, column_index))
        return unavaiable_locations

    def get_locations_for_enemy(self, mapdata):
        """Get all possible random spots where enemy can be placed."""
        median_row = int(len(mapdata)/2)
        median_col = int(len(mapdata[0])/2)
        unavailable_locations = self.unavailable_locations_for_enemy(mapdata)
        number_of_iterations = 50
        while number_of_iterations:
            enemy_start_locations = [
                (random.randint(median_row, len(mapdata) - 1),
                 random.randint(median_col, len(mapdata[0]) - 1))
                for i in range(0, 3)]
            locations_conflicted = [True for location in enemy_start_locations
                                    if location in unavailable_locations]
            if not locations_conflicted:
                break
            number_of_iterations = - 1
        return enemy_start_locations

    def get_location_for_player(self, mapdata):
        """Get all possible random spots where enemy can be placed."""
        unavailable_locations = self.unavailable_locations_for_player(mapdata)
        number_of_iterations = 50
        while number_of_iterations:
            player_start_locations = [
                (random.randint(4, len(mapdata) - 1),
                 random.randint(4, len(mapdata[0]) - 1))]
            locations_conflicted = [True for location in player_start_locations
                                    if location in unavailable_locations]
            if not locations_conflicted:
                break
            number_of_iterations = - 1
        return player_start_locations[0]

    def get_locations_for_gateway(self, mapdata):
        """Get all possible random spots where gateway can be placed."""
        unavailable_locations = self.unavailable_locations_for_enemy(mapdata)
        number_of_iterations = 50
        while number_of_iterations:
            gateway_locations = [
                (random.randint(2, len(mapdata) - 1),
                 random.randint(1, len(mapdata[0]) - 1))
                for i in range(0, 1)]
            locations_conflicted = [True for location in gateway_locations
                                    if location in unavailable_locations]
            if not locations_conflicted:
                break
            number_of_iterations = - 1
        return gateway_locations

    def item_collides_with_player(self):
        """Check for item collision with player."""
        for item_sprite in self.items.sprites():
            if item_sprite.rect.colliderect(self.bomberman_player.sprite.rect):
                self.player_hit_item = True
                self.item_class = item_sprite.item_num
                if self.item_class == ItemType.SKATE.value:
                    Level.player_hit_skate = True
                self.items.remove(item_sprite)

    def render_and_update_bombs(self):
        """render and update bombs placed by player in the level"""
        for bomb in self.bomberman_player.sprite.bombs:
            bomb.draw(self.display_surface)
            bomb.update(self.level_shift)

    #moved below code to bomb.py for better encapsulation, keep this commented here
    #in case we wanna undo anything
    #def render_and_update_explosions(self):
    #    """render and update explosions caused by bombs placed by player in the level"""
    #    for bomb in self.bomberman_player.sprite.bombs:
    #        for expl in bomb.sprite.explosions:
    #            expl.update(self.level_shift)
    #            expl.draw(self.display_surface)

    @staticmethod
    def _clean_up_level_bombs_after_explosion():
        """remove bombs which have been exploded from levels internal list"""
        for temp_bomb in Level.level_bombs.copy():
            if temp_bomb.has_explosion_ended:
                Level.level_bombs.remove(temp_bomb)

    def get_player_location_on_map(self) -> tuple:
        """Get the player's current location."""
        return round(self.bomberman_player.sprite.rect.x/32),\
               round(self.bomberman_player.sprite.rect.y/32)


    def get_enemy_count(self) -> int:
        """Get the number of enemies alive."""
        return len(self.bomberman_enemy.sprites())

    def set_gateway(self) :
        """Make a Gateway to next level when all enemies are killed"""
        self.gateway_index[0] += self.shift_accumulated[0]
        self.gateway_index[1] += self.shift_accumulated[1]
        self.gateway.add(gateway.Gateway(self.gateway_index))

    def gateway_collides_with_player(self):
        """Check for gateway collision with player."""
        for gateway_sprite in self.gateway.sprites():
            if gateway_sprite.rect.colliderect(self.bomberman_player.sprite.rect):
                self.player_hit_gateway = True

    def cheat_key(self):
        """cheat key for deleting all enemies"""
        # pylint: disable=no-member
        keys = pygame.key.get_pressed()
        if keys[pygame.K_0]:
            for enemy_sprite in self.bomberman_enemy.sprites():
                enemy_sprite.kill()

    def reset(self):
        """Reset the environment for the AI agent."""
        self.display_surface = self.initial_surface
        self.map_data = self.initial_map_data
        self.level_number = self.initial_level_number
        self.setup_level(self.map_data)
        self.player_hit_enemy = False
        self.player_hit_item = False
        self.player_hit_explosion = False
        self.player_hit_gateway = False
        self.gateway_flag = False
        self.level_shift = (0, 0)
        self.shift_accumulated = [0, 0]
        self.item_class = 0
        self.player_location_track = deque()
        self.bombing_possibility = 0.0

    def is_done(self) -> bool:
        """Check if enemy is alive or dead."""
        if self.player_hit_enemy or self.player_hit_explosion:
            return True
        return False

    def get_observation(self):
        """Get the current observation state space for AI."""
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        # pylint: disable=consider-using-in
        # pylint: disable=too-many-locals
        encoded_state = []
        encoded_state_loc = []
        bomb_present = 0
        bomb_explosion = 0
        self.bombing_possibility = 0
        for row in self.map_data:
            for column in row:
                if column == "X":
                    encoded_state_loc.append(1)
                elif column == "B_1" or column == "B_2":
                    encoded_state_loc.append(2)
                elif column == "E":
                    encoded_state_loc.append(3)
                elif column == "W":
                    encoded_state_loc.append(4)
                elif column == "#":
                    encoded_state_loc.append(5)
                else:
                    encoded_state_loc.append(0)

        while len(encoded_state_loc) < 416:
            encoded_state_loc.append(0)



        # Check for bomb nearby (Size 1 or 2)
        player_location = self.get_player_location_on_map()
        try:
            self.all_positions_of_player[player_location] += 1
        except:
            print(player_location)
        bomb_position = []
        for bomb in self.bomberman_player.sprite.bombs:
            bomb_present = 1
            bomb_location = tuple((round(bomb.sprite.rect.x / 32), round(bomb.sprite.rect.y / 32)))
            bomb_position.append(bomb_location)
            dist = math.dist(player_location, bomb_location)
            if dist < 5:
                encoded_state.append(1)
            else:
                encoded_state.append(0)
        # Possible that there can be two bombs (To avoid breaking the shape of the space)
        if len(encoded_state) == 1:
            encoded_state.append(0)

        # Check for enemies nearby (Size 3)
        enemy_loc = []
        for enemy_sprite in self.bomberman_enemy.sprites():
            enemy_location = enemy_sprite.get_location_on_map()
            enemy_loc.append(list(enemy_location))
            dist = math.dist(enemy_sprite.get_location_on_map(), player_location)
            if dist < 10:
                encoded_state.append(0.5)
            elif dist < 1:
                encoded_state.append(1.5)
                self.bombing_possibility = 1
            elif dist < 3:
                encoded_state.append(1)
                self.bombing_possibility = 0.6
            elif dist < 15:
                encoded_state.append(0.2)
            else:
                self.bombing_possibility = 0.3
                encoded_state.append(0)

        # Check for breakable walls nearby
        for wall in self.walls.sprites():
            if wall.tile_type == TileType.TWO_EXPLOSION\
                    or wall.tile_type == TileType.ONE_EXPLOSION_BOMB:
                wall_location = tuple((wall.rect.x/32, wall.rect.y/32))
                dist = math.dist(player_location, wall_location)
                if dist < 2:
                    encoded_state.append(1)
                elif dist < 4:
                    encoded_state.append(0.5)
                else:
                    encoded_state.append(0)

        # print(len(encoded_state))
        # Padding observation space to keep the shape uniform
        if len(encoded_state) < 20:
            iterator = 20 - len(encoded_state)
            while iterator:
                encoded_state.append(0)
                iterator -= 1

        if not bomb_position:
            bomb_position.append([0,0])
        if len(enemy_loc) < 3:
            enemy_loc.append([0,0])
        bomb_explosion_location = []
        for bomb in self.bomberman_player.sprite.bombs:
            for explosion in bomb.sprite.explosions:
                bomb_explosion = 1
                bomb_explosion_location.append(tuple((
                    round(explosion.sprite.rect.x / 32),
                    round(explosion.sprite.rect.y / 32)
                    ))
                )
        if not bomb_position:
            bomb_position.append([-1, -1])
        while len(enemy_loc) < 3:
            enemy_loc.append([-1, -1])
        while len(bomb_explosion_location) < 5:
            bomb_explosion_location.append([-1, -1])
        observation_space = {
            "grid": np.array(encoded_state_loc),
            "player_position": np.array(player_location),
            "bomb_position": np.array(bomb_position),
            "enemy_positions": np.array(enemy_loc),
            "bomb_explosion_location": np.array(bomb_explosion_location),
            "bomb_present": int(bomb_present),
            "explosion": int(bomb_explosion),
            "bombing_possibility": np.array([self.bombing_possibility])
        }
        return observation_space
        # return np.array(encoded_state_loc)

    def write_map_data(self):
        """Write map data to local disk for debug purpose."""
        # file = "map_loc.txt"
        with open("map_loc.txt", "w", encoding="utf-8") as file:
            for row_data in self.map_data:
                file.write("\t".join(row_data))
                file.write("\n")

    def update_map_data(self):
        """Update the current map data."""
        enemy_locations = []
        for enemy_loc in self.bomberman_enemy.sprites():
            enemy_locations.append(enemy_loc.get_location_on_map())
        player_location = self.get_player_location_on_map()
        updated_map = []
        for row in self.map_data:
            updated_row = [" " if row_value in ('E', 'P') else row_value for row_value in row]
            updated_map.append(updated_row)
        bomb_location = self.get_bomb_location()
        # print(updated_map)
        refreshed_map = []
        for row_index, row in enumerate(updated_map):
            refreshed_row = []
            for column_index, column in enumerate(row):
                if [column_index, row_index] in enemy_locations:
                    refreshed_row.append("E")
                elif (column_index, row_index) == player_location:
                    refreshed_row.append("P")
                elif (column_index, row_index) == bomb_location:
                    refreshed_row.append("X")
                else:
                    refreshed_row.append(column)
            # print(updated_row)
            refreshed_map.append(refreshed_row)
        self.map_data = refreshed_map

    def update_by_agent(self, action):
        """Update the current AI agent action."""
        self.agent_action = action

    def reset_collision_flags(self):
        """Reset collision flags."""
        self.agent_collided_vertical = False
        self.agent_collided_horizontal = False

    def get_bomb_location(self) -> tuple:
        """Get current bomb location."""
        bomb_location: tuple = ()
        for bomb in self.bomberman_player.sprite.bombs:
            bomb_location = tuple((round(bomb.sprite.rect.x/32), round(bomb.sprite.rect.y/32)))
        return bomb_location

    def get_reward(self):
        """Get the reward for AI agent's action."""
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-public-methods
        # pylint: disable=too-many-statements
        reward = 0
        # Avoid getting hit by bomb
        if self.player_hit_enemy or self.player_hit_explosion:
            # reward -= 40
            reward -= 10
            # reward -= 10.0
        else:
            reward += 1  # Prevented player from bombing when 1.0 and changed back from 0.5
        player_location = self.get_player_location_on_map()
        try:
            if self.all_positions_of_player[player_location] < 5:
                reward += 10.0
        except:
            print(f"Invalid pos:{player_location}")
        dist = 0
        # Getting close to enemy_loc and killing it
        for enemy_loc in self.bomberman_enemy.sprites():
            dist = math.dist(enemy_loc.get_location_on_map(), player_location)
            if dist < 3 and self.agent_action != 4:
                # reward += 5
                reward += 0.5
                # reward += 0.05
            elif dist < 2 and self.agent_action == 4:
                # reward += 25
                # reward += 0.25
                # reward += 2.0
                reward += 15.0
            elif dist < 2 and self.agent_action != 4:
                # reward -= 10
                # reward -= 0.10
                # reward += 7.5
                reward += 0.5
            elif dist < 1 and self.agent_action == 4:
                # reward += 35
                # reward += 0.8
                reward += 10.8
            elif dist < 1 and self.agent_action != 4:
                # reward += 35
                # reward += 0.8
                reward += 8.5
            elif dist < 2 and self.agent_action != 4:
                # reward -= 15
                reward += 0.15
                # reward += 5
            elif dist < 3 and self.agent_action == 4:
                # reward += 10
                # reward += 0.10
                reward += 11.50
            elif dist < 5:
                # reward += 1
                reward += 0.015
            elif dist < 7:
                # reward += 1
                reward += 0.010
            # elif dist < 8:
            #     # reward += 1
            #     reward += 0.015
            # elif dist < 9:
            #     # reward += 1
            #     reward += 0.001
            else:
                # reward -= 35
                reward -= 0.35

        dist = 0
        # Get closer to the breakable walls
        # pylint: disable=consider-using-in
        for wall in self.walls.sprites():
            if wall.tile_type == TileType.TWO_EXPLOSION \
                    or wall.tile_type == TileType.ONE_EXPLOSION_BOMB:
                wall_location = tuple((wall.rect.x/32, wall.rect.y/32))
                dist = math.dist(player_location, wall_location)
                if dist < 5 and self.agent_action == 5:
                    # reward += 2
                    reward += 0.02
                elif dist < 5 and self.agent_action == 4:
                    # reward += 1
                    reward += 0.01
                else:
                    pass

        dist = 0
        # Stay far away from the bomb
        for bomb in self.bomberman_player.sprite.bombs:
            bomb_location = tuple((round(bomb.sprite.rect.x/32), round(bomb.sprite.rect.y/32)))
            dist = math.dist(player_location, bomb_location)
            # print(f"dist: {dist}")
            if dist < 1:
                # reward -= 35
                reward -= 5
            elif dist < 3:
                # reward -= 10
                reward -= 3
            elif dist > 3 and dist < 4:
                # reward += 25
                reward += 6
            elif dist > 4:
                # reward += 25
                reward += 8

        dist = 0
        for bomb in self.bomberman_player.sprite.bombs:
            bomb_location = tuple((round(bomb.sprite.rect.x / 32), round(bomb.sprite.rect.y / 32)))
            for enemy_loc in self.bomberman_enemy.sprites():
                dist = math.dist(enemy_loc.get_location_on_map(), bomb_location)
                if dist < 2:
                    # reward += 10
                    reward += 5.0
                elif dist < 1:
                    # reward += 20
                    reward += 10.0
        # Avoid collisions
        if self.agent_collided_horizontal or self.agent_collided_vertical:
            # reward -= 5
            reward -= 0.005
            self.reset_collision_flags()

        # Enemy get his by bomb
        for bomb in self.bomberman_player.sprite.bombs:
            for explosion in bomb.sprite.explosions:
                for enemy_sprite in self.bomberman_enemy.sprites():
                    if explosion.sprite.rect.colliderect(enemy_sprite) and \
                            not enemy_sprite.is_paused():
                        # reward += 50
                        # reward += 5.0
                        reward += 15.0
        # Encourage bombing
        if self.agent_action == 4:
            reward += 0.5
            # reward += 8.0

        if self.bombing_possibility > 0.5 and self.agent_action == 4:
            # reward += 0.01
            reward += 2
        elif self.bombing_possibility > 0.5 and self.agent_action != 4:
            reward -= 0.01
        elif self.bombing_possibility < 0.5 and self.agent_action != 4:
            reward -= 0.005
        else:
            pass
        # If player is in the same spot for 10 seconds, penalize
        if len(set(self.player_location_track)) == 1:
            # reward -= 50
            reward -= 0.05
        else:
            reward += 0.05
        return reward

    def update_player_data(self):
        with open("all_loc.txt", "w", encoding="utf-8") as file:
            for key, value in self.all_positions_of_player.items():
                file.write(f'{key}:{value}\n')

    def track_player_location(self):
        """Get the current location of the player."""
        if len(list(self.player_location_track)) == 400:
            self.player_location_track.pop()
        self.player_location_track.appendleft(self.get_player_location_on_map())

    def run(self):
        """Graphically display all components of the level"""
        # self.scroll()

        enemies_alive = self.get_enemy_count()
        if enemies_alive == 0 and not self.gateway_flag:
            self.set_gateway()
            self.gateway_flag = True

        #handle level bombs spawned after breaking a wall
        Level.level_bombs.draw(self.display_surface)
        Level.level_bombs.update(self.level_shift)
        Level._clean_up_level_bombs_after_explosion()

        #handle items
        self.items.update(self.level_shift)
        self.items.draw(self.display_surface)
        self.item_collides_with_player()

        #handle level tiles like walls
        self.walls.update(self.level_shift)
        self.walls.draw(self.display_surface)

        #handle player
        self.bomberman_player.update(self.agent_action)
        self.horizontal_collision()
        self.vertical_collision()
        self.bomberman_player.draw(self.display_surface)
        # print(self.get_player_location_on_map())

        #handle bombs
        self.render_and_update_bombs()

        #handle explosions
        #self.render_and_update_explosions()
        self.player_collides_with_explosion()
        self.enemy_collides_with_explosion()

        if self.level_shift != (0, 0):
            self.shift_accumulated[0] += self.level_shift[0]
            self.shift_accumulated[1] += self.level_shift[1]

        # handle enemy
        self.enemy_collision_reverse()
        self.enemy_collides_with_player()
        self.bomberman_enemy.update(self.level_shift,
                                    self.unavailable_locations,
                                    self.shift_accumulated)
        self.bomberman_enemy.draw(self.display_surface)

        #handle gateway
        self.gateway.update(self.level_shift)
        self.gateway.draw(self.display_surface)
        self.gateway_collides_with_player()

        #track camera movement
        if self.level_shift != (0,0):
            self.shift_accumulated[0] += self.level_shift[0]
            self.shift_accumulated[1] += self.level_shift[1]

        #cheat key
        self.cheat_key()
        # print(self.map_data)
        self.update_map_data()
        # self.write_map_data()
        self.track_player_location()
        # self.get_reward()
        # self.update_player_data()