"""Main file to run the game."""
import sys
from pathlib import Path
from typing import List
import csv
import pygame
from . import level
from .settings import GameWindow

_SCREEN = pygame.display.set_mode((GameWindow.SCREEN_WIDTH.value, GameWindow.SCREEN_HEIGHT.value))
_MAP_FOLDER = "maps"
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
    extra_time = 0
    while True:
        time_remaining = max(0, _TIMER_DURATION + extra_time - pygame.time.get_ticks() // 1000)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        if level_map.player_hit_enemy or level_map.player_hit_explosion or time_remaining == 0:
            pygame.time.wait(1000)
            _endgame_screen(font, time_remaining)
            pygame.display.update()
            continue
        if level_map.player_hit_item:
            extra_time += 50
            level_map.player_hit_item = False
        timer_text = font.render(f'Time Remaining: {time_remaining}', True, _WHITE_FONT_TEXT)
        _SCREEN.fill((128, 128, 128)) #fill bg with grey color
        _SCREEN.blit(timer_text, (10, 10))
        level_map.run()
        _CLOCK.tick(60)
        pygame.display.update()


def _get_all_levels() -> List:
    """Read  and store different maps."""
    map_path = Path.cwd().joinpath(_MAP_FOLDER)
    available_level_files = list(map_path.iterdir())
    all_maps = []
    for level_file in available_level_files:
        with open(level_file, newline='', encoding="utf-8-sig") as file:
            reader = csv.reader(file)
            all_maps.append(list(reader))
    return all_maps


def _endgame_screen(font, time_remaining):
    """Endgame screen once player is killed."""
    _SCREEN.fill("black")
    gameover_text = font.render('GAMEOVER', True, _WHITE_FONT_TEXT)
    if time_remaining == 0:
        time_up_text = font.render("You ran out of time!", True, _WHITE_FONT_TEXT)
        _SCREEN.blit(time_up_text, (150, 200))
    _SCREEN.blit(gameover_text,  (150, 150))
