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
    SPRITE_WIDTH = 32
    SPRITE_HEIGHT = 32
    BOMB_RANGE = 1 #initial bomb range of player
    BOMB_LIMIT = 1 #initial bomb limit of player

class EnemyBomberman(Enum):
    """
    Constants related to player character
    """
    SPEED = 1
    ANIMATION_SPEED = 0.05
    SPRITE_WIDTH = 32
    SPRITE_HEIGHT = 32

class PlayerStatus(Enum):
    """
    Player status constants to track player state
    """
    IDLE = 'idle'
    RUN = 'run'

class EnemyStatus(Enum):
    """
    Player status constants to track player state
    """
    IDLE = 'idle'
    MOVE = 'move'

class ItemType(Enum):
    """
    Item type constants
    """
    EXTRA_TIME = 0
    SKATE = 1

class BombItem(Enum):
    """
    Bomb item constants
    """
    EXPLOSION_TIME_DURATION = 2
    EXPLOSION_END_TIME_DURATION = 3 #3-2 = 1 is amt of time explosion remains
    ANIMATION_SPEED = 0.02
    SPRITE_WIDTH = 32
    SPRITE_HEIGHT = 32
