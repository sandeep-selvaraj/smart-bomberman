from typing import List
import random
import pygame
import math
import numpy as np
from pathfinding.core.grid import Grid  # type: ignore
from pathfinding.finder.a_star import AStarFinder  # type: ignore
from . import tile
from . import player
from . import enemy
from . import item
from . import gateway
from .settings import Game
from .constants import Camera, PlayerBomberman, ItemType, TileType, NumericTileMapIds

class Level:
    # pylint: disable=too-many-instance-attributes
    """
    Storing and graphically setting up the map for each level.

    """

    player_hit_skate = False
    level_bombs: pygame.sprite.Group = pygame.sprite.Group()

    def __init__(self, level_data: List, surface: pygame.Surface, level_number: int, type_run):
        """
        Parameters
        ----------
        level_data: List
            The Map layout for a level
        """
        self.display_surface = surface
        self.map_data = level_data
        self.level_number = level_number
        self.type_run = type_run
        self.num_rows = len(level_data)
        self.num_cols = len(level_data[0])
        self.abstract_map_data = self.create_abstract_map_data()
        self.setup_level(level_data)
        #self.find_shortest_path_to_enemies_from_player()
        #self._print_abs_map_data()
        self.player_hit_enemy = False
        self.player_hit_item = False
        self.player_hit_invincible = False
        self.player_hit_explosion = False
        self.player_hit_gateway = False
        self.gateway_flag = False
        self.level_shift = (0,0)
        self.shift_accumulated = [0,0]
        self.item_class = 0
        self.is_player_out_of_bounds = False #rel: RL
        self.check = 0

    def create_abstract_map_data(self) -> np.ndarray:
        """
        creates a numeric grid representation of the level map
        this is a one to one correspondence of the original grid which has character tokens 
        """
        abs_map_data = np.zeros(shape=(self.num_rows, self.num_cols), dtype=int)
        #print(self.map_data[0][0] == '')
        for row_index, row in enumerate(self.map_data):
            for column_index, column in enumerate(row):
                if column == '#':
                    abs_map_data[row_index, column_index] = NumericTileMapIds.EDGE_OF_MAP.value
                elif column == 'W':
                    abs_map_data[row_index, column_index] = NumericTileMapIds.UNBREAKABLE_WALL.value
                elif column == 'B_1':
                    abs_map_data[row_index, column_index] = NumericTileMapIds.BREAKABLE_WALL_ONE_EXPL.value
                elif column == 'B_2':
                    abs_map_data[row_index, column_index] = NumericTileMapIds.BREAKABLE_WALL_TWO_EXPL.value
                elif column == 'P':
                    abs_map_data[row_index, column_index] = NumericTileMapIds.PLAYER.value
                elif column == 'I':
                    #item blocks will be seen by the RL agent as breakable walls since they are hidden in the walls
                    abs_map_data[row_index, column_index] = NumericTileMapIds.BREAKABLE_WALL_ONE_EXPL.value
                elif column == '':
                    pass
                else:
                    raise ValueError(f"{column} token was unexpected at ({row_index}, {column_index})")
        return abs_map_data
    
    def _update_player_coords_on_abstract_map(self):
        self.is_player_out_of_bounds = False
        player_pos = self.get_abstract_player_location_on_map()

        #update original position of player to blank space
        self.abstract_map_data[self.abstract_map_data == NumericTileMapIds.PLAYER.value] = NumericTileMapIds.BLANK_SPACE.value

        #update player position on abstract map data
        #here its 1 then 0 because on game moving in x dir is rows in map data and so on for y dir
        try:
            self.abstract_map_data[player_pos[1], player_pos[0]] = NumericTileMapIds.PLAYER.value
        except IndexError:
            self.is_player_out_of_bounds = True

    def _initialize_enemy_locations_on_abstract_map(self, locations_for_enemy):
        #print(locations_for_enemy)
        for (enemy_row_index, enemy_column_index) in locations_for_enemy:
            if self.abstract_map_data[enemy_row_index, enemy_column_index] == NumericTileMapIds.BLANK_SPACE.value:
                self.abstract_map_data[enemy_row_index, enemy_column_index] = NumericTileMapIds.ENEMY_1.value
            else:
                raise ValueError(f"{self.abstract_map_data[enemy_row_index, enemy_column_index]} already present at ({enemy_row_index}, {enemy_column_index})")
    
    def _update_enemy_coords_on_abstract_map(self):
        location_of_player = self.get_abstract_player_location_on_map()
        #update original position of enemies to blank space
        #self.abstract_map_data[self.abstract_map_data == NumericTileMapIds.ENEMY_1.value] = NumericTileMapIds.BLANK_SPACE.value
        self.abstract_map_data[np.logical_or(self.abstract_map_data == 6, self.abstract_map_data == 15)] = 0
        
        for enemy_sprite in self.bomberman_enemy.sprites():
            location_of_enemy = enemy_sprite.get_abstract_location_on_map()
            if location_of_player == location_of_enemy:
                self.abstract_map_data[location_of_enemy[1], location_of_enemy[0]] = NumericTileMapIds.PLAYER_AND_ENEMY.value
            else:
                self.abstract_map_data[location_of_enemy[1], location_of_enemy[0]] = NumericTileMapIds.ENEMY_1.value
    
    def _update_breakable_wall_coords_on_abstract_map(self):
        #update original position of breakable walls to blank space
        self.abstract_map_data[self.abstract_map_data == NumericTileMapIds.BREAKABLE_WALL_ONE_EXPL.value] = NumericTileMapIds.BLANK_SPACE.value
        
        for wall_sprite in self.walls.sprites():
            if wall_sprite.destroyable:
                location_of_wall = wall_sprite.get_abstract_location_on_map()
                self.abstract_map_data[location_of_wall[1], location_of_wall[0]] = NumericTileMapIds.BREAKABLE_WALL_ONE_EXPL.value
    
    def _update_bomb_coords_on_abstract_map(self): 
        #update original position of bombs to blank space
        self.abstract_map_data[np.logical_or(self.abstract_map_data == 10, self.abstract_map_data == 11)] = 0
        
        location_of_player = self.get_abstract_player_location_on_map()
        for bomb in self.bomberman_player.sprite.bombs:
            location_of_bomb = self.get_abstract_location_on_map(bomb.sprite.abstract_rect)
            if (((location_of_bomb[0]-location_of_player[0])**2 + (location_of_bomb[1]-location_of_player[1])**2) == 0):
                #if bomb and player are on top of each other use a specific token on the abstract map
                self.abstract_map_data[location_of_bomb[1], location_of_bomb[0]] = NumericTileMapIds.PLAYER_AND_BOMB.value
            else:
                self.abstract_map_data[location_of_bomb[1], location_of_bomb[0]] = NumericTileMapIds.BOMB.value
        self._update_expl_coords_on_abstract_map()

    def is_player_in_bomb_range(self):
        location_of_player = self.get_abstract_player_location_on_map()
        bomb_range = self.bomberman_player.sprite.bomb_range
        for bomb in self.bomberman_player.sprite.bombs:
            location_of_bomb = self.get_abstract_location_on_map(bomb.sprite.abstract_rect)
            if (((location_of_bomb[0]-location_of_player[0])**2 + (location_of_bomb[1]-location_of_player[1])**2) <= bomb_range):
                return True
        return False
    
    def _update_expl_coords_on_abstract_map(self): 
        #update original position of expl to blank space
        try:
            self.abstract_map_data[np.logical_or(self.abstract_map_data == 12, self.abstract_map_data == 13, self.abstract_map_data == 14)] = 0
            location_of_player = self.get_abstract_player_location_on_map()
            
            for bomb in self.bomberman_player.sprite.bombs:
                location_of_bomb = self.get_abstract_location_on_map(bomb.sprite.abstract_rect)
                for expl in bomb.sprite.explosions:
                    location_of_explosion = self.get_abstract_location_on_map(expl.sprite.abstract_rect)
                    if location_of_player == location_of_explosion and location_of_bomb == location_of_explosion:
                        self.abstract_map_data[location_of_explosion[1], location_of_explosion[0]] = NumericTileMapIds.PLAYER_AND_BOMB_AND_EXPLOSION.value
                    elif location_of_player == location_of_explosion:
                        self.abstract_map_data[location_of_explosion[1], location_of_explosion[0]] = NumericTileMapIds.EXPLOSION_AND_PLAYER.value
                    else:
                        self.abstract_map_data[location_of_explosion[1], location_of_explosion[0]] = NumericTileMapIds.EXPLOSION.value
        except IndexError:
            self.is_player_out_of_bounds = True
     
    
    #def get_distane_of_player_from_bombs(self):
    #    location_of_player = self.get_abstract_player_location_on_map()
    #    player_distance_from_bombs = []
    #    for bomb in self.bomberman_player.sprite.bombs:
    #        location_of_bomb = self.get_abstract_location_on_map(bomb.sprite.abstract_rect)
    #        player_distance_from_bombs.append((location_of_bomb[0]-location_of_player[0])**2 + (location_of_bomb[1]-location_of_player[1])**2)
    #    return player_distance_from_bombs
    
    def get_distance_of_player_from_bombs(self):
        #location_of_player = self.get_player_location_on_map()
        location_of_player = self.bomberman_player.sprite.abstract_rect
        player_distance_from_bombs = []
        for bomb in self.bomberman_player.sprite.bombs:
            #location_of_bomb = self.get_abstract_location_on_map(bomb.sprite.rect)
            location_of_bomb = bomb.sprite.abstract_rect
            player_distance_from_bombs.append(int(math.sqrt((location_of_bomb.x-location_of_player.x)**2 + (location_of_bomb.y-location_of_player.y)**2)))
        return player_distance_from_bombs

    
    def find_shortest_path_to_enemies_from_player(self):
        self.is_player_out_of_bounds = False
        # blank space = 0, breakable wall=2 and enemies=6 are converted to 1 ie, passable cells and others to 0 ie, obstacles for pathfinding
        encoded_abstract_map_data = np.where(np.logical_or.reduce((self.abstract_map_data == 0, self.abstract_map_data == 6)) == 0, 0, 1)
        #print(self.abstract_map_data)
        #print(encoded_abstract_map_data)
        grid = Grid(matrix=encoded_abstract_map_data)
        #player_position = np.argwhere(self.abstract_map_data == NumericTileMapIds.PLAYER.value)[0]
        #have to check PLAYER and PLAYER_AND_BOMB, PLAYER_AND_EXPLOSION, PLAYER_AND_BOMB_AND_EXPLOSION 
        #in case player and bomb are on same spot (which is the case in the beginning)
        shortest_distance_to_enemies = []
        
        try:
            player_position = np.argwhere(np.isin(self.abstract_map_data, [4, 11, 13, 14, 15]))[0]

            player_position_node = grid.node(player_position[1], player_position[0])
            enemy_positions = np.argwhere(self.abstract_map_data == NumericTileMapIds.ENEMY_1.value)

            a_star_finder = AStarFinder()
            #path, _ = a_star_finder.find_path(grid.node(0,0), grid.node(2, 2), grid)
            #print(path)
            #print(len(path))
            
            for enemy_pos in enemy_positions:
                #path, _ = a_star_finder.find_path(player_position_node, grid.node(4, 8), grid)
                path, _ = a_star_finder.find_path(player_position_node, grid.node(enemy_pos[1], enemy_pos[0]), grid)

                #print(f"Shortest path from {player_position} to {enemy_pos}:")
                #print(path)
                #print(len(path))
                shortest_distance_to_enemies.append(len(path))
                grid.cleanup()
        except IndexError:
            self.is_player_out_of_bounds = True
        return shortest_distance_to_enemies

    def _print_abs_map_data(self):
        print(self.abstract_map_data) 



    def setup_level(self, layout: List):
        # pylint: disable=too-many-branches
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
        self._initialize_enemy_locations_on_abstract_map(locations_for_enemy) #rel: RL
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
                    if prob < 0.3:
                        powerup = item.Item((x_position, y_position), ItemType.EXTRA_TIME.value)
                    elif prob < 0.6:
                        powerup = item.Item((x_position, y_position), ItemType.SKATE.value)
                    else:
                        powerup = item.Item((x_position, y_position), ItemType.INVINCIBLE.value)
                    self.items.add(powerup)
                    wall = tile.Tile((x_position, y_position), True, TileType.ONE_EXPLOSION_NO_BOMB)
                    self.walls.add(wall)
                if column == 'P':
                    if self.type_run == 'train_1':
                        location_for_player = self.get_location_for_player(self.map_data)
                        x_position = location_for_player[1] * Game.TILE_SIZE.value
                        y_position = location_for_player[0] * Game.TILE_SIZE.value
                    self.bomberman_player.add(player.Player(
                                                            (x_position, y_position),
                                                            self.walls,
                                                            self.display_surface,
                                                            self.type_run
                                                        ))
                if (row_index, column_index) in locations_for_enemy:
                    self.bomberman_enemy.add(enemy.Enemy((x_position, y_position),
                                                         self.level_number))
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
            #rel: RL - start
            #bomberman_player.abstract_position[0] += bomberman_player.direction.x * bomberman_player.speed
            #rel: RL - end
            
            #if player has reached left end of screen and wants to keep moving left
            self.level_shift = (bomberman_player.abstract_speed,0)
            bomberman_player.speed = 0
            is_scroll_to_be_added = True
            
        elif player_x > Camera.CAMERA_X_LIMIT_RIGHT.value and direction_x > 0:
            #rel: RL - start
            #bomberman_player.abstract_position[0] += bomberman_player.direction.x * bomberman_player.speed
            #rel: RL - end
            
            #if player has reached right end of screen and wants to keep moving right
            self.level_shift = (-bomberman_player.abstract_speed,0)
            bomberman_player.speed = 0
            is_scroll_to_be_added = True
        elif player_y < Camera.CAMERA_Y_LIMIT_TOP.value and direction_y < 0:
            #rel: RL - start
            #bomberman_player.abstract_position[1] += bomberman_player.direction.y * bomberman_player.speed
            #rel: RL - end
            
            #if player has reached top end of screen and wants to keep moving top
            self.level_shift = (0,bomberman_player.abstract_speed)
            bomberman_player.speed = 0
            is_scroll_to_be_added = True
        elif player_y > Camera.CAMERA_Y_LIMIT_BOTTOM.value and direction_y > 0:
            #rel: RL - start
            #bomberman_player.abstract_position[1] += bomberman_player.direction.y * bomberman_player.speed
            #rel: RL - end
            
            #if player has reached bottom end of screen and wants to keep moving down
            self.level_shift = (0,-bomberman_player.abstract_speed)
            bomberman_player.speed = 0
            is_scroll_to_be_added = True
        else:
            #if the player is within limits of screen - no scroll needed
            self.level_shift = (0,0)
            bomberman_player.speed = bomberman_player.abstract_speed
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
        #bomberman_player.rect.x += bomberman_player.direction.x * bomberman_player.speed
        #bomberman_player.abstract_rect.x += bomberman_player.direction.x * bomberman_player.abstract_speed
        bomberman_player.rect.x += bomberman_player.direction.x * 32
        bomberman_player.abstract_rect.x += bomberman_player.direction.x * 32
        player_wall_collision = False

        #detect collision with all game tiles in horizontal direction
        for sprite in self.walls.sprites():
            if sprite.rect.colliderect(bomberman_player.rect):
                player_wall_collision = True
                if bomberman_player.direction.x < 0:
                    #if player collides with a tile and was moving left,
                    #set the player to right of collider
                    bomberman_player.rect.left = sprite.rect.right
                    bomberman_player.abstract_rect.left = sprite.abstract_rect.right
                elif bomberman_player.direction.x > 0:
                    #if player collides with a tile and was moving right,
                    #set the player to left of collider
                    bomberman_player.rect.right = sprite.rect.left
                    bomberman_player.abstract_rect.right = sprite.abstract_rect.left
        return player_wall_collision

    def vertical_collision(self):
        """
        Handles player collision in vertical direction
        """
        bomberman_player = self.bomberman_player.sprite

        #move the player vertically
        #bomberman_player.rect.y += bomberman_player.direction.y * bomberman_player.speed
        #bomberman_player.abstract_rect.y += bomberman_player.direction.y * bomberman_player.abstract_speed
        bomberman_player.rect.y += bomberman_player.direction.y * 32
        bomberman_player.abstract_rect.y += bomberman_player.direction.y * 32
        player_wall_collision = False

        #detect collision with all game tiles in vertical direction
        for sprite in self.walls.sprites():
            if sprite.rect.colliderect(bomberman_player.rect):
                player_wall_collision = True
                if bomberman_player.direction.y < 0:
                    #if player collides with a tile and was moving top,
                    #set the player to bottom of collider
                    bomberman_player.rect.top = sprite.rect.bottom
                    bomberman_player.abstract_rect.top = sprite.abstract_rect.bottom
                elif bomberman_player.direction.y > 0:
                    #if player collides with a tile and was moving down,
                    #set the player to top of collider
                    bomberman_player.rect.bottom = sprite.rect.top
                    bomberman_player.abstract_rect.bottom = sprite.abstract_rect.top
        return player_wall_collision

    def player_collides_with_explosion(self):
        """Check for player collision with explosion"""
        if not self.player_hit_invincible:
            for bomb in self.bomberman_player.sprite.bombs:
                for explosion in bomb.sprite.explosions:
                    if explosion.sprite.rect.colliderect(self.bomberman_player.sprite.rect):
                        self.player_hit_explosion = True
                        #pass
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
        if self.player_hit_invincible:
            for enemy_sprite in self.bomberman_enemy.sprites():
                if enemy_sprite.rect.colliderect(self.bomberman_player.sprite.rect) and \
                            not enemy_sprite.is_paused():
                    enemy_sprite.enemy_hit_by_bomb()
                    enemy_sprite.set_pause(30)
        else:
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
                for i in range(0, 1)]
            locations_conflicted = [True for location in enemy_start_locations
                                    if location in unavailable_locations]
            #handle the scenario where sometimes there are duplicate enemy locations
            if not locations_conflicted and (len(enemy_start_locations) == len(set(enemy_start_locations))):
                break
            number_of_iterations -= 1
        enemy_start_locations = [(2,5)]
        return enemy_start_locations
    
    def get_location_for_player(self, mapdata):
        """Get all possible random spots where enemy can be placed."""
        median_row = int(len(mapdata)/2)
        median_col = int(len(mapdata[0])/2)
        unavailable_locations = self.unavailable_locations_for_enemy(mapdata)
        number_of_iterations = 50
        while number_of_iterations:
            player_start_location = (
                    random.randint(2, len(mapdata)-2),
                    random.randint(2, len(mapdata[0])-2)
                 )
            locations_conflicted = [True for location in unavailable_locations
                                    if location == player_start_location]
            #handle the scenario where sometimes there are duplicate enemy locations
            if not locations_conflicted:
                break
            if player_start_location[0] <= 1 or player_start_location[1] <= 1:
                continue
            number_of_iterations = - 1
        return player_start_location

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
                elif self.item_class == ItemType.INVINCIBLE.value:
                    self.player_hit_invincible = True
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
    
    def get_abstract_player_location_on_map(self) -> tuple:
        """Get the player's current location."""
        return round(self.bomberman_player.sprite.abstract_rect.x/32),\
               round(self.bomberman_player.sprite.abstract_rect.y/32)
    
    def get_abstract_location_on_map(self, location, size=Game.TILE_SIZE.value) -> tuple:
        """Get the anyones abstract location."""
        return round(location.x/size), round(location.y/size)


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

    def run(self):
        """Graphically display all components of the level"""
        self.bomberman_player.sprite.update_player_speed() #this has to be before scroll()
        self.scroll()

        #print(f'Rows: {self.num_rows} and Cols: {self.num_cols}')

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
        self._update_breakable_wall_coords_on_abstract_map()

        #handle player
        self.bomberman_player.update()
        if self.check % 10 == 0:
            self.horizontal_collision()
            self.vertical_collision()
            self.check = 0
        self.check += 1
        self.bomberman_player.draw(self.display_surface)
        self._update_player_coords_on_abstract_map() #rel: RL
        #print(self.bomberman_player.sprite.abstract_rect.x)
        # print(self.get_player_location_on_map())

        #handle bombs
        self.render_and_update_bombs()
        self._update_bomb_coords_on_abstract_map()

        #handle explosions
        #self.render_and_update_explosions()
        self.player_collides_with_explosion()
        self.enemy_collides_with_explosion()

        # handle enemy
        self.enemy_collision_reverse()
        self.enemy_collides_with_player()
        self.bomberman_enemy.update(self.level_shift,
                                    self.get_player_location_on_map(),
                                    self.map_data)
        self.bomberman_enemy.draw(self.display_surface)
        self._update_enemy_coords_on_abstract_map()

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

        self.find_shortest_path_to_enemies_from_player()
        #print(sp)
        #print(self.is_player_in_bomb_range())
        if self.type_run == 'play':
            self._print_abs_map_data()
        #if len(self.bomberman_player.sprite.bombs) != 0:
        #    print(min(self.get_distance_of_player_from_bombs()))