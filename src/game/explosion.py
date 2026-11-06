"""Setting up the bomb explosions"""

import pygame

from .utils.fileutils import import_sprite


class Explosion(pygame.sprite.Sprite):
    """
    Encapsulates the explosion at each individual tile caused by a bomb

    """

    def __init__(self, position: tuple):
        """
        Parameters
        ----------
        position: Tuple
            initial position of the bomb on map
        """
        super().__init__()

        self.image = import_sprite("graphics/explosion.png")
        self.rect = self.image.get_rect(topleft=position)

    def update(self, level_shift):
        """
        updates explosion state
        """
        self.rect.x += level_shift[0]
        self.rect.y += level_shift[1]
