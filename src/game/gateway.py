"""Processing of power-up items for the game"""

import pygame

from .utils.fileutils import import_sprite


class Gateway(pygame.sprite.Sprite):
    """
    Create gateway to next level for the game

    Parameters
    ----------
    postion [Tuple] : To place the item on a certain point
    """

    def __init__(self, position: tuple):
        pygame.sprite.Sprite.__init__(self)
        self.image = import_sprite("graphics/blackhole_1.png")
        self.rect = self.image.get_rect(topleft=position)

    def update(self, level_shift: tuple):
        """
        Update the locations of door according to the camera movement
        """

        self.rect.x += level_shift[0]
        self.rect.y += level_shift[1]
