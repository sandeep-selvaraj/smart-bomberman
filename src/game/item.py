"""Processing of power-up items for the game"""
import pygame
from typing import Tuple
from .utils.fileutils import import_sprite
from .constants import ItemType


class Item(pygame.sprite.Sprite):
    """
    Create items for the game

    Parameters
    ----------
    postion [Tuple] : To place the item on a certain point
    """
    def __init__(self, position: Tuple, item_type):
        pygame.sprite.Sprite.__init__(self)
        if item_type == ItemType.EXTRA_TIME.value:
            self.image = import_sprite("graphics/star.png")
        self.rect = self.image.get_rect(topleft=position)
    
    def update(self, level_shift: Tuple):
            """
            Update the locations of items according to the camera movement
            """
            self.rect.x += level_shift[0]
            self.rect.y += level_shift[1]
