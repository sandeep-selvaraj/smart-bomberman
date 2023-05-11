"""Setting up the players,obstacles and enemies in different maps."""
from typing import List
import random
import pygame
from . import tile
from . import player
from . import enemy
from .settings import Game
from .constants import Camera, PlayerBomberman


class Level:
    """
    Storing and graphically setting up the map for each level.

    """
    def __init__(self, level_data: List, surface: pygame.Surface):
        """
        Parameters
        ----------
        level_data: List
            The Map layout for a level
        """
        self.display_surface = surface
        self.setup_level(level_data)
        self.player_hit_enemy = False
        self.level_shift = (0,0)

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
        locations_for_enemy = self.get_locations_for_enemy(layout)
        for row_index, row in enumerate(layout):
            for column_index, column in enumerate(row):
                y_position = row_index * Game.TILE_SIZE.value
                x_position = column_index * Game.TILE_SIZE.value
                if column in ('W', '#'):
                    wall = tile.Tile((x_position, y_position), False)
                    self.walls.add(wall)
                if column == 'B':
                    wall = tile.Tile((x_position, y_position), True)
                    self.walls.add(wall)
                if column == 'P':
                    self.bomberman_player.add(player.Player((x_position, y_position)))
                if (row_index, column_index) in locations_for_enemy:
                    self.bomberman_enemy.add(enemy.Enemy((x_position, y_position)))

    def scroll(self):
        """
        Simulates the camera movement via level scrolling mechanism
        """
        bomberman_player = self.bomberman_player.sprite
        player_x = bomberman_player.rect.centerx
        direction_x = bomberman_player.direction.x
        player_y = bomberman_player.rect.centery
        direction_y = bomberman_player.direction.y

        if player_x < Camera.CAMERA_X_LIMIT_LEFT.value and direction_x < 0:
            #if player has reached left end of screen and wants to keep moving left
            self.level_shift = (PlayerBomberman.SPEED.value,0)
            bomberman_player.speed = 0
        elif player_x > Camera.CAMERA_X_LIMIT_RIGHT.value and direction_x > 0:
            #if player has reached right end of screen and wants to keep moving right
            self.level_shift = (-PlayerBomberman.SPEED.value,0)
            bomberman_player.speed = 0
        elif player_y < Camera.CAMERA_Y_LIMIT_TOP.value and direction_y < 0:
            #if player has reached top end of screen and wants to keep moving top
            self.level_shift = (0,PlayerBomberman.SPEED.value)
            bomberman_player.speed = 0
        elif player_y > Camera.CAMERA_Y_LIMIT_BOTTOM.value and direction_y > 0:
            #if player has reached bottom end of screen and wants to keep moving down
            self.level_shift = (0,-PlayerBomberman.SPEED.value)
            bomberman_player.speed = 0
        else:
            #if the player is within limits of screen - no scroll needed
            self.level_shift = (0,0)
            bomberman_player.speed = PlayerBomberman.SPEED.value

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

    def enemy_collision_reverse(self):
        """Redirect enemy after collision with wall."""
        for enemy_sprite in self.bomberman_enemy.sprites():
            if pygame.sprite.spritecollide(enemy_sprite, self.walls.sprites(), False):
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
                if column in ('W', '#', 'B', 'P'):
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

    def run(self):
        """Graphically display all components of the level"""

        #handle level tiles like walls
        self.walls.update(self.level_shift)
        self.walls.draw(self.display_surface)
        self.scroll()

        #handle player
        self.bomberman_player.update()
        self.horizontal_collision()
        self.vertical_collision()
        self.bomberman_player.draw(self.display_surface)

        # handle enemy
        self.enemy_collision_reverse()
        self.enemy_collides_with_player()
        self.bomberman_enemy.update(self.level_shift)
        self.bomberman_enemy.draw(self.display_surface)
