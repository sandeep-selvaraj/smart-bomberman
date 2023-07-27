"""Processing of a simple Tile of a game."""
from typing import Tuple
import random
import pygame
from .utils.fileutils import import_sprite
from .constants import TileType


class Tile(pygame.sprite.Sprite):
    # pylint: disable=too-few-public-methods
    """
    Create a simple tile for the game.

    Attributes:
        pygame.sprite.Sprite
    """
    def __init__(self, position: Tuple, destroyable: bool, tile_type: TileType):
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
        tile_type: TileType(Enum)
            to identify the type of tile in terms of explosion
        """
        super().__init__()
        if destroyable:
            self.image = import_sprite("graphics/destrWall.png")
        else:
            self.image = import_sprite("graphics/wall.png")
        self.rect = self.image.get_rect(topleft=position)
        self.destroyable = destroyable
        self.tile_type = tile_type
        self._init_hidden_bomb()

    def _init_hidden_bomb(self):
        """sets the internal field about whether the wall hides a bomb or not"""
        if self.tile_type == TileType.ONE_EXPLOSION_BOMB:
            prob = random.random()
            if prob < 0: #0 for initial training
                self.does_wall_contain_bomb = True
            else:
                self.does_wall_contain_bomb = False
        else:
            self.does_wall_contain_bomb = False

    def update_tile_type(self, from_tile_type: TileType, to_tile_type: TileType):
        # pylint: disable=unused-argument
        """
        Updates the tile type for the tile including its graphics
        Parameters
        ----------

        from_tile_type: TileType(Enum)
            original tile type
        to_tile_type: TileType(Enum)
            updated tile type
        """
        self.tile_type = to_tile_type
        self.image = import_sprite("graphics/destrWall_1.png")
        self._init_hidden_bomb()

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
