"""Setting up the players,obstacles and enemies in different maps."""
from typing import List
import random
import pygame
from . import tile
from . import player
from . import enemy
from . import item
from . import gateway
from .settings import Game
from .constants import Camera, PlayerBomberman, ItemType, TileType

class Level:
    # pylint: disable=too-many-instance-attributes
    """
    Storing and graphically setting up the map for each level.

    """

    player_hit_skate = False
    player_hit_bomb_length = False
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
        self.player_hit_invincible = False
        self.player_hit_explosion = False
        self.player_hit_gateway = False
        self.gateway_flag = False
        self.level_shift = (0,0)
        self.shift_accumulated = [0,0]
        self.item_class = 0

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
        locations_for_gateway = self.get_locations_for_gateway(layout)
        self.unavailable_locations = self.unavailable_locations_for_enemy(layout)
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
                    if prob < 0.25:
                        powerup = item.Item((x_position, y_position), ItemType.SKATE.value)
                    elif prob < 0.50:
                        powerup = item.Item((x_position, y_position), ItemType.BOMB.value)
                    elif prob < 0.75:
                        powerup = item.Item((x_position, y_position), ItemType.INVINCIBLE.value)
                    else:
                        powerup = item.Item((x_position, y_position), ItemType.EXTRA_TIME.value)
                    self.items.add(powerup)
                    wall = tile.Tile((x_position, y_position), True, TileType.ONE_EXPLOSION_NO_BOMB)
                    self.walls.add(wall)
                if column == 'P':
                    self.bomberman_player.add(player.Player(
                                                                (x_position, y_position),
                                                                self.walls,
                                                                self.display_surface
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
                elif bomberman_player.direction.x > 0:
                    #if player collides with a tile and was moving right,
                    #set the player to left of collider
                    bomberman_player.rect.right = sprite.rect.left

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
                elif bomberman_player.direction.y > 0:
                    #if player collides with a tile and was moving down,
                    #set the player to top of collider
                    bomberman_player.rect.bottom = sprite.rect.top

    def player_collides_with_explosion(self):
        """Check for player collision with explosion"""
        if not self.player_hit_invincible:
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
                for i in range(0, 3)]
            locations_conflicted = [True for location in enemy_start_locations
                                    if location in unavailable_locations]
            if not locations_conflicted:
                break
            number_of_iterations = - 1
        return enemy_start_locations

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
                elif self.item_class == ItemType.BOMB.value:
                    Level.player_hit_bomb_length = True
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
        self.scroll()

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
        self.bomberman_player.update()
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



        #track camera movement
        if self.level_shift != (0,0):
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

        #cheat key
        self.cheat_key()
