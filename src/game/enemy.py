"""Setting up the Enemy character."""

import pygame
from .utils.fileutils import import_from_spritesheet
from .constants import EnemyStatus, EnemyBomberman
from .algorithms import a_star


class Enemy(pygame.sprite.Sprite):
    """
    Defining enemy characteristics.

    Parameters
    ----------
    postion [Tuple] : To place the enemy on a certain point
    """

    def __init__(self, position):
        pygame.sprite.Sprite.__init__(self)
        self.build_enemy_animation()
        self.image = self.animations[EnemyStatus.IDLE][0]
        self.rect = self.image.get_rect(topleft=position)
        self.direction = -1
        self.current_location = (None, None)

    def build_enemy_animation(self):
        """Animate the enemy movements."""
        self.animations = {EnemyStatus.IDLE: [], EnemyStatus.MOVE: []}
        enemy_sprites = import_from_spritesheet('graphics/enemy.png',
                                                EnemyBomberman.SPRITE_HEIGHT.value,
                                                EnemyBomberman.SPRITE_WIDTH.value
                                                )

        self.animations[EnemyStatus.IDLE].append(enemy_sprites[1])
        self.animations[EnemyStatus.MOVE] = enemy_sprites

    def enemy_movement(self, path_to_player):
        """Adding directions specific positioning of the enemy."""
        _ = path_to_player  # To be removed
        # if path_to_player:
        #     x_direction, y_direction = path_to_player
        #     x_current, y_current = self.current_location
        #     y_difference = (y_direction - y_current)
        #     if y_difference != 0:
        #         self.rect.y += y_difference
        #     else:
        #         self.rect.x += (x_direction - x_current)
        # else:
        self.rect.x += self.direction

    def enemy_collision(self):
        """Reverse the enemy once it collides with a wall"""
        self.direction *= -1

    def get_location_on_map(self) -> tuple:
        """Get player location on the map."""
        return round(self.rect.x / EnemyBomberman.SPRITE_HEIGHT.value), \
               round(self.rect.y / EnemyBomberman.SPRITE_WIDTH.value)

    def update(self, level_shift, player_location, mapdata) -> None:
        """
        Updating the status of the enemy on the map per frame.

        Parameters
        ----------
        level_shift [Tuple] : The position of the enemy
        """
        self.rect.x += level_shift[0]
        self.rect.y += level_shift[1]
        self.current_location = self.get_location_on_map()
        path = a_star.get_path(mapdata, player_location, self.current_location)
        next_path = None
        if path:
            *_, next_path, _ = path
        self.enemy_movement(next_path)
