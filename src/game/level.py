"""Setting up different maps in levels."""
from typing import List
import pygame
from . import tile, settings


class Level:
    """
    Storing and graphically setting up the map for each level.

    """
    def __init__(self, level_data: List, surface: pygame.Surface):
        """
        Parameters
        ----------
        level_data: List
            The Map layout for a level
        """
        self.display_surface = surface
        self.setup_level(level_data)

    def setup_level(self, layout: List):
        """
        Setup up the map for a level.

        Parameters
        ----------
        layout: List
            The Map layout

        """
        self.walls = pygame.sprite.Group()
        for row_index, row in enumerate(layout):
            for column_index, column in enumerate(row):
                y_position = row_index * settings.TILE_SIZE
                x_position = column_index * settings.TILE_SIZE
                if column == 'X':
                    wall = tile.Tile((x_position, y_position), settings.TILE_SIZE)
                    self.walls.add(wall)

    def run(self):
        """Graphically display the map layout."""
        self.walls.draw(self.display_surface)