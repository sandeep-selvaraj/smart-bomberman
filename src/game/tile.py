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
    def __init__(self, position: Tuple):
        """
        Initialize the tile.

        Parameters
        ----------

        position: Tuple
            x,y co-ordinates of the tile
        size: int
            size of the tile
        """
        super().__init__()
        self.image = pygame.image.load("graphics/wall.png")
        self.rect = self.image.get_rect(topleft=position)
