"""file to hold various constants"""
from enum import Enum
from .settings import Game, GameWindow

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
    ANIMATION_SPEED = 0.05
    SPRITE_WIDTH = 34
    SPRITE_HEIGHT = 34

class PlayerStatus(Enum):
    """
    Player status constants to track player state
    """
    IDLE = 'idle'
    RUN = 'run'
