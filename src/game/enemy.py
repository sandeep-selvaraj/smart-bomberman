"""Setting up the Enemy character."""

import pygame
from .utils.fileutils import import_from_spritesheet
from .constants import EnemyStatus, EnemyBomberman


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

    def build_enemy_animation(self):
        """Animate the enemy movements."""
        self.animations = {EnemyStatus.IDLE: [], EnemyStatus.MOVE: []}
        enemy_sprites = import_from_spritesheet('graphics/enemy.png',
                                                EnemyBomberman.SPRITE_HEIGHT.value,
                                                EnemyBomberman.SPRITE_WIDTH.value
                                                )

        self.animations[EnemyStatus.IDLE].append(enemy_sprites[1])
        self.animations[EnemyStatus.MOVE] = enemy_sprites

    def enemy_movement(self):
        """Adding directions specific positioning of the enemy."""
        self.rect.x += self.direction

    def enemy_collision(self):
        """Reverse the enemy once it collides with a wall"""
        self.direction *= -1

    def update(self, level_shift) -> None:
        """
        Updating the status of the enemy on the map per frame.

        Parameters
        ----------
        level_shift [Tuple] : The position of the enemy
        """
        self.rect.x += level_shift[0]
        self.rect.y += level_shift[1]
        self.enemy_movement()
