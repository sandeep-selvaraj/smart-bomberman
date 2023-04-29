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
_CLOCK = pygame.time.Clock()
_TIMER_DURATION = 300
_WHITE_FONT_TEXT = (255, 255, 255)

def start_game(level_number: int):
    """Run the game."""
    # pylint: disable=no-member
    pygame.init()
    pygame.display.set_caption("Smart-Bomberman")
    level_maps = _get_all_levels()
    level_map = level.Level(level_maps[level_number - 1], _SCREEN)
    font = pygame.font.Font(pygame.font.get_default_font(), 18)
    while True:
        time_remaining = max(0, _TIMER_DURATION - pygame.time.get_ticks() // 1000)
        timer_text = font.render(f'Time Remaining: {time_remaining}', True, _WHITE_FONT_TEXT)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        _SCREEN.fill("black")
        _SCREEN.blit(timer_text, (10, 10))
        level_map.run()
        _CLOCK.tick(60)
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
