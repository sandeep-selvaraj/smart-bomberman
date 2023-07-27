"""file to hold various constants"""
from enum import Enum
from .settings import Game, GameWindow

class Camera(Enum):
    """
    Constants related to camera settings
    """
    #CAMERA_X_LIMIT_LEFT = 2*Game.TILE_SIZE.value
    CAMERA_X_LIMIT_LEFT = 0
    #CAMERA_X_LIMIT_RIGHT = GameWindow.SCREEN_WIDTH.value - 2 * Game.TILE_SIZE.value
    CAMERA_X_LIMIT_RIGHT = GameWindow.SCREEN_WIDTH.value
    CAMERA_Y_LIMIT_TOP = 2*Game.TILE_SIZE.value
    CAMERA_Y_LIMIT_BOTTOM = GameWindow.SCREEN_HEIGHT.value - 2 * Game.TILE_SIZE.value

class PlayerBomberman(Enum):
    """
    Constants related to player character
    """
    SPEED = 1
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

class PlayerAction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    WAIT = "WAIT"
    BOMB = "BOMB"

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
    SKATE = 0
    INVINCIBLE = 1
    EXTRA_TIME = 2

class BombItem(Enum):
    """
    Bomb item constants
    """
    EXPLOSION_TIME_DURATION = 3
    EXPLOSION_END_TIME_DURATION = 4 #4-3 = 1 is amt of time explosion remains
    ANIMATION_SPEED = 0.02
    SPRITE_WIDTH = 32
    SPRITE_HEIGHT = 32

class TileType(Enum):
    """
    Tile type constants
    """
    NONE = 0
    ONE_EXPLOSION_BOMB = 1
    TWO_EXPLOSION = 2
    ONE_EXPLOSION_NO_BOMB = 3

class GameFinalState(Enum):
    LOSE = "LOSE"
    WIN = "WIN"
    NONE = "NONE"

class NumericTileMapIds(Enum):
    BLANK_SPACE = 0
    UNBREAKABLE_WALL = 1
    BREAKABLE_WALL_ONE_EXPL = 2
    BREAKABLE_WALL_TWO_EXPL = 3
    PLAYER = 4
    ITEM = 5
    ENEMY_1 = 6
    #ENEMY_2 = 7
    #GATEWAY = 8
    EDGE_OF_MAP = 9
    BOMB = 10
    PLAYER_AND_BOMB = 11
    EXPLOSION = 12
    EXPLOSION_AND_PLAYER = 13
    PLAYER_AND_BOMB_AND_EXPLOSION = 14
    PLAYER_AND_ENEMY = 15

