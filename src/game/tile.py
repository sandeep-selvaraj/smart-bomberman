"""Processing of a simple Tile of a game."""
from typing import Tuple
import pygame
from .utils.fileutils import import_sprite


class Tile(pygame.sprite.Sprite):
    # pylint: disable=too-few-public-methods
    """
    Create a simple tile for the game.

    Attributes:
        pygame.sprite.Sprite
    """
    def __init__(self, position: Tuple, destroyable: bool):
        """
        Initialize the tile.

        Parameters
        ----------

        position: Tuple
            x,y co-ordinates of the tile
        size: int
            size of the tile
        destroyable: bool
            to check if the wall is destroyable
        """
        super().__init__()
        if destroyable:
            self.image = import_sprite("graphics/destrWall.png")
        else:
            self.image = import_sprite("graphics/wall.png")
        self.rect = self.image.get_rect(topleft=position)
        self.destroyable = destroyable

    def update(self, level_shift: Tuple):
        """
        Scrolls the tile in x and y direction to simulate camera movement

        Parameters
        ----------

        scroll: Tuple
            amount to scroll in the x and y direction
        """
        self.rect.x += level_shift[0]
        self.rect.y += level_shift[1]
