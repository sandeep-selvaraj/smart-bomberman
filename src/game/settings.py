"""File to hold various settings."""
from enum import Enum


class Game(Enum):
    """
    Constants related to general Game definitions.
    """
    TILE_SIZE = 32

class GameWindow(Enum):
    """
    Constants related to general Game Window attributes.
    """

    #screen dimensions
    SCREEN_WIDTH = 42*Game.TILE_SIZE.value
    SCREEN_HEIGHT = 16*Game.TILE_SIZE.value
