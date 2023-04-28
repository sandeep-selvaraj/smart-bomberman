"""Main file to run the game."""
import sys
from pathlib import Path
from typing import List
import pygame
from . import settings, level

_SCREEN = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
_CURRENT_PATH = Path.cwd()
_MAP_FOLDER = "maps"
_MAP_PATH = _CURRENT_PATH.joinpath(_MAP_FOLDER)
# test_tile = pygame.sprite.Group(tile.Tile((100, 100), 100))


def start_game(level_number: int):
    """Run the game."""
    # pylint: disable=no-member
    level_maps = _get_all_levels()
    level_map = level.Level(level_maps[level_number - 1], _SCREEN)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        _SCREEN.fill("black")
        level_map.run()
        # test_tile.draw(_SCREEN)

        pygame.display.update()


def _get_all_levels() -> List:
    """Read level data from map."""
    available_level_files = list(_MAP_PATH.iterdir())
    all_levels_map = []
    for level_file in available_level_files:
        with open(level_file, encoding="utf-8") as file:
            all_levels_map.append(file.readlines())
    return all_levels_map
