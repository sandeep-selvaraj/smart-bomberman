"""Main file to run the game."""
import sys
from pathlib import Path
from typing import List
import csv
import pygame
from . import settings, level

_SCREEN = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
_CURRENT_PATH = Path.cwd()
_MAP_FOLDER = "maps"
_MAP_PATH = _CURRENT_PATH.joinpath(_MAP_FOLDER)


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
        pygame.display.set_caption("Smart-Bomberman")
        pygame.display.update()


def _get_all_levels() -> List:
    """Read  and store different maps."""
    available_level_files = list(_MAP_PATH.iterdir())
    all_maps = []
    for level_file in available_level_files:
        with open(level_file, newline='', encoding="utf-8-sig") as file:
            reader = csv.reader(file)
            all_maps.append(list(reader))
    return all_maps
