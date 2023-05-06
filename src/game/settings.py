"""File to deal with game window settings."""
from enum import Enum


class Game(Enum):
    """
    Constants related to general Game definitions.
    """
    TILE_SIZE = 34

class GameWindow(Enum):
    """
    Constants related to general Game Window attributes.
    """

    #screen dimensions
    SCREEN_WIDTH = 24*Game.TILE_SIZE.value
    SCREEN_HEIGHT = 14*Game.TILE_SIZE.value

class Camera(Enum):
    """
    Constants related to camera settings
    """
    CAMERA_X_LIMIT_LEFT = 2*Game.TILE_SIZE.value
    CAMERA_X_LIMIT_RIGHT = GameWindow.SCREEN_WIDTH.value - 2 * Game.TILE_SIZE.value
    CAMERA_Y_LIMIT_TOP = 2*Game.TILE_SIZE.value
    CAMERA_Y_LIMIT_BOTTOM = GameWindow.SCREEN_HEIGHT.value - 2 * Game.TILE_SIZE.value

class PlayerBomberman(Enum):
    """
    Constants related to player character
    """
    SPEED = 2
