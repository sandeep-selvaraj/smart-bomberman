"""File to deal with game window settings."""
from enum import Enum


class Game(Enum):
    """
    Enum basically to deal with Game definitions.
    """
    TILE_SIZE = 34

class GameWindow(Enum):
    """
    Enum to deal with the Game Window attributes.
    """
    SCREEN_WIDTH = 24*Game.TILE_SIZE.value
    SCREEN_HEIGHT = 14*Game.TILE_SIZE.value
