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
    def __init__(self, position: Tuple, size: int, is_background: bool):
        """
        Initialize the tile.

        Parameters
        ----------

        position: Tuple
            x,y co-ordinates of the tile
        size: int
            size of the tile
        background: bool
            to check if the tile is for a wall or background
        """
        super().__init__()
        self.image = pygame.Surface((size, size))
        if is_background:
            self.image.fill("brown")
        else:
            self.image.fill("grey")
        self.rect = self.image.get_rect(topleft=position)
