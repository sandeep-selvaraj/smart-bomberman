"""Processing of a simple Tile of a game."""
from typing import Tuple
import pygame


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
            self.image = pygame.image.load("graphics/destrWall.png")
        else:
            self.image = pygame.image.load("graphics/wall.png")
        self.rect = self.image.get_rect(topleft=position)
