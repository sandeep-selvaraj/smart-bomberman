"""Processing of power-up items for the game"""
from typing import Tuple
import pygame
from .utils.fileutils import import_sprite
from .constants import ItemType


class Item(pygame.sprite.Sprite):
    # pylint: disable=too-few-public-methods
    """
    Create items for the game

    Parameters
    ----------
    postion [Tuple] : To place the item on a certain point
    """
    def __init__(self, position: Tuple, item_type):
        pygame.sprite.Sprite.__init__(self)
        if item_type == ItemType.EXTRA_TIME.value:
            self.image = import_sprite("graphics/extra_time.png")
            self.item_num = ItemType.EXTRA_TIME.value
        elif item_type == ItemType.SKATE.value:
            self.image = import_sprite("graphics/skate.png")
            self.item_num = ItemType.SKATE.value
        elif item_type == ItemType.INVINCIBLE.value:
            self.image = import_sprite("graphics/invincible.png")
            self.item_num = ItemType.INVINCIBLE.value
        self.rect = self.image.get_rect(topleft=position)

    def update(self, level_shift: Tuple):
        """
        Update the locations of items according to the camera movement
        """
        self.rect.x += level_shift[0]
        self.rect.y += level_shift[1]
