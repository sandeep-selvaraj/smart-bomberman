"""Setting up the players,obstacles and enemies in different maps."""
from typing import List
import pygame
from . import tile
from . import player
from .settings import Game, Camera, PlayerBomberman


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
